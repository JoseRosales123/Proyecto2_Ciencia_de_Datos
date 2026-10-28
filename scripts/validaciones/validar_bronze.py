
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import sys

import pyarrow.parquet as pq


# ============================================================
# CONFIGURACION DEL PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

BRONZE = RAIZ_PROYECTO / "bronze"
DATOS_FUENTE = RAIZ_PROYECTO / "datos_red"


FUENTES = {
    "transmetro": {
        "archivo": "transmetro_validaciones.csv",
        "esperados": 713786,
    },
    "aerometro": {
        "archivo": "aerometro_boardings.csv",
        "esperados": 387053,
    },
}


# ============================================================
# CALCULAR HUELLA DEL REGISTRO ORIGINAL
# ============================================================

def huella_registro(raw_value):
    return hashlib.sha256(
        raw_value.encode("utf-8")
    ).digest()


# ============================================================
# LEER Y CONTAR REGISTROS DEL CSV ORIGINAL
# ============================================================

def contar_registros_origen(ruta):
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe el archivo original: {ruta}"
        )

    frecuencias = Counter()
    total = 0

    with ruta.open(
        "r",
        encoding="utf-8-sig"
    ) as archivo:

        next(archivo, None)

        for linea in archivo:
            raw_value = linea.rstrip("\r\n")

            if not raw_value:
                continue

            frecuencias[huella_registro(raw_value)] += 1
            total += 1

    return total, frecuencias


# ============================================================
# LEER Y CONTAR REGISTROS DE BRONZE
# ============================================================

def contar_registros_bronze(archivos_parquet):
    frecuencias = Counter()
    total = 0

    for ruta in archivos_parquet:
        archivo = pq.ParquetFile(ruta)

        if "raw_value" not in archivo.schema_arrow.names:
            raise RuntimeError(
                f"Falta la columna raw_value en: {ruta}"
            )

        cantidad_archivo = 0

        for lote in archivo.iter_batches(
            batch_size=50000,
            columns=["raw_value"]
        ):
            valores = lote.column(0).to_pylist()

            for raw_value in valores:
                if raw_value is None:
                    raise RuntimeError(
                        f"Se encontró raw_value nulo en: {ruta}"
                    )

                frecuencias[
                    huella_registro(raw_value)
                ] += 1

                total += 1
                cantidad_archivo += 1

        print(
            f"{ruta.name:<55} "
            f"{cantidad_archivo:>10,} filas"
        )

    return total, frecuencias


# ============================================================
# VALIDAR UNA FUENTE STREAMING
# ============================================================

def validar(fuente):
    config = FUENTES[fuente]

    carpeta_bronze = BRONZE / fuente
    archivo_fuente = DATOS_FUENTE / config["archivo"]
    esperados = config["esperados"]

    archivos_parquet = sorted(
        carpeta_bronze.rglob("*.parquet")
    )

    if not archivos_parquet:
        raise RuntimeError(
            f"No se encontraron archivos Parquet "
            f"para {fuente}."
        )

    print("=" * 85)
    print("PROYECTO 2 - VALIDACION DE BRONZE STREAMING")
    print("=" * 85)
    print(f"Fuente:              {fuente}")
    print(f"Archivo original:    {config['archivo']}")
    print(f"Registros esperados: {esperados:,}")
    print(f"Archivos Parquet:    {len(archivos_parquet)}")
    print("-" * 85)

    # --------------------------------------------------------
    # VALIDAR ESQUEMA DE BRONZE
    # --------------------------------------------------------

    columnas = (
        pq.ParquetFile(archivos_parquet[0])
        .schema_arrow.names
    )

    print("\nCOLUMNAS BRONZE:")

    for columna in columnas:
        print(f"  - {columna}")

    # --------------------------------------------------------
    # CONTAR REGISTROS Y COMPARAR CONTENIDO ORIGINAL
    # --------------------------------------------------------

    print("\nLEYENDO REGISTROS DEL ORIGEN...")

    total_origen, frecuencias_origen = (
        contar_registros_origen(archivo_fuente)
    )

    print("LEYENDO REGISTROS PARQUET...")

    total_bronze, frecuencias_bronze = (
        contar_registros_bronze(archivos_parquet)
    )

    # Counter conserva también las repeticiones reales.
    # Dos filas iguales en el CSV deben aparecer dos
    # veces en Bronze.

    faltantes = sum(
        (frecuencias_origen - frecuencias_bronze).values()
    )

    sobrantes = sum(
        (frecuencias_bronze - frecuencias_origen).values()
    )

    conteo_correcto = (
        total_origen == esperados
        and total_bronze == esperados
    )

    contenido_correcto = (
        faltantes == 0
        and sobrantes == 0
    )

    # --------------------------------------------------------
    # MOSTRAR RESULTADOS
    # --------------------------------------------------------

    print("\n" + "=" * 85)
    print("RESULTADOS DE VALIDACION")
    print("=" * 85)

    print(f"Registros esperados:       {esperados:,}")
    print(f"Registros de origen:       {total_origen:,}")
    print(f"Registros en Bronze:       {total_bronze:,}")
    print(f"Diferencia Bronze-origen:  {total_bronze - total_origen:,}")
    print(f"Registros faltantes:       {faltantes:,}")
    print(f"Registros sobrantes:       {sobrantes:,}")

    print(
        f"Conteo correcto:           "
        f"{'SI' if conteo_correcto else 'NO'}"
    )

    print(
        f"Contenido original intacto: "
        f"{'SI' if contenido_correcto else 'NO'}"
    )

    print("=" * 85)

    if conteo_correcto and contenido_correcto:
        print(
            "RESULTADO: BRONZE VALIDADO CORRECTAMENTE"
        )
        return 0

    print(
        "RESULTADO: SE ENCONTRARON DIFERENCIAS "
        "EN LOS REGISTROS DE BRONZE"
    )
    return 1


# ============================================================
# EJECUCION POR TERMINAL
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Valida conteos y preservacion de registros "
            "originales de Streaming en Bronze."
        )
    )

    parser.add_argument(
        "--source",
        choices=list(FUENTES.keys()),
        required=True
    )

    args = parser.parse_args()

    sys.exit(validar(args.source))
