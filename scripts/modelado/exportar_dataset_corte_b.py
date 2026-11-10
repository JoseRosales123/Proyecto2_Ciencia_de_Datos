"""Preparación reproducible de B; ejecutar solo tras autorización posterior.

Sin --exportar-b solo muestra ayuda. Importar o usar --help no carga .env,
no importa psycopg y no lee datasets ni consulta PostgreSQL.
No evalúa modelos y no revela distribución de etiquetas.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'datos_modelado_local/fase2_2'
OUTPUT = LOCAL / 'dataset_corte_B.csv'
PARTIAL = LOCAL / 'dataset_corte_B.csv.partial'
MANIFEST = LOCAL / 'exportacion_b_manifiesto.json'
LEDGER = LOCAL / 'exportacion_b_bitacora.jsonl'
POLICY = ROOT / 'docs/Fase_2/fase2_2/politica_congelada.json'
CORTE = date(2026, 7, 31)
INICIO = CORTE - timedelta(days=28)
FIN = CORTE + timedelta(days=30)
PHRASE = 'AUTORIZO_EXPORTACION_B'

# Exactamente el orden del COPY de A, más los dos metadatos exigidos por el evaluador.
COLUMNS_A = [
    'usuario_seudonimo', 'eventos_ultimos_7_dias', 'eventos_ultimos_28_dias',
    'modo_mas_usado', 'cantidad_modos_distintos', 'dias_desde_ultimo_evento',
    'proporcion_eventos_hora_pico', 'zona_origen_mas_frecuente',
    'gasto_acumulado_gtq', 'gasto_promedio_evento_gtq', 'abandono',
]
COLUMNS = COLUMNS_A + ['corte', 'fecha_corte']
NUMERIC = [
    'eventos_ultimos_7_dias', 'eventos_ultimos_28_dias',
    'cantidad_modos_distintos', 'dias_desde_ultimo_evento',
    'proporcion_eventos_hora_pico', 'gasto_acumulado_gtq', 'gasto_promedio_evento_gtq',
]
CATEGORICAL = ['modo_mas_usado', 'zona_origen_mas_frecuente']

# Variante local de la consulta de A: solo normaliza op como las features dbt.
# No cambia el historial, los identificadores ni la regla de disponibilidad personal.
SQL_DISPONIBILIDAD_B = """
CREATE TEMP TABLE disponibilidad_12 AS
SELECT
    i.usuario_seudonimo,
    i.sistema || '|' || i.llave_original AS tarjeta_operador,
    CASE
        WHEN i.sistema <> 'Transmetro' THEN TRUE
        WHEN UPPER(c.op) = 'DELETE' THEN FALSE
        ELSE TRUE
    END AS habilitada
FROM silver.silver_identidad_usuarios_seudonimizada i
LEFT JOIN ultimas_cdc_12 c
  ON i.sistema = 'Transmetro'
 AND i.llave_original = c.tarjeta
"""

SQL_FEATURES = """
CREATE TEMP TABLE features_b_22 AS
SELECT * FROM features.feat_abandono_cortes
WHERE corte = 'B' AND fecha_corte = DATE '2026-07-31'
"""

# Solo cardinalidades y verificaciones internas, nunca SUM(abandono) ni distribución.
SQL_AUDITORIA = """
SELECT
    (SELECT COUNT(*) FROM etiquetas_14),
    (SELECT COUNT(*) FROM features_b_22),
    (SELECT COUNT(*) FROM etiquetas_14 e
     FULL JOIN features_b_22 f USING (usuario_seudonimo)
     WHERE e.usuario_seudonimo IS NULL OR f.usuario_seudonimo IS NULL),
    EXISTS (SELECT 1 FROM features_b_22
            WHERE usuario_seudonimo IS NULL OR usuario_seudonimo = ''),
    EXISTS (SELECT 1 FROM features_b_22 GROUP BY usuario_seudonimo HAVING COUNT(*) > 1),
    EXISTS (SELECT 1 FROM features_b_22
            WHERE ultimo_evento_previo IS NULL
               OR ultimo_evento_previo >= DATE '2026-07-31'
               OR ultimo_evento_previo < DATE '2026-07-03'),
    EXISTS (
        SELECT 1 FROM features_b_22 f
        LEFT JOIN (
            SELECT usuario_seudonimo, COUNT(*) AS n, MAX(fecha) AS ultimo
            FROM eventos_12
            WHERE fecha >= DATE '2026-07-03' AND fecha < DATE '2026-07-31'
            GROUP BY usuario_seudonimo
        ) e USING (usuario_seudonimo)
        WHERE e.n IS DISTINCT FROM f.eventos_ultimos_28_dias::bigint
           OR e.ultimo IS DISTINCT FROM f.ultimo_evento_previo
    )
