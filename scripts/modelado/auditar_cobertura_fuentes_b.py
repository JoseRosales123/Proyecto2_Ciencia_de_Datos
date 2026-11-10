"""Integridad y cobertura de fuentes: nunca lee abandono ni datasets por persona.

Importar o usar --help no lee fuentes, manifiestos, .env ni PostgreSQL.
Requiere autorización posterior para consultas agregadas y metadatos de ingesta.
No certifica automáticamente completitud del origen ni habilita el test B.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import uuid

ROOT = Path(__file__).resolve().parents[2]
PHRASE = 'AUTORIZO_AUDITORIA_FUENTES_B'
WINDOWS = [('previa', date(2026, 7, 3), date(2026, 7, 31)),
           ('posterior', date(2026, 7, 31), date(2026, 8, 30))]

# Solo SQL fijo sobre fuentes operativas. No usa usuarios, features por persona,
# etiquetas, exportadores ni modelos. Las expresiones replican dbt y SQL_EVENTOS.
SOURCES = {
    'transmetro': {
        'stage': 'transmetro_validaciones',
        'silver': 'silver_transmetro_validaciones',
        'silver_date': "fecha_hora_local AT TIME ZONE 'UTC'",
        'base': "SELECT to_timestamp(fecha_hora, 'YYYY-MM-DD HH24:MI:SS') "
                "AT TIME ZONE 'UTC' AS fecha, "
                "ROW_NUMBER() OVER (PARTITION BY validation_id "
                "ORDER BY kafka_partition, kafka_offset) > 1 AS rechazado "
                "FROM staging.transmetro_validaciones",
        'rejection': 'duplicado_validation_id', 'stream': True,
    },
    'transurbano': {
        'stage': 'transurbano_transacciones',
        'silver': 'silver_transurbano_transacciones', 'silver_date': 'fecha_hora_local',
        'base': "SELECT to_timestamp(fecha || ' ' || hora, 'DD/MM/YYYY HH24:MI:SS')::timestamp "
                "AS fecha, (NULLIF(TRIM(cod_parada), '') IS NULL OR "
                "to_date(fecha, 'DD/MM/YYYY') > ingestion_date) AS rechazado "
                "FROM staging.transurbano_transacciones",
        'rejection': 'union_parada_nula_o_fecha_futura', 'stream': False,
        'manifest_source': 'transurbano_transacciones',
    },
    'metroriel': {
        'stage': 'metroriel_viajes', 'silver': 'silver_metroriel_viajes',
        'silver_date': 'entry_ts',
        'base': 'SELECT entry_ts::timestamp AS fecha, '
                '(exit_station IS NULL OR exit_ts IS NULL OR duration_s IS NULL) '
                'AS rechazado FROM staging.metroriel_viajes',
        'rejection': 'viaje_sin_salida', 'stream': False,
        'manifest_source': 'metroriel_viajes',
    },
    'aerometro': {
        'stage': 'aerometro_boardings', 'silver': 'silver_aerometro_boardings',
        'silver_date': 'fecha_hora_local',
        'base': "SELECT timestamp_utc::timestamptz AT TIME ZONE 'America/Guatemala' "
                'AS fecha, FALSE AS rechazado FROM staging.aerometro_boardings',
        'rejection': 'ninguno_en_modelo_silver', 'stream': True,
    },
}


def sha(path):
    # Se usa solo sobre código o manifiestos JSON, nunca CSV/Parquet de individuos.
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_csv(path, rows, columns):
    with path.open('x', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def audit_manifests(source):
    """Solo JSON de manifiestos y metadatos de archivos Parquet, no sus columnas."""
    import pyarrow.parquet as pq
    rows = []
    bronze = (ROOT / 'bronze').resolve()
    candidates = sorted((bronze / '_manifests').glob(f'{source}-*.json'))
    for path in candidates:
        manifest = json.loads(path.read_text(encoding='utf-8-sig'))
        records = manifest.get('records')
        expected = manifest.get('expected_records')
        declared_hash = manifest.get('source_file_sha256', '')
        valid = (manifest.get('source') == source and type(records) is int and
                 records >= 0 and type(expected) is int and expected == records and
                 manifest.get('count_matches') is True and
                 isinstance(declared_hash, str) and len(declared_hash) == 64 and
                 all(c in '0123456789abcdef' for c in declared_hash.lower()))
        files = manifest.get('parquet_files', [])
        if not isinstance(files, list) or not files or len(files) != len(set(files)):
            raise ValueError('Inventario de Parquet inválido')
        parquet_rows = 0
        for relative in files:
            target = (ROOT / relative).resolve()
            if not target.is_relative_to(bronze / source) or target.suffix != '.parquet':
                raise ValueError('Ruta de manifiesto fuera de la fuente autorizada')
            parquet_rows += pq.ParquetFile(target).metadata.num_rows
        rows.append({'fuente': source, 'manifiesto_sha256': sha(path),
                     'origen_sha256_declarado': declared_hash if valid else '',
                     'filas_declaradas': records if type(records) is int else None,
                     'filas_metadata_parquet': parquet_rows,
                     'estado': 'APROBADO' if valid and parquet_rows == records else 'BLOQUEANTE'})
    if not rows:
        rows.append({'fuente': source, 'manifiesto_sha256': '',
                     'origen_sha256_declarado': '', 'filas_declaradas': None,
                     'filas_metadata_parquet': None, 'estado': 'PENDIENTE'})
    # No sumar versiones de origen distintas como si fueran una sola ingesta.
    if len(rows) > 1:
        for row in rows:
            if row['estado'] == 'APROBADO':
                row['estado'] = 'PENDIENTE_SELECCION_SNAPSHOT'
    return rows


def auditar():
    # Toda lectura real está detrás de la autorización CLI. Salida nueva por ejecución.
    import psycopg
    from dotenv import load_dotenv
    run = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:12]
    out = ROOT / 'docs/reportes_fase2_2/cobertura_fuentes' / run
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'bitacora.jsonl').open('x', encoding='utf-8') as ledger:
        def event(name, **extra):
            ledger.write(json.dumps({'fecha_utc': datetime.now(timezone.utc).isoformat(),
                                     'evento': name, **extra}) + '\n')
            ledger.flush()
            os.fsync(ledger.fileno())
        event('ANTES_DE_LECTURA_FUENTES')
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                             text=True).strip()
            load_dotenv(ROOT / '.env')
            daily, nulls, offsets, batch, stages = [], [], [], [], []
            with psycopg.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', '5434'),
                user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
                dbname=os.environ['POSTGRES_DB'], autocommit=True,
            ) as connection:
                with connection.cursor() as cur:
                    cur.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
                    try:
                        cur.execute("SET LOCAL TIME ZONE 'UTC'")
                        cur.execute("SET LOCAL statement_timeout = '120s'")
                        cur.execute('SELECT transaction_timestamp()')
                        snapshot_time = cur.fetchone()[0].isoformat()
                        for name, spec in SOURCES.items():
                            # Base SQL clasifica rechazos sin seleccionar personas ni etiquetas.
                            cur.execute(f"WITH base AS ({spec['base']}) SELECT COUNT(*), "
                                        'COUNT(*) FILTER (WHERE fecha IS NULL) FROM base')
                            total, missing_dates = cur.fetchone()
                            stages.append({'fuente': name, 'filas_staging': total})
                            nulls.append({'fuente': name, 'fechas_nulas': missing_dates})
                            for window, start, end in WINDOWS:
                                cur.execute(f"WITH base AS ({spec['base']}) "
                                            'SELECT fecha::date, COUNT(*), '
                                            'COUNT(*) FILTER (WHERE rechazado) FROM base '
                                            'WHERE fecha >= %s AND fecha < %s '
                                            'GROUP BY fecha::date', (start, end))
                                staging_days = {d: (n, rejected) for d, n, rejected in cur.fetchall()}
                                cur.execute(f"SELECT ({spec['silver_date']})::date, COUNT(*) "
                                            f"FROM silver.{spec['silver']} "
                                            f"WHERE ({spec['silver_date']}) >= %s "
                                            f"AND ({spec['silver_date']}) < %s "
                                            f"GROUP BY ({spec['silver_date']})::date", (start, end))
                                silver_days = dict(cur.fetchall())
                                for index in range((end - start).days):
                                    day = start + timedelta(days=index)
                                    n, rejected = staging_days.get(day, (0, 0))
                                    accepted = silver_days.get(day, 0)
                                    daily.append({'fuente': name, 'ventana': window,
                                                  'dia': day.isoformat(), 'staging': n,
                                                  'rechazados_regla': rejected,
                                                  'regla': spec['rejection'], 'silver': accepted,
                                                  'diferencia': n - rejected - accepted,
                                                  'sin_eventos_silver': accepted == 0})
                            if spec['stream']:
                                cur.execute('SELECT kafka_partition, COUNT(*), '
                                            'COUNT(DISTINCT kafka_offset), MIN(kafka_offset), '
                                            'MAX(kafka_offset), COUNT(*) FILTER '
                                            '(WHERE kafka_offset IS NULL) '
                                            f"FROM staging.{spec['stage']} GROUP BY kafka_partition")
                                for partition, n, unique, lo, hi, missing in cur.fetchall():
                                    offsets.append({'fuente': name, 'particion': partition,
                                                    'filas': n, 'offsets_distintos': unique,
                                                    'offset_min': lo, 'offset_max': hi,
                                                    'offsets_nulos': missing,
                                                    'huecos_rango': hi - lo + 1 - unique
                                                    if lo is not None else None})
                            else:
                                cur.execute('SELECT COUNT(*), COUNT(DISTINCT source_row_number), '
                                            'MIN(source_row_number), MAX(source_row_number) '
                                            f"FROM staging.{spec['stage']}")
                                n, unique, lo, hi = cur.fetchone()
                                batch.append({'fuente': name, 'filas': n, 'filas_distintas': unique,
                                              'fila_min': lo, 'fila_max': hi})
                        cur.execute('SELECT COUNT(*), COUNT(DISTINCT seq), MIN(seq), MAX(seq), '
                                    'MIN(commit_ts), MAX(commit_ts), COUNT(*) FILTER '
                                    "(WHERE UPPER(op) NOT IN ('INSERT','UPDATE','DELETE') OR op IS NULL) "
                                    'FROM staging.cdc_padron_usuarios WHERE commit_ts < %s',
                                    (date(2026, 7, 31),))
                        n, unique, lo, hi, first, last, invalid_ops = cur.fetchone()
                        cdc = {'filas_antes_corte': n, 'seq_distintas': unique, 'seq_min': lo,
                               'seq_max': hi, 'commit_min': str(first), 'commit_max': str(last),
                               'operaciones_fuera_dominio': invalid_ops}
                    finally:
                        cur.execute('ROLLBACK')
            manifests = []
            for source in ('transurbano_transacciones', 'metroriel_viajes', 'cdc_padron_usuarios'):
                manifests.extend(audit_manifests(source))
            # Son métricas de integridad; nunca certifican por sí solas el origen completo.
            blockers = []
            if any(row['filas_staging'] == 0 for row in stages):
                blockers.append('Fuente Staging vacía')
            if any(row['diferencia'] != 0 for row in daily):
                blockers.append('Diferencias Staging-rechazos-Silver requieren explicación')
            if any(row['fechas_nulas'] for row in nulls):
                blockers.append('Fechas nulas en fuentes')
            if any(row['estado'] == 'BLOQUEANTE' for row in manifests):
                blockers.append('Manifiestos inconsistentes')
            if any(row['particion'] is None or row['offsets_nulos'] or
                   row['filas'] != row['offsets_distintos'] or row['huecos_rango'] != 0
                   for row in offsets):
                blockers.append('Offsets sin reconciliar con publicación del origen')
            if invalid_ops or n != unique:
                blockers.append('Integridad CDC pendiente de resolución')
            if any(row['filas'] != row['filas_distintas'] or row['fila_min'] != 1 or
                   row['fila_max'] != row['filas_distintas'] for row in batch):
                blockers.append('Numeración Batch incompleta o duplicada; reconciliar con origen')
            for filename, rows in [('cobertura_diaria.csv', daily), ('fechas_nulas.csv', nulls),
                                   ('offsets_streaming.csv', offsets), ('filas_batch.csv', batch),
                                   ('filas_staging.csv', stages), ('manifiestos.csv', manifests)]:
                if rows:
                    save_csv(out / filename, rows, list(rows[0]))
            result = {
                'estado': 'BLOQUEANTE' if blockers else 'PENDIENTE_CERTIFICACION_ORIGEN',
                'certificado': False, 'commit': commit, 'snapshot_db_utc': snapshot_time,
                'sha256_script': sha(Path(__file__)), 'cdc_agregado': cdc,
                'bloqueos_tecnicos': blockers,
                'pendientes': ['Certificado independiente de cobertura y cierre de cada origen',
                               'Hashes origen declarados no recalculados sobre datos individuales',
                               'Reconciliar manifiestos/snapshot con totales de Staging',
                               'Reconciliar offsets con el productor y su origen completo',
                               'Justificar días sin eventos y todos los rechazos',
                               'Certificar catálogos, identidad y estado inicial/historial CDC',
                               'Vincular snapshot DB con metadatos de manifiestos de filesystem'],
                'dias_sin_eventos_silver': sum(row['sin_eventos_silver'] for row in daily),
            }
            with (out / 'resultado.json').open('x', encoding='utf-8') as handle:
                json.dump(result, handle, ensure_ascii=False, indent=2)
            event('FINALIZADO', estado=result['estado'], certificado=False)
            print(f'Auditoría agregada guardada en {out}. No certifica ni habilita el test B.')
        except BaseException as error:
            event('FALLO', tipo=type(error).__name__)
            raise RuntimeError('Auditoría detenida: revisar integridad/configuración, sin revelar datos.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--auditar-fuentes', action='store_true',
                        help='Solo con autorización posterior para fuentes y manifiestos')
    parser.add_argument('--confirmacion', help=f'Debe ser exactamente {PHRASE}')
    args = parser.parse_args()
    if not args.auditar_fuentes:
        parser.print_help()
        return
    if args.confirmacion != PHRASE:
        parser.error('Sin confirmación no se accede a fuentes')
    auditar()


if __name__ == '__main__':
    main()
