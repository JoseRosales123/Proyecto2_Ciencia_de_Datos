"""Preflight y normalizaciones puras del futuro adaptador; NO conecta ni ejecuta SQL.

Los esquemas permiten conversiones, pero no acreditan historia. No fabricar
disponible_utc, vigente_desde ni claves de eventos a partir de fechas arbitrarias.
"""
from scripts.mlops.contrato_c import (
    SYSTEMS, normalize_source_time, normalize_cdc_commit, utc_time, feature_time, opaque_id,
)
from decimal import Decimal
import re


class IntegrationBlocked(ValueError):
    pass


def integration_blockers(evidence):
    """Referencias deben corresponder a pruebas revisadas por el equipo.

    Su presencia es solo control documental: no autentica ni verifica su verdad.
    El ejecutor real permanece no implementado incluso con todas las referencias.
    """
    required = (
        'disponibilidad_historica', 'historia_identidad', 'historia_catalogos',
        'timezone_sesion_transmetro', 'timezone_cdc', 'claves_eventos_transurbano',
        'deduplicacion_point_in_time', 'collation_equivalente',
    )
    missing = [key for key in required if not isinstance(evidence.get(key), str) or not evidence[key].strip()]
    if evidence.get('tipo_disponibilidad') != 'HISTORICA_ACREDITADA':
        missing.append('ingestion_timestamp técnico no acredita disponibilidad histórica')
    return missing


def require_real_ready(evidence):
    blockers = integration_blockers(evidence)
    if blockers:
        raise IntegrationBlocked('Integración bloqueada: ' + '; '.join(blockers))
    # Ninguna referencia declarativa habilita por sí sola un extractor no auditado.
    raise IntegrationBlocked('Extractor PostgreSQL real aún no implementado ni validado; no conectar')


def source_event_window(system, controls, days=28):
    """Aerómetro tiene límite UTC verificable; otras fuentes retienen reloj propio."""
    if system not in SYSTEMS:
        raise ValueError('Sistema desconocido')
    if system == 'Aerometro':
        return dict(clock='UTC_DESDE_AMERICA_GUATEMALA', bounds=controls.aerometro_utc_window(days))
    return dict(clock='RELOJ_FEATURE_HEREDADO_SIN_ZONA', bounds=controls.window(days))


def event_is_visible(system, timestamp, available_utc, controls, *, session_zone=None, reference=None):
    moment = normalize_source_time(system, timestamp, session_zone=session_zone, reference=reference)
    start, end = controls.window()
    return start <= moment < end and utc_time(available_utc) < utc_time(controls.availability_utc)


def normalize_source_cdc(row, *, source_zone=None, reference=None):
    """Solo campos presentes en staging; no crea IDs ni historia de identidad.

    tarjeta real no se devuelve: debe seudonimizarse aparte con namespace estable.
    """
    moment = normalize_cdc_commit(row['commit_ts'], source_zone=source_zone, reference=reference)
    op = row['op'].upper()
    if op not in ('INSERT', 'UPDATE', 'DELETE'):
        raise ValueError('Operación CDC inválida')
    seq = int(row['seq'])
    if seq < 0:
        raise ValueError('Secuencia CDC inválida')
    return dict(commit_utc=moment.isoformat(), op=op, seq=seq,
                ingestion_utc=utc_time(row['ingestion_timestamp']).isoformat(),
                disponibilidad_historica='NO_INFERIDA_DESDE_INGESTION')


def validate_normalized_package(metadata, actual_hashes):
    """Contrato V3 con hashes de los tres CSV y referencias revisables.

    Verifica estructura/integridad, NO autenticidad de referencias ni certificación
    histórica. No habilita el extractor real. No admite fallback de snapshot fijo.
    """
    evidence = metadata.get('proveniencia', {})
    if not isinstance(evidence, dict):
        raise IntegrationBlocked('Proveniencia debe contener referencias documentales')
    blockers = integration_blockers(evidence)
    if blockers:
        raise IntegrationBlocked('Paquete sin evidencia histórica: ' + '; '.join(blockers))
    expected = metadata.get('archivos_sha256', {})
    names = {'eventos.csv', 'identidades.csv', 'cdc.csv'}
    if not isinstance(expected, dict) or set(expected) != names or set(actual_hashes) != names:
        raise ValueError('Inventario de hashes del paquete incorrecto')
    if any(not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value)
           for value in expected.values()) or expected != actual_hashes:
        raise ValueError('Hash de paquete normalizado incorrecto')


