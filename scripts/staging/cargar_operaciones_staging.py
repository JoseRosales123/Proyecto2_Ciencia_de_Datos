from pathlib import Path
import csv
import json
import os

import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
BRONZE = RAIZ_PROYECTO / "bronze"

load_dotenv(RAIZ_PROYECTO / ".env")


def conectar():
    return psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


FUENTES = {

    "transmetro": {
        "carpeta": BRONZE / "transmetro",
        "tabla": "transmetro_validaciones",
    },

    "transurbano": {
        "carpeta": BRONZE / "transurbano_transacciones",
        "tabla": "transurbano_transacciones",
    },

    "metroriel": {
        "carpeta": BRONZE / "metroriel_viajes",
        "tabla": "metroriel_viajes",
    },

    "aerometro": {
        "carpeta": BRONZE / "aerometro",
        "tabla": "aerometro_boardings",
    },
}


def crear_tablas(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS staging.transmetro_validaciones (
            validation_id TEXT,
            tarjeta TEXT,
            estacion_id TEXT,
            linea TEXT,
            fecha_hora TEXT,
            tarifa TEXT,
            tipo TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            kafka_partition INTEGER,
            kafka_offset BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.transurbano_transacciones (
            fecha TEXT,
            hora TEXT,
            num_tarjeta TEXT,
            cod_parada TEXT,
            ruta TEXT,
            monto_centavos TEXT,
            cod_estado TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.metroriel_viajes (
            trip_id TEXT,
            card TEXT,

            entry_station TEXT,
            entry_ts TEXT,

            exit_station TEXT,
            exit_ts TEXT,

            fare_gtq TEXT,
            duration_s TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.aerometro_boardings (
            boarding_id TEXT,
            user_hash TEXT,
            station_code TEXT,
            axis TEXT,
            timestamp_utc TEXT,
            cabin_number TEXT,
            fare TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            kafka_partition INTEGER,
            kafka_offset BIGINT
        );
        """
    )

    # Staging es reconstruible.
    cursor.execute(
        """
        TRUNCATE TABLE
            staging.transmetro_validaciones,
            staging.transurbano_transacciones,
            staging.metroriel_viajes,
            staging.aerometro_boardings;
        """
    )


def cargar_transmetro(cursor):

    archivos = sorted(
        FUENTES["transmetro"]["carpeta"].rglob("*.parquet")
    )

    sql = """
        INSERT INTO staging.transmetro_validaciones
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        );
    """

    lote = []
    total = 0

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            campos = next(
                csv.reader([registro["raw_value"]])
            )

            lote.append(
                (
                    *campos,
                    registro["raw_value"],
                    registro["ingestion_timestamp"],
                    registro["ingestion_date"],
                    registro["kafka_partition"],
                    registro["kafka_offset"],
                )
            )

            total += 1

            if len(lote) >= 5000:
                cursor.executemany(sql, lote)
                lote.clear()

    if lote:
        cursor.executemany(sql, lote)

    return total


def cargar_transurbano(cursor):

    archivos = sorted(
        FUENTES["transurbano"]["carpeta"].rglob("*.parquet")
    )

    sql = """
        INSERT INTO staging.transurbano_transacciones
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        );
    """

    lote = []
    total = 0

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            campos = next(
                csv.reader([registro["raw_value"]])
            )

            lote.append(
                (
                    *campos,
                    registro["raw_value"],
                    registro["ingestion_timestamp"],
                    registro["ingestion_date"],
                    registro["source_row_number"],
                )
            )

            total += 1

            if len(lote) >= 5000:
                cursor.executemany(sql, lote)
                lote.clear()

    if lote:
        cursor.executemany(sql, lote)

    return total


def cargar_metroriel(cursor):

    archivos = sorted(
        FUENTES["metroriel"]["carpeta"].rglob("*.parquet")
    )

    sql = """
        INSERT INTO staging.metroriel_viajes
        VALUES (
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s,
            %s, %s, %s, %s
        );
    """

    lote = []
    total = 0

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            obj = json.loads(
                registro["raw_value"]
            )

            salida = obj.get("exit")

            lote.append(
                (
                    obj["trip_id"],
                    obj["card"],

                    obj["entry"]["station"],
                    obj["entry"]["ts"],

                    (
                        salida["station"]
                        if salida
                        else None
                    ),

                    (
                        salida["ts"]
                        if salida
                        else None
                    ),

                    obj["fare_gtq"],
                    obj["duration_s"],

                    registro["raw_value"],
                    registro["ingestion_timestamp"],
                    registro["ingestion_date"],
                    registro["source_row_number"],
                )
            )

            total += 1

            if len(lote) >= 5000:
                cursor.executemany(sql, lote)
                lote.clear()

    if lote:
        cursor.executemany(sql, lote)

    return total


def cargar_aerometro(cursor):

    archivos = sorted(
        FUENTES["aerometro"]["carpeta"].rglob("*.parquet")
    )

    sql = """
        INSERT INTO staging.aerometro_boardings
        VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        );
    """

    lote = []
    total = 0

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            campos = next(
                csv.reader([registro["raw_value"]])
            )

            lote.append(
                (
                    *campos,
                    registro["raw_value"],
                    registro["ingestion_timestamp"],
                    registro["ingestion_date"],
                    registro["kafka_partition"],
                    registro["kafka_offset"],
                )
            )

            total += 1

            if len(lote) >= 5000:
                cursor.executemany(sql, lote)
                lote.clear()

    if lote:
        cursor.executemany(sql, lote)

    return total


def main():

    print("=" * 90)
    print("BRONZE -> STAGING | FUENTES OPERATIVAS")
    print("=" * 90)

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            crear_tablas(cursor)

            tm = cargar_transmetro(cursor)
            print(
                f"Transmetro cargado:  {tm:,}"
            )

            tu = cargar_transurbano(cursor)
            print(
                f"Transurbano cargado: {tu:,}"
            )

            mr = cargar_metroriel(cursor)
            print(
                f"MetroRiel cargado:   {mr:,}"
            )

            am = cargar_aerometro(cursor)
            print(
                f"Aerometro cargado:   {am:,}"
            )

            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*)
                     FROM staging.transmetro_validaciones),

                    (SELECT COUNT(*)
                     FROM staging.transurbano_transacciones),

                    (SELECT COUNT(*)
                     FROM staging.metroriel_viajes),

                    (SELECT COUNT(*)
                     FROM staging.aerometro_boardings);
                """
            )

            (
                tm_db,
                tu_db,
                mr_db,
                am_db,
            ) = cursor.fetchone()

    print("-" * 90)

    print(
        f"{'FUENTE':<20}"
        f"{'BRONZE':>15}"
        f"{'STAGING':>15}"
        f"{'VALIDO':>12}"
    )

    print("-" * 90)

    resultados = [
        ("Transmetro", tm, tm_db),
        ("Transurbano", tu, tu_db),
        ("MetroRiel", mr, mr_db),
        ("Aerometro", am, am_db),
    ]

    todo_ok = True

    for nombre, origen, destino in resultados:

        ok = origen == destino

        if not ok:
            todo_ok = False

        print(
            f"{nombre:<20}"
            f"{origen:>15,}"
            f"{destino:>15,}"
            f"{'SI' if ok else 'NO':>12}"
        )

    print("-" * 90)

    print(
        f"Todas las fuentes coinciden: "
        f"{'SI' if todo_ok else 'NO'}"
    )

    if todo_ok:
        print(
            "RESULTADO: OPERACIONES CARGADAS A STAGING CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: REVISAR CONTEOS"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()