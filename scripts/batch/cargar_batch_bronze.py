
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

DATOS_FUENTE = RAIZ_PROYECTO / "datos_red"
BRONZE = RAIZ_PROYECTO / "bronze"
MANIFESTS = BRONZE / "_manifests"


# ============================================================
# CONFIGURACIÓN DE LAS FUENTES BATCH - PROYECTO 2
# ============================================================

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
        "esperados": 590844,
    },

    "transurbano_transacciones": {
        "archivo": "transurbano_transacciones.csv",
        "sistema": "transurbano",
        "formato": "csv",
        "esperados": 1635788,
    },
}


# ============================================================
# CALCULAR HASH SHA-256
# ============================================================

def calcular_sha256(ruta):
    sha256 = hashlib.sha256()

    with ruta.open("rb") as archivo:
        for bloque in iter(
            lambda: archivo.read(1024 * 1024),
            b""
        ):
            sha256.update(bloque)

    return sha256.hexdigest()


# ============================================================
# ESCRIBIR LOTE EN PARQUET
# ============================================================

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

    # Escribir primero en un archivo temporal para evitar
    # que un lote incompleto se interprete como válido.
    ruta_temporal = ruta.with_suffix(".parquet.tmp")

    try:
        pq.write_table(
            tabla,
            ruta_temporal,
            compression="snappy"
        )

        ruta_temporal.replace(ruta)

    finally:
        if ruta_temporal.exists():
            ruta_temporal.unlink()

    print(
        f"Bronze -> "
        f"{ruta.relative_to(RAIZ_PROYECTO)} "
        f"({len(registros):,} registros)"
    )

    return ruta


# ============================================================
# CARGAR UNA FUENTE BATCH
# ============================================================