def normalize_silver_event(system, row, *, tarjeta_id, available_utc,
                           availability_reference, evidence, source_file_sha256=None):
    """Mapea solo columnas reales de Silver tras extracción PIT ya reconciliada.

    No consulta SQL, no genera historia de identidad ni usa ingestion_timestamp
    como disponible_utc. La fecha de disponibilidad debe suministrarse con evidencia.
    La veracidad de las referencias requiere revisión humana fuera de esta función.
    """
    if system not in SYSTEMS:
        raise ValueError('Fuente desconocida')
    required = {'disponibilidad_historica', 'historia_identidad', 'historia_catalogos', 'deduplicacion_point_in_time'}
    if system == 'Transmetro':
        required.add('timezone_sesion_transmetro')
    if system == 'Transurbano':
        required.add('claves_eventos_transurbano')
    blockers = [key for key in required if not isinstance(evidence.get(key), str) or not evidence[key].strip()]
    if evidence.get('tipo_disponibilidad') != 'HISTORICA_ACREDITADA':
        blockers.append('disponibilidad histórica no acreditada')
    if blockers or not isinstance(availability_reference, str) or not availability_reference.strip():
        raise IntegrationBlocked('No normalizar una fuente sin procedencia histórica revisable')
    if not isinstance(available_utc, str) or not available_utc:
        raise IntegrationBlocked('Falta disponibilidad histórica; no usar ingesta técnica como sustituto')
    token = opaque_id(tarjeta_id, 'CARD')
    available = utc_time(available_utc).isoformat()
    definitions = {
        'Transmetro': ('validacion_id', 'fecha_hora_local', 'tarifa_gtq', 'zona_conformada'),
        'Transurbano': ('source_row_number', 'fecha_hora_local', 'monto_gtq', 'zona_conformada'),
        'MetroRiel': ('trip_id', 'entry_ts', 'fare_gtq', 'zona_origen_conformada'),
        'Aerometro': ('boarding_id', 'timestamp_utc', 'tarifa_gtq', 'zona_conformada'),
    }
    key, time_key, money_key, zone_key = definitions[system]
    identifier = str(row[key])
    if not identifier.isascii() or not identifier.isdigit():
        raise ValueError('Clave de evento/posición inválida')
    if system == 'Transurbano':
        if not isinstance(source_file_sha256, str) or not re.fullmatch('[a-f0-9]{64}', source_file_sha256):
            raise IntegrationBlocked('source_row_number requiere hash de fuente comprobado; no existe source_file en staging TU')
        event_id = f'{system}:{source_file_sha256}:{int(identifier)}'
    else:
        event_id = f'{system}:{int(identifier)}'
    value = row[time_key]
    timestamp = value.isoformat() if hasattr(value, 'isoformat') else value
    if system == 'Transmetro':
        # Esta interfaz consume Silver timestamptz, no el texto crudo staging.
        # La referencia timezone_sesion_transmetro sigue siendo obligatoria.
        moment = utc_time(timestamp).replace(tzinfo=None)
    elif system == 'Aerometro':
        moment = normalize_source_time(system, timestamp)
    else:
        moment = feature_time(timestamp)
    money = Decimal(str(row[money_key])) if row[money_key] is not None else Decimal(0)
    if not money.is_finite() or money < 0:
        raise ValueError('Gasto no admitido por contrato C; revisar semántica con A')
    zone = row[zone_key]
    if zone is not None and not isinstance(zone, str):
        raise ValueError('Zona conformada debe ser texto o NULL')
    return dict(evento_id=event_id, tarjeta_id=token, sistema=system,
                fecha_feature=moment.isoformat(), disponible_utc=available,
                zona=zone if zone is not None else '', gasto_gtq=str(money))
