from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

DATOS_FUENTE = RAIZ_PROYECTO / "datos_fuente"
BRONZE = RAIZ_PROYECTO / "bronze"
MANIFESTS = BRONZE / "_manifests"


FUENTES = {
    "tm_estaciones": {
        "archivo": "tm_estaciones.csv",
        "sistema": "transmetro",
        "formato": "csv",
        "esperados": 104,
    },

    "tu_paradas": {
        "archivo": "tu_paradas.csv",
        "sistema": "transurbano",
        "formato": "csv",
        "esperados": 328,
    },

    "mr_estaciones": {
        "archivo": "mr_estaciones.csv",
        "sistema": "metroriel",
        "formato": "csv",
        "esperados": 22,
    },

    "am_estaciones": {
        "archivo": "am_estaciones.csv",
        "sistema": "aerometro",
        "formato": "csv",
        "esperados": 14,
    },

    "metroriel_viajes": {
        "archivo": "metroriel_viajes.jsonl",
        "sistema": "metroriel",
        "formato": "jsonl",
        "esperados": 299100,
    },

    "transurbano_transacciones": {
        "archivo": "transurbano_transacciones.csv",
        "sistema": "transurbano",
        "formato": "csv",
        "esperados": 832791,
    },
}


def calcular_sha256(ruta):
    sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            sha256.update(bloque)

    return sha256.hexdigest()


def escribir_lote(
    registros,
    fuente,
    hash_corto,
    ingestion_date,
):
    if not registros:
        return None

    carpeta = (
        BRONZE
        / fuente
        / f"ingestion_date={ingestion_date}"
    )

    carpeta.mkdir(
        parents=True,
        exist_ok=True
    )

    fila_inicio = registros[0]["source_row_number"]
    fila_fin = registros[-1]["source_row_number"]

    nombre = (
        f"part-{hash_corto}-"
        f"{fila_inicio:012d}-"
        f"{fila_fin:012d}.parquet"
    )

    ruta = carpeta / nombre

    tabla = pa.Table.from_pylist(registros)

    pq.write_table(
        tabla,
        ruta,
        compression="snappy"
    )

    print(
        f"Bronze -> "
        f"{ruta.relative_to(RAIZ_PROYECTO)} "
        f"({len(registros):,} registros)"
    )

    return ruta


