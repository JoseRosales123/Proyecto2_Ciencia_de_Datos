"""Construcción point-in-time C desde insumos normalizados, sin SQL ni modelos.

No aplica identidad global derivada del futuro. La extracción de fuentes originales
está bloqueada; adaptador_c solo implementa controles y conversiones puras.
"""
import csv
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path

from scripts.mlops.contrato_c import (
    FEATURES, SYSTEMS, cutoff, feature_time, utc_time, opaque_id, TemporalControls, digest,
)
from scripts.mlops.adaptador_c import validate_normalized_package


def read_inputs(folder, date, *, with_controls=False):
    cutoff(date)
    folder = Path(folder)
    paths = [folder / name for name in ('contrato_c.json', 'eventos.csv', 'identidades.csv', 'cdc.csv')]
    if any(path.is_symlink() or not path.is_file() or path.resolve() != path.absolute() for path in paths):
        raise ValueError('Carpeta incompleta o rutas redirigidas')
    manifest_hash = digest(paths[0])
    metadata = json.loads(paths[0].read_text(encoding='utf-8'))
    required = dict(fecha_corte=date,
                    datos_sinteticos=True, ids_autorizados=True,
                    reloj_features='LEGADO_1_4_SIN_ZONA')
    if any(metadata.get(key) != value for key, value in required.items()):
        raise ValueError('Contrato, origen sintético o autorización de IDs incompletos')
    version = metadata.get('contrato')
    if version == 'INFERENCIA_C_NORMALIZADA_V1':
        if metadata.get('corte_disponibilidad_utc') != '2026-08-30T00:00:00Z':
            raise ValueError('V1 conserva UTC00; para otra política usar V2 explícito')
        controls = TemporalControls(date)
    elif version in ('INFERENCIA_C_NORMALIZADA_V2', 'INFERENCIA_C_NORMALIZADA_V3'):
        if not with_controls:
            raise ValueError('V2/V3 requiere devolver controles explícitos; no descartar política temporal')
        if not isinstance(metadata.get('referencia_politica_temporal'), str) or not metadata['referencia_politica_temporal'].strip():
            raise ValueError('V2/V3 exige referencia de decisión temporal, no inferida')
        controls = TemporalControls(date, metadata['corte_disponibilidad_utc'], metadata['corte_efectivo_cdc_utc'])
    else:
        raise ValueError('Versión del contrato no admitida')
    if version == 'INFERENCIA_C_NORMALIZADA_V3':
        validate_normalized_package(metadata, {path.name: digest(path) for path in paths[1:]})
    schemas = [
        {'evento_id', 'tarjeta_id', 'sistema', 'fecha_feature', 'disponible_utc', 'zona', 'gasto_gtq'},
        {'tarjeta_id', 'unidad_id', 'sistema', 'vigente_desde', 'disponible_utc', 'seq'},
        {'tarjeta_id', 'op', 'commit_utc', 'disponible_utc', 'seq'},
    ]
    tables = []
    for path, schema in zip(paths[1:], schemas):
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or len(reader.fieldnames) != len(schema) or set(reader.fieldnames) != schema:
                raise ValueError('Esquema normalizado inválido; no aceptar datasets de entrenamiento')
            tables.append(list(reader))
    if digest(paths[0]) != manifest_hash:
        raise ValueError('Contrato cambió durante la lectura')
    if version == 'INFERENCIA_C_NORMALIZADA_V3':
        validate_normalized_package(metadata, {path.name: digest(path) for path in paths[1:]})
    return (*tables, controls) if with_controls else tables


def _latest(rows, key, order):
    result = {}
    seen = {}
    for row in rows:
        rank = order(row)
        marker = (row[key], rank)
        semantic = {k: v for k, v in row.items() if k != 'disponible_utc'}
        if marker in seen and seen[marker] != semantic:
            raise ValueError('Historia ambigua con igual timestamp/seq')
        seen[marker] = semantic
        if row[key] not in result or rank > order(result[row[key]]):
            result[row[key]] = row
    return result