"""

SQL_EXPORT = """
COPY (
    SELECT
        f.usuario_seudonimo,
        f.eventos_ultimos_7_dias, f.eventos_ultimos_28_dias,
        f.modo_mas_usado, f.cantidad_modos_distintos,
        f.dias_desde_ultimo_evento, f.proporcion_eventos_hora_pico,
        f.zona_origen_mas_frecuente,
        f.gasto_acumulado_gtq, f.gasto_promedio_evento_gtq,
        e.abandono, f.corte, f.fecha_corte
    FROM features_b_22 f
    JOIN etiquetas_14 e USING (usuario_seudonimo)
    ORDER BY f.usuario_seudonimo
) TO STDOUT WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')
"""


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def persist(handle, event):
    handle.write(json.dumps({'fecha_utc': datetime.now(timezone.utc).isoformat(),
                             **event}, ensure_ascii=False) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def validate_csv(expected_rows):
    """Verifica el archivo recién exportado en privado; no imprime ni acumula etiquetas."""
    seen = set()
    count = 0
    with PARTIAL.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != COLUMNS:
            raise ValueError('Esquema CSV incompatible')
        for row in reader:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('Fila CSV incompleta')
            identifier = row['usuario_seudonimo']
            if (not identifier.startswith('USR:') or len(identifier) != 68 or
                    any(c not in '0123456789abcdef' for c in identifier[4:]) or
                    identifier in seen):
                raise ValueError('Identidad inválida o duplicada')
            seen.add(identifier)
            if row['corte'] != 'B' or row['fecha_corte'] != CORTE.isoformat():
                raise ValueError('Metadatos de corte inválidos')
            if row['abandono'] not in ('0', '1'):
                raise ValueError('Etiqueta no binaria')
            values = {}
            for column in NUMERIC:
                try:
                    number = Decimal(row[column])
                except InvalidOperation:
                    raise ValueError('Tipo numérico inválido') from None
                if not number.is_finite():
                    raise ValueError('Numérico no finito')
                values[column] = number
            for column in NUMERIC[:4]:
                if values[column] != values[column].to_integral_value():
                    raise ValueError('Conteo o días no enteros')
            if not (values['eventos_ultimos_28_dias'] >= 2 and
                    0 <= values['eventos_ultimos_7_dias'] <= values['eventos_ultimos_28_dias'] and
                    1 <= values['cantidad_modos_distintos'] <= 4 and
                    1 <= values['dias_desde_ultimo_evento'] <= 28 and
                    0 <= values['proporcion_eventos_hora_pico'] <= 1):
                raise ValueError('Características fuera de dominio')
            # Categóricas son texto CSV o vacío: se preservan los nulos para el pipeline.
            count += 1
    if count != expected_rows or not count:
        raise ValueError('Cardinalidad exportada incompatible')


def exportar(coverage_until):
    # Comprobar exclusión sin abrir datasets. No usar un destino configurable.
    for path in (OUTPUT, PARTIAL, MANIFEST, LEDGER):
        relative = path.relative_to(ROOT).as_posix()
        ignored = subprocess.run(['git', 'check-ignore', '-q', '--', relative], cwd=ROOT)
        tracked = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', relative],
                                 cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ignored.returncode != 0 or tracked.returncode == 0:
            raise RuntimeError('El destino local debe estar excluido y no versionado')
        if path.exists():
            raise FileExistsError('Ya existe un artefacto de exportación; no sobrescribir')
    # No exportar si hay una evaluación reservada, autorizada o con resultados previos.
    if any(path.exists() for path in (
        LOCAL / 'test_b_bitacora.jsonl', LOCAL / 'autorizacion_test_b.json',
        ROOT / 'docs/reportes_fase2_2/test_unico_B',
    )):
        raise RuntimeError('Hay artefactos del test único: detener para revisión')
    policy = json.loads(POLICY.read_text(encoding='utf-8'))
    if digest(POLICY) != POLICY.with_suffix('.sha256').read_text(encoding='utf-8').split()[0]:
        raise ValueError('Huella de política incompatible')
    if (policy['estado_b'] != 'NO_EJECUTADO' or policy['estado_politica'] != 'CONGELADA' or
            policy['caracteristicas'] != NUMERIC + CATEGORICAL):
        raise ValueError('Contrato de política incompatible')
    LOCAL.mkdir(parents=True, exist_ok=True)
    # Reserva independiente de la del evaluador; no se borra ni reintenta automáticamente.
    with LEDGER.open('x', encoding='utf-8') as ledger:
        sources = [
            'scripts/modelado/exportar_dataset_corte_b.py',
            'scripts/modelado/exportar_dataset_corte_a.py',
            'scripts/etiquetado/calcular_etiquetas.py',
            'dbt_red_metropolitana/models/features/feat_abandono_cortes.sql',
            'dbt_red_metropolitana/models/silver/silver_identidad_usuarios.sql',
            'dbt_red_metropolitana/models/silver/silver_identidad_usuarios_seudonimizada.sql',
        ]
        persist(ledger, {'evento': 'RESERVA_EXPORTACION', 'estado': 'INICIADO',
                         'politica_sha256': digest(POLICY)})
        try:
            # Importaciones diferidas: no ejecutan main() de los módulos reutilizados.
            import psycopg
            from dotenv import load_dotenv
            sys.path.insert(0, str(ROOT))
            from scripts.etiquetado.calcular_etiquetas import (
                SQL_EVENTOS, SQL_ULTIMAS_OPERACIONES,
                SQL_DISPONIBILIDAD_PERSONA, preparar_fechas,
            )
            from scripts.modelado.exportar_dataset_corte_a import SQL_ETIQUETAS
            load_dotenv(ROOT / '.env')
            params = preparar_fechas(CORTE)
            if params != (INICIO, CORTE, CORTE, FIN, INICIO, FIN):
                raise ValueError('Definición de ventanas modificada')
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                             text=True).strip()
            code_hashes = {source: digest(ROOT / source) for source in sources}
            persist(ledger, {'evento': 'ANTES_DE_CONSULTAR_B', 'commit': commit,
                             'cobertura_declarada_hasta_exclusiva': coverage_until.isoformat()})
            with psycopg.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5434'),
                user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
                dbname=os.environ['POSTGRES_DB'], options='-c timezone=UTC',
                autocommit=True,
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute('BEGIN ISOLATION LEVEL REPEATABLE READ')
                    try:
                        # Solo escrituras temporales, misma sesión/snapshot; rollback siempre.
                        cur.execute(SQL_EVENTOS)
                        cur.execute('SELECT EXISTS (SELECT 1 FROM eventos_12 '
                                    'WHERE usuario_seudonimo IS NULL)')
                        if cur.fetchone()[0]:
                            raise ValueError('Hay eventos sin identidad')
                        cur.execute(SQL_ULTIMAS_OPERACIONES, (CORTE,))
                        cur.execute(SQL_DISPONIBILIDAD_B)
                        cur.execute(SQL_DISPONIBILIDAD_PERSONA)
                        cur.execute(SQL_ETIQUETAS, params)
                        cur.execute('CREATE UNIQUE INDEX ON etiquetas_14 (usuario_seudonimo)')
                        cur.execute(SQL_FEATURES)
                        cur.execute(SQL_AUDITORIA)
                        n_labels, n_features, unmatched, *invalid = cur.fetchone()
                        if not n_labels or n_labels != n_features or unmatched or any(invalid):
                            raise ValueError('Auditoría de integridad fallida')
                        # O_EXCL y archivo parcial: ninguna salida previa se sobrescribe.
                        with PARTIAL.open('xb') as handle:
                            with cur.copy(SQL_EXPORT) as copy:
                                for block in copy:
                                    handle.write(block)
                            handle.flush()
                            os.fsync(handle.fileno())
                        validate_csv(n_labels)
                    finally:
                        cur.execute('ROLLBACK')
            checksum = digest(PARTIAL)
            # Enlace exclusivo: falla si el destino apareció; no usar os.replace().
            # Requiere soporte de hard links en el sistema de archivos local.
            os.link(PARTIAL, OUTPUT)
            PARTIAL.unlink()
            with MANIFEST.open('x', encoding='utf-8') as handle:
                json.dump({
                    'estado': 'EXPORTADO_VALIDADO', 'fecha_utc': datetime.now(timezone.utc).isoformat(),
                    'commit': commit, 'corte': 'B', 'fecha_corte': CORTE.isoformat(),
                    'ventana_features': [INICIO.isoformat(), CORTE.isoformat()],
                    'ventana_etiqueta': [CORTE.isoformat(), FIN.isoformat()],
                    'intervalos': '[inicio, fin)', 'columnas': COLUMNS,
                    'dataset_b_sha256': checksum, 'politica_sha256': digest(POLICY),
                    'sha256_codigo': code_hashes, 'snapshot': 'REPEATABLE READ; UTC',
                    'cobertura_declarada_hasta_exclusiva': coverage_until.isoformat(),
                    'verificaciones': 'esquema, tipos, cardinalidad, unicidad, población y temporalidad',
                    'evaluacion_b': 'NO_EJECUTADO',
                }, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            persist(ledger, {'evento': 'FINALIZADO', 'estado': 'EXPORTADO_VALIDADO',
                             'dataset_b_sha256': checksum})
        except BaseException as error:
            persist(ledger, {'evento': 'FALLO_REQUIERE_REVISION', 'tipo': type(error).__name__})
            # Evitar tracebacks/errores SQL con valores individuales o credenciales.
            raise RuntimeError('Exportación detenida. No borrar artefactos ni reintentar sin revisión.') from None
    print('Exportación local validada. Sin distribución de etiquetas ni evaluación.')
    print('Conservar CSV, manifiesto y bitácora en el directorio privado excluido de Git.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exportar-b', action='store_true',
                        help='Solo con autorización posterior para consultar/exportar B')
    parser.add_argument('--confirmacion', help=f'Debe ser exactamente {PHRASE}')
    parser.add_argument('--cobertura-confirmada-hasta', type=date.fromisoformat,
                        help='Fin exclusivo ISO de cobertura completa certificada por el operador')
    args = parser.parse_args()
    if not args.exportar_b:
        parser.print_help()
        return
    if args.confirmacion != PHRASE:
        parser.error('Falta confirmación explícita; no se ha consultado ningún dato')
    if args.cobertura_confirmada_hasta is None or args.cobertura_confirmada_hasta < FIN:
        parser.error('Debe certificarse cobertura completa hasta 2026-08-30 exclusivo o posterior')
    exportar(args.cobertura_confirmada_hasta)


if __name__ == '__main__':
    main()
