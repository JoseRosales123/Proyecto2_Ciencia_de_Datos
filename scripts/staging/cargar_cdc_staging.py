from pathlib import Path
from datetime import datetime, date
import csv
import os

import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

BRONZE_CDC = (
    RAIZ_PROYECTO
    / "bronze"
    / "cdc_padron_usuarios"
)

load_dotenv(RAIZ_PROYECTO / ".env")


def conectar():
    return psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def preparar_tabla(cursor):

    cursor.execute(
        """
        CREATE SCHEMA IF NOT EXISTS staging;

        CREATE TABLE IF NOT EXISTS staging.cdc_padron_usuarios (
            seq BIGINT PRIMARY KEY,
            commit_ts TIMESTAMP NOT NULL,
            op VARCHAR(10) NOT NULL,
            tarjeta TEXT NOT NULL,
            perfil TEXT,
            zona_residencia TEXT,
            estado TEXT,

            source_file TEXT NOT NULL,
            source_row_number BIGINT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            raw_value TEXT NOT NULL
        );
        """
    )

    # Staging es temporal/reconstruible.
    # Bronze permanece intacto.
    cursor.execute(
        "TRUNCATE TABLE staging.cdc_padron_usuarios;"
    )


def cargar():

    archivos = sorted(
        BRONZE_CDC.rglob("*.parquet")
    )

    if not archivos:
        raise FileNotFoundError(
            "No se encontraron archivos CDC en Bronze."
        )

    print("=" * 85)
    print("BRONZE -> STAGING | CDC PADRON DE USUARIOS")
    print("=" * 85)
    print(
        f"Archivos Parquet encontrados: "
        f"{len(archivos)}"
    )
    print("=" * 85)

    total = 0

    insert_sql = """
        INSERT INTO staging.cdc_padron_usuarios (
            seq,
            commit_ts,
            op,
            tarjeta,
            perfil,
            zona_residencia,
            estado,
            source_file,
            source_row_number,
            ingestion_timestamp,
            ingestion_date,
            raw_value
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s
        );
    """

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            preparar_tabla(cursor)

            lote = []

            for archivo_parquet in archivos:

                tabla = pq.read_table(
                    archivo_parquet
                )

                for registro in tabla.to_pylist():

                    raw = registro["raw_value"]

                    campos = next(
                        csv.reader([raw])
                    )

                    if len(campos) != 7:
                        raise ValueError(
                            f"Registro CDC inválido: {raw}"
                        )

                    (
                        seq,
                        commit_ts,
                        op,
                        tarjeta,
                        perfil,
                        zona,
                        estado,
                    ) = campos

                    ingestion_timestamp = (
                        datetime.fromisoformat(
                            registro[
                                "ingestion_timestamp"
                            ]
                        )
                    )

                    ingestion_date = (
                        date.fromisoformat(
                            registro[
                                "ingestion_date"
                            ]
                        )
                    )

                    fila = (
                        int(seq),
                        datetime.fromisoformat(
                            commit_ts
                        ),
                        op,
                        tarjeta,
                        perfil or None,
                        zona or None,
                        estado or None,
                        registro["source_file"],
                        registro[
                            "source_row_number"
                        ],
                        ingestion_timestamp,
                        ingestion_date,
                        raw,
                    )

                    lote.append(fila)
                    total += 1

                    if len(lote) >= 5000:

                        cursor.executemany(
                            insert_sql,
                            lote
                        )

                        lote.clear()

            if lote:

                cursor.executemany(
                    insert_sql,
                    lote
                )

            # ------------------------------------------
            # Validaciones
            # ------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(DISTINCT seq) AS secuencias,
                    MIN(seq) AS primera_seq,
                    MAX(seq) AS ultima_seq,
                    COUNT(*) FILTER (
                        WHERE op = 'INSERT'
                    ) AS inserts,
                    COUNT(*) FILTER (
                        WHERE op = 'UPDATE'
                    ) AS updates,
                    COUNT(*) FILTER (
                        WHERE op = 'DELETE'
                    ) AS deletes,
                    COUNT(*) FILTER (
                        WHERE tarjeta = 'SIN-TARJETA'
                    ) AS sin_tarjeta
                FROM staging.cdc_padron_usuarios;
                """
            )

            resultado = cursor.fetchone()

    (
        total_db,
        secuencias,
        primera_seq,
        ultima_seq,
        inserts,
        updates,
        deletes,
        sin_tarjeta,
    ) = resultado

    print("\n" + "=" * 85)
    print("VALIDACION DE STAGING")
    print("=" * 85)

    print(
        f"Registros leídos desde Bronze: "
        f"{total:,}"
    )

    print(
        f"Registros cargados a Staging: "
        f"{total_db:,}"
    )

    print(
        f"Secuencias distintas:         "
        f"{secuencias:,}"
    )

    print(
        f"Rango de secuencia:           "
        f"{primera_seq:,} -> {ultima_seq:,}"
    )

    print("-" * 85)

    print(
        f"INSERT:      {inserts:,}"
    )

    print(
        f"UPDATE:      {updates:,}"
    )

    print(
        f"DELETE:      {deletes:,}"
    )

    print(
        f"SIN-TARJETA: {sin_tarjeta:,}"
    )

    print("-" * 85)

    correcto = (
        total == 31050
        and total_db == 31050
        and secuencias == 31050
        and primera_seq == 1
        and ultima_seq == 31050
    )

    print(
        f"Conteo y secuencia válidos: "
        f"{'SI' if correcto else 'NO'}"
    )

    if correcto:
        print(
            "RESULTADO: CDC CARGADO A STAGING CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: SE ENCONTRARON DIFERENCIAS"
        )

    print("=" * 85)


if __name__ == "__main__":
    cargar()