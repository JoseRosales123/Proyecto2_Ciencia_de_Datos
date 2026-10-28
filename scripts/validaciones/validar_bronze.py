from pathlib import Path
import argparse
import pyarrow.parquet as pq


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

BRONZE = RAIZ_PROYECTO / "bronze"
DATOS_FUENTE = RAIZ_PROYECTO / "datos_fuente"


FUENTES = {
    "transmetro": {
        "archivo": "transmetro_validaciones.csv",
        "esperados": 363221,
    },
    "aerometro": {
        "archivo": "aerometro_boardings.csv",
        "esperados": 203554,
    },
}


def validar(fuente):

    config = FUENTES[fuente]

    carpeta_bronze = BRONZE / fuente
    archivo_fuente = DATOS_FUENTE / config["archivo"]
    esperados = config["esperados"]

    archivos_parquet = sorted(
        carpeta_bronze.rglob("*.parquet")
    )

    if not archivos_parquet:
        print(f"No se encontraron archivos Parquet para {fuente}.")
        return

    print("=" * 80)
    print("VALIDACIÓN DE CAPA BRONZE")
    print("=" * 80)
    print(f"Fuente: {fuente}")
    print(f"Archivo original: {config['archivo']}")
    print(f"Archivos Parquet encontrados: {len(archivos_parquet)}")
    print("-" * 80)

    total_registros = 0

    for archivo in archivos_parquet:

        metadata = pq.ParquetFile(archivo).metadata
        filas = metadata.num_rows

        total_registros += filas

        print(
            f"{archivo.name:<55} "
            f"{filas:>10,} filas"
        )

    print("-" * 80)

    print(f"Registros esperados:       {esperados:,}")
    print(f"Registros encontrados:     {total_registros:,}")

    conteo_correcto = total_registros == esperados

    print(
        f"Conteo coincide:           "
        f"{'SI' if conteo_correcto else 'NO'}"
    )

    # -----------------------------------------------------
    # Revisar esquema
    # -----------------------------------------------------

    primer_parquet = archivos_parquet[0]

    tabla = pq.read_table(primer_parquet)

    print("\nCOLUMNAS BRONZE:")

    for columna in tabla.column_names:
        print(f"  - {columna}")

    # -----------------------------------------------------
    # Verificar preservación del registro original
    # -----------------------------------------------------

    with archivo_fuente.open(
        "r",
        encoding="utf-8-sig"
    ) as archivo:

        # Saltar encabezado
        next(archivo)

        primera_linea_original = (
            next(archivo)
            .rstrip("\r\n")
        )

    primer_raw = (
        tabla["raw_value"][0]
        .as_py()
    )

    coincide_raw = (
        primera_linea_original == primer_raw
    )

    print("\nVALIDACIÓN DE DATO CRUDO")
    print("-" * 80)

    print(
        f"Primer registro original coincide "
        f"con raw_value: "
        f"{'SI' if coincide_raw else 'NO'}"
    )

    print("\nPrimer registro original:")
    print(primera_linea_original)

    print("\nPrimer raw_value en Bronze:")
    print(primer_raw)

    print("\n" + "=" * 80)

    if conteo_correcto and coincide_raw:
        print("RESULTADO: BRONZE VALIDADO CORRECTAMENTE")
    else:
        print("RESULTADO: SE ENCONTRARON DIFERENCIAS")

    print("=" * 80)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        choices=["transmetro", "aerometro"],
        required=True
    )

    args = parser.parse_args()

    validar(args.source)