from pathlib import Path
import csv
import os

import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
BRONZE = RAIZ_PROYECTO / "bronze"

load_dotenv(RAIZ_PROYECTO / ".env")


def conectar():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5434")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


CATALOGOS = {
    "tm_estaciones": {
        "carpeta": BRONZE / "tm_estaciones",
        "esperados": 104,
    },
    "tu_paradas": {
        "carpeta": BRONZE / "tu_paradas",
        "esperados": 328,
    },
    "mr_estaciones": {
        "carpeta": BRONZE / "mr_estaciones",
        "esperados": 22,
    },
    "am_estaciones": {
        "carpeta": BRONZE / "am_estaciones",
        "esperados": 14,
    },
}


def crear_tablas(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS staging.tm_estaciones (
            estacion_id TEXT,
            nombre TEXT,
            linea TEXT,
            zona TEXT,
            lat TEXT,
            lon TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.tu_paradas (
            cod_parada TEXT,
            descripcion TEXT,
            ruta TEXT,
            sector TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.mr_estaciones (
            id_estacion TEXT,
            nombre_estacion TEXT,
            zona_nombre TEXT,
            km TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );

        CREATE TABLE IF NOT EXISTS staging.am_estaciones (
            station_code TEXT,
            station_name TEXT,
            axis TEXT,
            district TEXT,

            raw_value TEXT NOT NULL,
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            ingestion_date DATE NOT NULL,
            source_row_number BIGINT
        );
        """
    )

    cursor.execute(
        """
        TRUNCATE TABLE
            staging.tm_estaciones,
            staging.tu_paradas,
            staging.mr_estaciones,
            staging.am_estaciones;
        """
    )


def leer_bronze(nombre):

    archivos = sorted(
        CATALOGOS[nombre]["carpeta"].rglob("*.parquet")
    )

    registros = []

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            campos = next(
                csv.reader([registro["raw_value"]])
            )

            registros.append(
                (
                    campos,
                    registro["raw_value"],
                    registro["ingestion_timestamp"],
                    registro["ingestion_date"],
                    registro["source_row_number"],
                )
            )

    return registros


def cargar_tm(cursor):

    registros = leer_bronze("tm_estaciones")

    sql = """
        INSERT INTO staging.tm_estaciones
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        );
    """

    filas = [
        (
            *campos,
            raw,
            ts,
            fecha,
            fila,
        )
        for campos, raw, ts, fecha, fila
        in registros
    ]

    cursor.executemany(sql, filas)

    return len(filas)


def cargar_tu(cursor):

    registros = leer_bronze("tu_paradas")

    sql = """
        INSERT INTO staging.tu_paradas
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        );
    """

    filas = [
        (
            *campos,
            raw,
            ts,
            fecha,
            fila,
        )
        for campos, raw, ts, fecha, fila
        in registros
    ]

    cursor.executemany(sql, filas)

    return len(filas)


def cargar_mr(cursor):

    registros = leer_bronze("mr_estaciones")

    sql = """
        INSERT INTO staging.mr_estaciones
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        );
    """

    filas = [
        (
            *campos,
            raw,
            ts,
            fecha,
            fila,
        )
        for campos, raw, ts, fecha, fila
        in registros
    ]

    cursor.executemany(sql, filas)

    return len(filas)


def cargar_am(cursor):

    registros = leer_bronze("am_estaciones")

    sql = """
        INSERT INTO staging.am_estaciones
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        );
    """

    filas = [
        (
            *campos,
            raw,
            ts,
            fecha,
            fila,
        )
        for campos, raw, ts, fecha, fila
        in registros
    ]

    cursor.executemany(sql, filas)

    return len(filas)


def main():

    print("=" * 90)
    print("BRONZE -> STAGING | CATALOGOS DE TRANSPORTE")
    print("=" * 90)

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            crear_tablas(cursor)

            tm = cargar_tm(cursor)
            tu = cargar_tu(cursor)
            mr = cargar_mr(cursor)
            am = cargar_am(cursor)

            cursor.execute(
                """
                SELECT
                    (SELECT COUNT(*)
                     FROM staging.tm_estaciones),

                    (SELECT COUNT(*)
                     FROM staging.tu_paradas),

                    (SELECT COUNT(*)
                     FROM staging.mr_estaciones),

                    (SELECT COUNT(*)
                     FROM staging.am_estaciones);
                """
            )

            tm_db, tu_db, mr_db, am_db = cursor.fetchone()

    resultados = [
        ("TM estaciones", 104, tm, tm_db),
        ("TU paradas", 328, tu, tu_db),
        ("MR estaciones", 22, mr, mr_db),
        ("AM estaciones", 14, am, am_db),
    ]

    print(
        f"{'CATALOGO':<20}"
        f"{'ESPERADO':>15}"
        f"{'BRONZE':>15}"
        f"{'STAGING':>15}"
        f"{'VALIDO':>12}"
    )

    print("-" * 90)

    todo_ok = True

    for nombre, esperado, bronze, staging in resultados:

        ok = (
            esperado == bronze
            and bronze == staging
        )

        if not ok:
            todo_ok = False

        print(
            f"{nombre:<20}"
            f"{esperado:>15,}"
            f"{bronze:>15,}"
            f"{staging:>15,}"
            f"{'SI' if ok else 'NO':>12}"
        )

    print("-" * 90)

    print(
        f"Todos los catalogos coinciden: "
        f"{'SI' if todo_ok else 'NO'}"
    )

    if todo_ok:
        print(
            "RESULTADO: CATALOGOS CARGADOS A STAGING CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: REVISAR CATALOGOS"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()