def cargar_fuente(fuente, batch_size=50000):

    if batch_size <= 0:
        raise ValueError(
            "El tamaño del lote debe ser mayor que cero."
        )

    config = FUENTES[fuente]

    ruta_fuente = DATOS_FUENTE / config["archivo"]

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
    print("CARGA BATCH -> BRONZE | PROYECTO 2")
    print("=" * 80)
    print(f"Fuente:              {fuente}")
    print(f"Archivo:             {config['archivo']}")
    print(f"Sistema:             {config['sistema']}")
    print(f"Formato:             {config['formato'].upper()}")
    print(f"SHA-256:             {sha256}")
    print(f"Registros esperados: {config['esperados']:,}")
    print("=" * 80)

    # --------------------------------------------------------
    # IDEMPOTENCIA
    # --------------------------------------------------------

    if ruta_manifest.exists():

        with ruta_manifest.open(
            "r",
            encoding="utf-8"
        ) as archivo:
            manifest_existente = json.load(archivo)

        archivos_manifest = [
            RAIZ_PROYECTO / ruta
            for ruta in manifest_existente.get(
                "parquet_files", []
            )
        ]

        manifest_valido = (
            manifest_existente.get("source_file_sha256")
            == sha256
            and manifest_existente.get("records")
            == config["esperados"]
            and manifest_existente.get("count_matches")
            is True
            and len(archivos_manifest) > 0
            and all(
                ruta.is_file()
                for ruta in archivos_manifest
            )
        )

        if not manifest_valido:
            raise RuntimeError(
                f"El manifiesto de {fuente} existe, "
                "pero está incompleto o no es válido. "
                "Se requiere revisar Bronze antes "
                "de continuar."
            )

        registros_parquet = sum(
            pq.ParquetFile(ruta).metadata.num_rows
            for ruta in archivos_manifest
        )

        if registros_parquet != config["esperados"]:
            raise RuntimeError(
                f"El manifiesto de {fuente} existe, "
                "pero los archivos Parquet no tienen "
                "el conteo esperado."
            )

        print(
            "\nEl archivo ya fue cargado anteriormente."
        )
        print(
            "Se verificaron el manifiesto y sus "
            "archivos Parquet."
        )
        print(
            "RESULTADO: CARGA OMITIDA POR IDEMPOTENCIA"
        )

        return

    # --------------------------------------------------------
    # METADATOS DE INGESTA
    # --------------------------------------------------------

    ahora = datetime.now(timezone.utc)

    ingestion_timestamp = ahora.isoformat()
    ingestion_date = ahora.date().isoformat()

    registros = []
    total = 0
    archivos_creados = []

    try:

        # ----------------------------------------------------
        # CSV
        # ----------------------------------------------------

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

                        archivos_creados.append(ruta)
                        registros.clear()

        # ----------------------------------------------------
        # JSON LINES
        # ----------------------------------------------------

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

                        archivos_creados.append(ruta)
                        registros.clear()

        else:
            raise ValueError(
                f"Formato no soportado: "
                f"{config['formato']}"
            )

        # ----------------------------------------------------
        # ÚLTIMO LOTE
        # ----------------------------------------------------

        if registros:

            ruta = escribir_lote(
                registros,
                fuente,
                hash_corto,
                ingestion_date,
            )

            archivos_creados.append(ruta)

        # ----------------------------------------------------
        # VALIDACIÓN DE CONTEO
        # ----------------------------------------------------

        coincide = total == config["esperados"]

        print("\n" + "=" * 80)
        print("VALIDACIÓN DE CARGA BATCH")
        print("=" * 80)
        print(
            f"Registros esperados: "
            f"{config['esperados']:,}"
        )
        print(
            f"Registros cargados:  {total:,}"
        )
        print(
            f"Diferencia:          "
            f"{total - config['esperados']:,}"
        )
        print(
            f"Conteo coincide:     "
            f"{'SI' if coincide else 'NO'}"
        )
        print(
            f"Archivos Parquet:    "
            f"{len(archivos_creados)}"
        )

        if not coincide:
            raise RuntimeError(
                f"Carga Batch fallida para {fuente}: "
                f"esperados={config['esperados']}, "
                f"cargados={total}"
            )

        # Comprobar que los lotes escritos contienen
        # exactamente el número esperado de registros.
        total_parquet = sum(
            pq.ParquetFile(ruta).metadata.num_rows
            for ruta in archivos_creados
        )

        if total_parquet != total:
            raise RuntimeError(
                f"Diferencia entre los registros leídos "
                f"y los archivos Parquet de {fuente}: "
                f"leídos={total}, parquet={total_parquet}"
            )

        # ----------------------------------------------------
        # MANIFIESTO: SOLO DESPUÉS DE VALIDAR
        # ----------------------------------------------------

        manifest = {
            "source": fuente,
            "source_file": config["archivo"],
            "source_file_sha256": sha256,
            "ingestion_timestamp": ingestion_timestamp,
            "ingestion_date": ingestion_date,
            "records": total,
            "expected_records": config["esperados"],
            "count_matches": True,
            "parquet_files": [
                str(ruta.relative_to(RAIZ_PROYECTO))
                for ruta in archivos_creados
            ],
        }

        ruta_manifest_temporal = (
            ruta_manifest.with_suffix(".json.tmp")
        )

        try:
            with ruta_manifest_temporal.open(
                "w",
                encoding="utf-8"
            ) as archivo:

                json.dump(
                    manifest,
                    archivo,
                    indent=4,
                    ensure_ascii=False
                )

            ruta_manifest_temporal.replace(
                ruta_manifest
            )

        finally:
            if ruta_manifest_temporal.exists():
                ruta_manifest_temporal.unlink()

        print(
            "RESULTADO: CARGA BATCH COMPLETADA CORRECTAMENTE"
        )
        print("=" * 80)

    except Exception:

        # Eliminar solamente los Parquet asociados a
        # esta fuente y a esta ejecución fallida.
        for ruta in archivos_creados:
            if ruta.exists():
                ruta.unlink()

        # Un manifiesto inválido no debe marcar la
        # carga como completada.
        if ruta_manifest.exists():
            try:
                with ruta_manifest.open(
                    "r",
                    encoding="utf-8"
                ) as archivo:
                    manifest_actual = json.load(archivo)

                if (
                    manifest_actual.get("source_file_sha256")
                    == sha256
                    and manifest_actual.get(
                        "ingestion_timestamp"
                    ) == ingestion_timestamp
                ):
                    ruta_manifest.unlink()

            except (OSError, ValueError):
                pass

        raise


# ============================================================
# EJECUCIÓN POR TERMINAL
# ============================================================

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