def cargar_fuente(fuente, batch_size=50000):

    config = FUENTES[fuente]

    ruta_fuente = (
        DATOS_FUENTE
        / config["archivo"]
    )

    if not ruta_fuente.exists():
        raise FileNotFoundError(
            f"No existe el archivo: {ruta_fuente}"
        )

    MANIFESTS.mkdir(
        parents=True,
        exist_ok=True
    )

    sha256 = calcular_sha256(ruta_fuente)
    hash_corto = sha256[:12]

    ruta_manifest = (
        MANIFESTS
        / f"{fuente}-{hash_corto}.json"
    )

    print("=" * 80)
    print("CARGA BATCH -> BRONZE")
    print("=" * 80)
    print(f"Fuente:            {fuente}")
    print(f"Archivo:           {config['archivo']}")
    print(f"Sistema:           {config['sistema']}")
    print(f"Formato:           {config['formato'].upper()}")
    print(f"SHA-256:           {sha256}")
    print(f"Registros esperados: {config['esperados']:,}")
    print("=" * 80)

    # -----------------------------------------------------
    # Idempotencia
    # -----------------------------------------------------

    if ruta_manifest.exists():

        print(
            "\nEl archivo ya fue cargado anteriormente."
        )

        print(
            "No se realizará una segunda carga."
        )

        print(
            "RESULTADO: CARGA OMITIDA POR IDEMPOTENCIA"
        )

        return

    # -----------------------------------------------------
    # Metadatos de ingesta
    # -----------------------------------------------------

    ahora = datetime.now(timezone.utc)

    ingestion_timestamp = ahora.isoformat()
    ingestion_date = ahora.date().isoformat()

    registros = []
    total = 0
    archivos_creados = []

    # -----------------------------------------------------
    # CSV
    # -----------------------------------------------------

    if config["formato"] == "csv":

        with ruta_fuente.open(
            "r",
            encoding="utf-8-sig"
        ) as archivo:

            encabezado = (
                archivo.readline()
                .rstrip("\r\n")
            )

            for numero_fila, linea in enumerate(
                archivo,
                start=1
            ):

                raw_value = linea.rstrip("\r\n")

                if not raw_value:
                    continue

                registro = {
                    "source_system": config["sistema"],
                    "source_file": config["archivo"],
                    "source_file_sha256": sha256,
                    "source_row_number": numero_fila,
                    "source_header": encabezado,
                    "raw_value": raw_value,
                    "ingestion_timestamp": ingestion_timestamp,
                    "ingestion_date": ingestion_date,
                }

                registros.append(registro)
                total += 1

                if len(registros) >= batch_size:

                    ruta = escribir_lote(
                        registros,
                        fuente,
                        hash_corto,
                        ingestion_date,
                    )

                    archivos_creados.append(
                        str(ruta.relative_to(RAIZ_PROYECTO))
                    )

                    registros.clear()

    # -----------------------------------------------------
    # JSON Lines
    # -----------------------------------------------------

    elif config["formato"] == "jsonl":

        with ruta_fuente.open(
            "r",
            encoding="utf-8"
        ) as archivo:

            for numero_fila, linea in enumerate(
                archivo,
                start=1
            ):

                raw_value = linea.rstrip("\r\n")

                if not raw_value:
                    continue

                registro = {
                    "source_system": config["sistema"],
                    "source_file": config["archivo"],
                    "source_file_sha256": sha256,
                    "source_row_number": numero_fila,
                    "source_header": None,
                    "raw_value": raw_value,
                    "ingestion_timestamp": ingestion_timestamp,
                    "ingestion_date": ingestion_date,
                }

                registros.append(registro)
                total += 1

                if len(registros) >= batch_size:

                    ruta = escribir_lote(
                        registros,
                        fuente,
                        hash_corto,
                        ingestion_date,
                    )

                    archivos_creados.append(
                        str(ruta.relative_to(RAIZ_PROYECTO))
                    )

                    registros.clear()

    # -----------------------------------------------------
    # Último lote
    # -----------------------------------------------------

    if registros:

        ruta = escribir_lote(
            registros,
            fuente,
            hash_corto,
            ingestion_date,
        )

        archivos_creados.append(
            str(ruta.relative_to(RAIZ_PROYECTO))
        )

    # -----------------------------------------------------
    # Validación
    # -----------------------------------------------------

    coincide = (
        total == config["esperados"]
    )

    manifest = {
        "source": fuente,
        "source_file": config["archivo"],
        "source_file_sha256": sha256,
        "ingestion_timestamp": ingestion_timestamp,
        "ingestion_date": ingestion_date,
        "records": total,
        "expected_records": config["esperados"],
        "count_matches": coincide,
        "parquet_files": archivos_creados,
    }

    with ruta_manifest.open(
        "w",
        encoding="utf-8"
    ) as archivo:

        json.dump(
            manifest,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    print("\n" + "=" * 80)

    print(
        f"Registros esperados:   "
        f"{config['esperados']:,}"
    )

    print(
        f"Registros cargados:    "
        f"{total:,}"
    )

    print(
        f"Conteo coincide:       "
        f"{'SI' if coincide else 'NO'}"
    )

    print(
        f"Archivos Parquet:      "
        f"{len(archivos_creados)}"
    )

    print("=" * 80)

    if coincide:
        print(
            "RESULTADO: CARGA BATCH COMPLETADA CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: SE ENCONTRARON DIFERENCIAS"
        )

    print("=" * 80)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        choices=list(FUENTES.keys()) + ["all"],
        required=True,
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000,
    )

    args = parser.parse_args()

    if args.source == "all":

        for nombre_fuente in FUENTES:

            cargar_fuente(
                nombre_fuente,
                args.batch_size,
            )

            print("\n")

    else:

        cargar_fuente(
            args.source,
            args.batch_size,
        )