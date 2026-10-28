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


FUENTES = {
    "transurbano": {
        "carpeta": BRONZE / "transurbano_transacciones",
        "tabla": "usuarios_transurbano",
        "columna": "num_tarjeta",
        "formato": "csv",
        "indice_llave": 2,
    },

    "metroriel": {
        "carpeta": BRONZE / "metroriel_viajes",
        "tabla": "usuarios_metroriel",
        "columna": "card",
        "formato": "jsonl",
    },

    "aerometro": {
        "carpeta": BRONZE / "aerometro",
        "tabla": "usuarios_aerometro",
        "columna": "user_hash",
        "formato": "csv",
        "indice_llave": 1,
    },
}


def conectar():
    return psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def extraer_llaves(config):

    archivos = sorted(
        config["carpeta"].rglob("*.parquet")
    )

    if not archivos:
        raise FileNotFoundError(
            f"No se encontraron Parquet en {config['carpeta']}"
        )

    llaves = set()
    registros_leidos = 0

    for archivo in archivos:

        tabla = pq.read_table(archivo)

        for registro in tabla.to_pylist():

            raw = registro["raw_value"]

            # -------------------------------------
            # CSV
            # -------------------------------------
            if config["formato"] == "csv":

                campos = next(
                    csv.reader([raw])
                )

                llave = campos[
                    config["indice_llave"]
                ].strip()

            # -------------------------------------
            # JSON Lines
            # -------------------------------------
            else:

                objeto = json.loads(raw)

                llave = objeto["card"]

            registros_leidos += 1

            if llave:
                llaves.add(llave)

    return registros_leidos, llaves


def crear_tabla(
    cursor,
    tabla,
    columna
):

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS staging.{tabla} (
            {columna} TEXT PRIMARY KEY
        );
        """
    )

    cursor.execute(
        f"""
        TRUNCATE TABLE staging.{tabla};
        """
    )


def cargar_catalogo(
    cursor,
    tabla,
    columna,
    llaves
):

    sql = f"""
        INSERT INTO staging.{tabla} (
            {columna}
        )
        VALUES (%s);
    """

    cursor.executemany(
        sql,
        [(llave,) for llave in sorted(llaves)]
    )


def main():

    resultados = []

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            for nombre, config in FUENTES.items():

                registros_leidos, llaves = (
                    extraer_llaves(config)
                )

                crear_tabla(
                    cursor,
                    config["tabla"],
                    config["columna"],
                )

                cargar_catalogo(
                    cursor,
                    config["tabla"],
                    config["columna"],
                    llaves,
                )

                cursor.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM staging.{config['tabla']};
                    """
                )

                cargados = cursor.fetchone()[0]

                resultados.append(
                    (
                        nombre,
                        registros_leidos,
                        len(llaves),
                        cargados,
                    )
                )

    print("=" * 90)
    print("CATALOGOS MINIMOS DE USUARIOS")
    print("=" * 90)

    print(
        f"{'OPERADOR':<20}"
        f"{'REGISTROS OPERACION':>22}"
        f"{'USUARIOS UNICOS':>20}"
        f"{'CATALOGO':>15}"
    )

    print("-" * 90)

    todo_correcto = True

    for (
        nombre,
        registros,
        unicos,
        cargados,
    ) in resultados:

        correcto = unicos == cargados

        if not correcto:
            todo_correcto = False

        print(
            f"{nombre:<20}"
            f"{registros:>22,}"
            f"{unicos:>20,}"
            f"{cargados:>15,}"
        )

    print("-" * 90)

    print(
        f"Todos los catalogos coinciden: "
        f"{'SI' if todo_correcto else 'NO'}"
    )

    if todo_correcto:
        print(
            "RESULTADO: CATALOGOS MINIMOS CONSTRUIDOS CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: REVISAR CATALOGOS"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()