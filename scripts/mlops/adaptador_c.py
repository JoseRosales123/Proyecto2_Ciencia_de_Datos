"""Preflight y normalizaciones puras del futuro adaptador; NO conecta ni ejecuta SQL.

Los esquemas permiten conversiones, pero no acreditan historia. No fabricar
disponible_utc, vigente_desde ni claves de eventos a partir de fechas arbitrarias.
"""
from scripts.mlops.contrato_c import (
    SYSTEMS, normalize_source_time, normalize_cdc_commit, utc_time,
)


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
