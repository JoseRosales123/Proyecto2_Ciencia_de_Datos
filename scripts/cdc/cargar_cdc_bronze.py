
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

import pyarrow as pa
import pyarrow.parquet as pq


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

ARCHIVO_FUENTE = (
    RAIZ_PROYECTO
    / "datos_red"
    / "cdc_padron_usuarios.csv"
)

BRONZE = RAIZ_PROYECTO / "bronze"
MANIFESTS = BRONZE / "_manifests"

FUENTE = "cdc_padron_usuarios"
ESPERADOS = 77636
BATCH_SIZE = 10000


# ============================================================
# CALCULAR SHA-256
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
# ESCRIBIR LOTE PARQUET
# ============================================================

def escribir_lote(registros, hash_corto, ingestion_date):
    if not registros:
        return None

    carpeta = (
        BRONZE
        / FUENTE
        / f"ingestion_date={ingestion_date}"
    )
    carpeta.mkdir(parents=True, exist_ok=True)

    fila_inicio = registros[0]["source_row_number"]
    fila_fin = registros[-1]["source_row_number"]

    nombre = (
        f"part-{hash_corto}-"
        f"{fila_inicio:012d}-"
        f"{fila_fin:012d}.parquet"
    )

    ruta = carpeta / nombre
    temporal = ruta.with_suffix(".parquet.tmp")

    try:
        tabla = pa.Table.from_pylist(registros)
        pq.write_table(tabla, temporal, compression="snappy")
        temporal.replace(ruta)
    finally:
        if temporal.exists():
            temporal.unlink()

    print(
        f"Bronze -> {ruta.relative_to(RAIZ_PROYECTO)} "
        f"({len(registros):,} registros)"
    )

    return ruta


# ============================================================
# INGESTA CDC
# ============================================================

def cargar():
    if not ARCHIVO_FUENTE.is_file():
        raise FileNotFoundError(
            f"No existe el archivo CDC: {ARCHIVO_FUENTE}"
        )

    MANIFESTS.mkdir(parents=True, exist_ok=True)

    sha256 = calcular_sha256(ARCHIVO_FUENTE)
    hash_corto = sha256[:12]

    manifest_path = MANIFESTS / f"{FUENTE}-{hash_corto}.json"

    print("=" * 80)
    print("INGESTA CDC -> BRONZE | PROYECTO 2")
    print("=" * 80)
    print(f"Archivo:             {ARCHIVO_FUENTE.name}")
    print(f"SHA-256:             {sha256}")
    print(f"Registros esperados: {ESPERADOS:,}")

    # --------------------------------------------------------
    # IDEMPOTENCIA
    # --------------------------------------------------------

    if manifest_path.exists():
        with manifest_path.open("r", encoding="utf-8") as archivo:
            manifest = json.load(archivo)

        rutas = [
            RAIZ_PROYECTO / nombre
            for nombre in manifest.get("parquet_files", [])
        ]

        valido = (
            manifest.get("source_file_sha256") == sha256
            and manifest.get("records") == ESPERADOS
            and manifest.get("count_matches") is True
            and len(rutas) > 0
            and all(ruta.is_file() for ruta in rutas)
        )

        if not valido:
            raise RuntimeError(
                "El manifiesto CDC existe pero está incompleto "
                "o no corresponde a los datos actuales."
            )

        total_parquet = sum(
            pq.ParquetFile(ruta).metadata.num_rows
            for ruta in rutas
        )

        if total_parquet != ESPERADOS:
            raise RuntimeError(
                "El manifiesto CDC existe, pero el conteo "
                "de sus archivos Parquet es incorrecto."
            )

        print("RESULTADO: CARGA OMITIDA POR IDEMPOTENCIA")
        return

    # --------------------------------------------------------
    # METADATOS
    # --------------------------------------------------------

    ahora = datetime.now(timezone.utc)
    ingestion_timestamp = ahora.isoformat()
    ingestion_date = ahora.date().isoformat()

    registros = []
    archivos_creados = []
    total = 0

    try:
        with ARCHIVO_FUENTE.open(
            "r",
            encoding="utf-8-sig"
        ) as archivo:
            encabezado = archivo.readline().rstrip("\r\n")

            for numero_fila, linea in enumerate(archivo, start=1):
                raw_value = linea.rstrip("\r\n")

                if not raw_value:
                    continue

                registros.append({
                    "source_system": "transmetro_cdc",
                    "source_file": ARCHIVO_FUENTE.name,
                    "source_file_sha256": sha256,
                    "source_row_number": numero_fila,
                    "source_header": encabezado,
                    "raw_value": raw_value,
                    "ingestion_timestamp": ingestion_timestamp,
                    "ingestion_date": ingestion_date,
                })

                total += 1

                if len(registros) >= BATCH_SIZE:
                    ruta = escribir_lote(
                        registros, hash_corto, ingestion_date
                    )
                    archivos_creados.append(ruta)
                    registros.clear()

        if registros:
            ruta = escribir_lote(
                registros, hash_corto, ingestion_date
            )
            archivos_creados.append(ruta)

        # ----------------------------------------------------
        # VALIDAR REGISTROS
        # ----------------------------------------------------

        diferencia = total - ESPERADOS

        print("=" * 80)
        print("VALIDACIÓN DE INGESTA CDC")
        print(f"Registros esperados: {ESPERADOS:,}")
        print(f"Registros cargados:  {total:,}")
        print(f"Diferencia:          {diferencia:,}")

        if total != ESPERADOS:
            raise RuntimeError(
                f"Conteo CDC incorrecto: "
                f"esperados={ESPERADOS}, cargados={total}"
            )

        total_parquet = sum(
            pq.ParquetFile(ruta).metadata.num_rows
            for ruta in archivos_creados
        )

        if total_parquet != ESPERADOS:
            raise RuntimeError(
                f"Conteo Parquet incorrecto: {total_parquet}"
            )

        # ----------------------------------------------------
        # GUARDAR MANIFIESTO VALIDADO
        # ----------------------------------------------------

        manifest = {
            "source": FUENTE,
            "source_file": ARCHIVO_FUENTE.name,
            "source_file_sha256": sha256,
            "ingestion_timestamp": ingestion_timestamp,
            "ingestion_date": ingestion_date,
            "records": total,
            "expected_records": ESPERADOS,
            "count_matches": True,
            "parquet_files": [
                str(ruta.relative_to(RAIZ_PROYECTO))
                for ruta in archivos_creados
            ],
        }

        temporal = manifest_path.with_suffix(".json.tmp")

        try:
            with temporal.open("w", encoding="utf-8") as archivo:
                json.dump(
                    manifest, archivo,
                    indent=4, ensure_ascii=False
                )
            temporal.replace(manifest_path)
        finally:
            if temporal.exists():
                temporal.unlink()

        print(f"Archivos Parquet:    {len(archivos_creados)}")
        print("RESULTADO: CDC CARGADO A BRONZE CORRECTAMENTE")
        print("=" * 80)

    except Exception:
        for ruta in archivos_creados:
            if ruta.exists():
                ruta.unlink()
        raise


if __name__ == "__main__":
    cargar()
