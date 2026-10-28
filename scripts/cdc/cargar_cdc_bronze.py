from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

ARCHIVO_FUENTE = (
    RAIZ_PROYECTO
    / "datos_fuente"
    / "cdc_padron_usuarios.csv"
)

BRONZE = RAIZ_PROYECTO / "bronze"
MANIFESTS = BRONZE / "_manifests"

FUENTE = "cdc_padron_usuarios"
ESPERADOS = 31050
BATCH_SIZE = 10000


def calcular_sha256(ruta):
    sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:
        for bloque in iter(
            lambda: archivo.read(1024 * 1024),
            b""
        ):
            sha256.update(bloque)

    return sha256.hexdigest()


def escribir_lote(
    registros,
    hash_corto,
    ingestion_date
):
    if not registros:
        return None

    carpeta = (
        BRONZE
        / FUENTE
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


def cargar():

    if not ARCHIVO_FUENTE.exists():
        raise FileNotFoundError(
            f"No existe {ARCHIVO_FUENTE}"
        )

    MANIFESTS.mkdir(
        parents=True,
        exist_ok=True
    )

    sha256 = calcular_sha256(
        ARCHIVO_FUENTE
    )

    hash_corto = sha256[:12]

    manifest_path = (
        MANIFESTS
        / f"{FUENTE}-{hash_corto}.json"
    )

    print("=" * 80)
    print("INGESTA CDC -> BRONZE")
    print("=" * 80)

    print(
        f"Archivo:             "
        f"{ARCHIVO_FUENTE.name}"
    )

    print(
        f"SHA-256:             "
        f"{sha256}"
    )

    print(
        f"Registros esperados: "
        f"{ESPERADOS:,}"
    )

    print("=" * 80)

    # --------------------------------------------------
    # Idempotencia
    # --------------------------------------------------

    if manifest_path.exists():

        print(
            "\nEl archivo CDC ya fue ingerido anteriormente."
        )

        print(
            "No se realizará una segunda carga."
        )

        print(
            "RESULTADO: CARGA OMITIDA POR IDEMPOTENCIA"
        )

        return

    ahora = datetime.now(timezone.utc)

    ingestion_timestamp = ahora.isoformat()
    ingestion_date = ahora.date().isoformat()

    total = 0
    registros = []
    archivos_creados = []

    with ARCHIVO_FUENTE.open(
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
                "source_system": "transmetro_cdc",
                "source_file": ARCHIVO_FUENTE.name,
                "source_file_sha256": sha256,
                "source_row_number": numero_fila,
                "source_header": encabezado,
                "raw_value": raw_value,
                "ingestion_timestamp": ingestion_timestamp,
                "ingestion_date": ingestion_date,
            }

            registros.append(registro)
            total += 1

            if len(registros) >= BATCH_SIZE:

                ruta = escribir_lote(
                    registros,
                    hash_corto,
                    ingestion_date
                )

                archivos_creados.append(
                    str(
                        ruta.relative_to(
                            RAIZ_PROYECTO
                        )
                    )
                )

                registros.clear()

    if registros:

        ruta = escribir_lote(
            registros,
            hash_corto,
            ingestion_date
        )

        archivos_creados.append(
            str(
                ruta.relative_to(
                    RAIZ_PROYECTO
                )
            )
        )

    coincide = total == ESPERADOS

    manifest = {
        "source": FUENTE,
        "source_file": ARCHIVO_FUENTE.name,
        "source_file_sha256": sha256,
        "ingestion_timestamp": ingestion_timestamp,
        "ingestion_date": ingestion_date,
        "records": total,
        "expected_records": ESPERADOS,
        "count_matches": coincide,
        "parquet_files": archivos_creados,
    }

    with manifest_path.open(
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
        f"Registros esperados: "
        f"{ESPERADOS:,}"
    )

    print(
        f"Registros cargados:  "
        f"{total:,}"
    )

    print(
        f"Conteo coincide:     "
        f"{'SI' if coincide else 'NO'}"
    )

    print(
        f"Archivos Parquet:    "
        f"{len(archivos_creados)}"
    )

    print("=" * 80)

    if coincide:

        print(
            "RESULTADO: CDC CARGADO A BRONZE CORRECTAMENTE"
        )

    else:

        print(
            "RESULTADO: SE ENCONTRARON DIFERENCIAS"
        )

    print("=" * 80)


if __name__ == "__main__":
    cargar()