def build_features(events, identities, cdc, date='2026-08-30', *, controls=None):
    """Filtro temporal ANTES de identidad, deduplicación, población y agregación.

    Eventos usan reloj heredado; disponibilidad y efectividad CDC tienen límites
    independientes. El default V1 conserva UTC00 y V2 debe declararlos. No implica
    simultaneidad de relojes. Correcciones conocidas tarde no reescriben el pasado.
    """
    import pandas as pd

    controls = controls or TemporalControls(date)
    if controls.date != date:
        raise ValueError('Fecha distinta entre controles y features')
    _, end = controls.window()
    available_end = utc_time(controls.availability_utc)
    prior = [r for r in identities if feature_time(r['vigente_desde']) < end
             and utc_time(r['disponible_utc']) < available_end]
    history = [r for r in cdc if utc_time(r['commit_utc']) < utc_time(controls.cdc_effective_utc)
               and utc_time(r['disponible_utc']) < available_end]
    id_map = _latest(prior, 'tarjeta_id', lambda r: (feature_time(r['vigente_desde']), int(r['seq'])))
    state = _latest(history, 'tarjeta_id', lambda r: (utc_time(r['commit_utc']), int(r['seq'])))
    for card, row in id_map.items():
        opaque_id(card, 'CARD'); opaque_id(row['unidad_id'], 'USR')
        if row['sistema'] not in SYSTEMS:
            raise ValueError('Sistema desconocido')
    for row in state.values():
        opaque_id(row['tarjeta_id'], 'CARD')
        if row['op'].upper() not in ('INSERT', 'UPDATE', 'DELETE'):
            raise ValueError('Operación CDC inválida')
    cards_by_unit = {}
    for card, row in id_map.items():
        active = row['sistema'] != 'Transmetro' or state.get(card, {}).get('op', '').upper() != 'DELETE'
        if active:
            cards_by_unit.setdefault(row['unidad_id'], set()).add(card)
    # Historia completa visible para la identidad; ventana de eventos solo previa.
    visible = [r for r in events if end - timedelta(days=28) <= feature_time(r['fecha_feature']) < end
               and utc_time(r['disponible_utc']) < available_end]
    unique = {}
    by_unit = {}
    for row in visible:
        if not row['evento_id'] or None in row or any(value is None for value in row.values()):
            raise ValueError('Evento mal formado')
        marker = (row['sistema'], row['evento_id'])
        semantic = {k: v for k, v in row.items() if k != 'disponible_utc'}
        if marker in unique:
            if unique[marker] != semantic:
                raise ValueError('Corrección histórica ambigua; resolver antes de inferir')
            continue
        unique[marker] = semantic
        card = opaque_id(row['tarjeta_id'], 'CARD')
        if card not in id_map or row['sistema'] != id_map[card]['sistema']:
            raise ValueError('Identidad histórica no reconciliada')
        unit = id_map[card]['unidad_id']
        by_unit.setdefault(unit, []).append(row)

    def rounded(value, digits):
        return float(value.quantize(Decimal(10) ** -digits, rounding=ROUND_HALF_UP))

    rows = []
    for unit in sorted(by_unit):
        items = by_unit[unit]
        if len(items) < 2 or unit not in cards_by_unit:
            continue
        times = [feature_time(r['fecha_feature']) for r in items]
        modes, zones = {}, {}
        total = Decimal(0)
        for row in items:
            cost = Decimal(row['gasto_gtq'] or '0')
            if not cost.is_finite() or cost < 0:
                raise ValueError('Gasto inválido')
            total += cost
            modes[row['sistema']] = modes.get(row['sistema'], 0) + 1
            if row['zona']:
                zones[row['zona']] = zones.get(row['zona'], 0) + 1
        peak = sum(5 <= t.hour <= 8 or 16 <= t.hour <= 19 for t in times)
        rows.append(dict(
            unidad_id=unit, tarjetas=';'.join(sorted(cards_by_unit[unit])),
            eventos_ultimos_7_dias=sum(t >= end - timedelta(days=7) for t in times),
            eventos_ultimos_28_dias=len(items), cantidad_modos_distintos=len(modes),
            dias_desde_ultimo_evento=(end.date() - max(times).date()).days,
            proporcion_eventos_hora_pico=rounded(Decimal(peak) / len(items), 4),
            gasto_acumulado_gtq=rounded(total, 2), gasto_promedio_evento_gtq=rounded(total / len(items), 2),
            modo_mas_usado=min(modes, key=lambda m: (-modes[m], m)),
            zona_origen_mas_frecuente=min(zones, key=lambda z: (-zones[z], z)) if zones else 'DESCONOCIDO',
        ))
    return pd.DataFrame(rows, columns=['unidad_id', 'tarjetas', *FEATURES])
