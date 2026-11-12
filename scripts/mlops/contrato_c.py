"""Contrato C independiente de A/B. Importar no lee datos ni carga modelos."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib
import json
import re
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'docs/Fase_2/fase2_2/politica_congelada.json'
MODEL_DIR = ROOT / 'modelos/fase2_4'
NUMERIC = (
    'eventos_ultimos_7_dias', 'eventos_ultimos_28_dias',
    'cantidad_modos_distintos', 'dias_desde_ultimo_evento',
    'proporcion_eventos_hora_pico', 'gasto_acumulado_gtq', 'gasto_promedio_evento_gtq',
)
CATEGORICAL = ('modo_mas_usado', 'zona_origen_mas_frecuente')
FEATURES = NUMERIC + CATEGORICAL
SYSTEMS = ('Transmetro', 'Transurbano', 'MetroRiel', 'Aerometro')


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def cutoff(value):
    if value != '2026-08-30':
        raise ValueError('Solo se admite corte C=2026-08-30')
    return datetime(2026, 8, 30)


def feature_time(value):
    """Reloj de features heredado, explícitamente SIN zona; no UTC uniforme."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        raise ValueError('fecha_feature/vigente_desde requiere reloj heredado sin zona')
    return parsed


def utc_time(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp de disponibilidad/CDC requiere zona')
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class TemporalControls:
    """Eventos por reloj propio; disponibilidad y efectividad CDC independientes.

    Defaults conservan explícitamente el prototipo V1, NO un contrato A/B.
    UTC06 es una alternativa a revisar, nunca un cambio automático de default.
    """
    date: str = '2026-08-30'
    availability_utc: str = '2026-08-30T00:00:00Z'
    cdc_effective_utc: str = '2026-08-30T00:00:00Z'

    def __post_init__(self):
        cutoff(self.date)
        allowed = {utc_time('2026-08-30T00:00:00Z'), utc_time('2026-08-30T06:00:00Z')}
        if utc_time(self.availability_utc) not in allowed or utc_time(self.cdc_effective_utc) not in allowed:
            raise ValueError('Cortes UTC permitidos explícitamente: UTC00 o UTC06')

    def window(self, days=28):
        if days not in (7, 28):
            raise ValueError('Solo ventanas 7/28 días')
        end = cutoff(self.date)
        return end - timedelta(days=days), end

    def aerometro_utc_window(self, days=28):
        start, end = self.window(days)
        zone = ZoneInfo('America/Guatemala')
        return (start.replace(tzinfo=zone).astimezone(timezone.utc),
                end.replace(tzinfo=zone).astimezone(timezone.utc))


def normalize_source_time(system, value, *, session_zone=None, reference=None):
    """Conversión pura del evento según SQL existente, no disponibilidad.

    Transmetro: to_timestamp(texto) depende de sesión; AT TIME ZONE UTC produce
    timestamp sin zona. Exigir zona documentada evita asumir una sesión histórica.
    TU/MR ya deben ser relojes civiles sin zona según SQL. No extrapolar UTC-6.
    """
    if system == 'Aerometro':
        return utc_time(value).astimezone(ZoneInfo('America/Guatemala')).replace(tzinfo=None)
    if system == 'Transmetro':
        if not session_zone or not reference or not reference.strip():
            raise ValueError('Transmetro requiere timezone de sesión y referencia verificable')
        return feature_time(value).replace(tzinfo=ZoneInfo(session_zone)).astimezone(timezone.utc).replace(tzinfo=None)
    if system in ('Transurbano', 'MetroRiel'):
        return feature_time(value)
    raise ValueError('Fuente desconocida')


def normalize_cdc_commit(value, *, source_zone=None, reference=None):
    """commit_ts real es TIMESTAMP sin zona; nunca agregar Z sin evidencia."""
    if not source_zone or not reference or not reference.strip():
        raise ValueError('CDC sin zona: interpretación y evidencia obligatorias')
    return feature_time(value).replace(tzinfo=ZoneInfo(source_zone)).astimezone(timezone.utc)


def opaque_id(value, prefix):
    if not isinstance(value, str) or not re.fullmatch(prefix + r':[0-9a-f]{64}', value):
        raise ValueError('Solo IDs seudonimizados del contrato autorizado')
    return value


def policy_contract():
    """Comprueba huellas antes de importar constructores históricos; nunca lee B."""
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    if digest(POLICY) != POLICY.with_suffix('.sha256').read_text().split()[0]:
        raise ValueError('Sidecar de política incorrecto')
    if policy['caracteristicas'] != list(FEATURES) or policy['umbral'] != {
        'numerador': 1, 'denominador': 3, 'comparador': '>='
    } or policy['modelo'] != 'LogisticRegression L1' or policy['hiperparametros']['C'] != 1:
        raise ValueError('Contrato congelado incompatible')
    for relative, expected in policy['sha256_codigo'].items():
        path = ROOT / relative
        if not path.resolve().is_relative_to(ROOT.resolve()) or digest(path) != expected:
            raise ValueError('Código histórico diferente del congelado')
    return policy


def check_versions(policy):
    import numpy
    import pandas
    import sklearn
    versions = dict(numpy=numpy.__version__, pandas=pandas.__version__, sklearn=sklearn.__version__)
    if versions != policy['versiones']:
        raise ValueError('Versiones distintas a las congeladas')
    return versions
