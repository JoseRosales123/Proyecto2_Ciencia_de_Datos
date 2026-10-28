
from pathlib import Path
import csv
import json
import sys
from datetime import datetime, timezone

import pyarrow.parquet as pq


# ============================================================
# CONFIGURACIÓN DEL PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

DATOS_RED = RAIZ_PROYECTO / "datos_red"
BRONZE = RAIZ_PROYECTO / "bronze"

REPORTES = RAIZ_PROYECTO / "docs" / "reportes_fase1"


# ============================================================
# FUENTES Y CONTEOS ESPERADOS
# ============================================================

FUENTES = [
    {
        "archivo": "tm_estaciones.csv",
        "bronze": "tm_estaciones",
        "via": "Batch",
        "esperados": 104,
    },
    {
        "archivo": "tu_paradas.csv",
        "bronze": "tu_paradas",
        "via": "Batch",
        "esperados": 328,
    },
    {
        "archivo": "mr_estaciones.csv",
        "bronze": "mr_estaciones",
        "via": "Batch",
        "esperados": 22,
    },
    {
        "archivo": "am_estaciones.csv",
        "bronze": "am_estaciones",
        "via": "Batch",
        "esperados": 14,
    },
    {
        "archivo": "transmetro_validaciones.csv",
        "bronze": "transmetro",
        "via": "Streaming",
        "esperados": 713786,
    },
    {
        "archivo": "transurbano_transacciones.csv",
        "bronze": "transurbano_transacciones",
        "via": "Batch",
        "esperados": 1635788,
    },
    {
        "archivo": "metroriel_viajes.jsonl",
        "bronze": "metroriel_viajes",
        "via": "Batch",
        "esperados": 590844,
    },
    {
        "archivo": "aerometro_boardings.csv",
        "bronze": "aerometro",
        "via": "Streaming",
        "esperados": 387053,
    },
    {
        "archivo": "cdc_padron_usuarios.csv",
        "bronze": "cdc_padron_usuarios",
        "via": "CDC",
        "esperados": 77636,
    },
]


# ============================================================
# CONTAR REGISTROS DE ORIGEN
# ============================================================

def contar_origen(ruta):
    if not ruta.is_file():
        raise FileNotFoundError(
            f"No existe el archivo de origen: {ruta}"
        )

    with ruta.open("r", encoding="utf-8-sig") as archivo:
        total_lineas = sum(1 for _ in archivo)

    if ruta.suffix.lower() == ".jsonl":
        return total_lineas

    return max(total_lineas - 1, 0)


# ============================================================
# CONTAR REGISTROS PARQUET
# ============================================================

def contar_parquet(carpeta):
    archivos = sorted(carpeta.rglob("*.parquet"))

    total = 0

    for archivo in archivos:
        metadata = pq.ParquetFile(archivo).metadata
        total += metadata.num_rows

    return len(archivos), total


# ============================================================
# CONSTRUIR INVENTARIO
# ============================================================

def construir_inventario():
    resultados = []
    todo_correcto = True

    for fuente in FUENTES:
        ruta_origen = DATOS_RED / fuente["archivo"]
        carpeta_bronze = BRONZE / fuente["bronze"]

        origen = contar_origen(ruta_origen)

        cantidad_parquet, cargados = contar_parquet(
            carpeta_bronze
        )

        esperados = fuente["esperados"]
        diferencia = cargados - esperados

        correcto = (
            origen == esperados
            and cargados == esperados
        )

        if not correcto:
            todo_correcto = False

        resultados.append({
            "archivo": fuente["archivo"],
            "via": fuente["via"],
            "origen": origen,
            "esperados": esperados,
            "cargados": cargados,
            "diferencia": diferencia,
            "archivos_parquet": cantidad_parquet,
            "valido": correcto,
        })

    return resultados, todo_correcto


# ============================================================
# MOSTRAR TABLA DE RECONCILIACIÓN
# ============================================================

def mostrar_inventario(resultados):
    ancho = 115

    print("=" * ancho)
    print("PROYECTO 2 - INVENTARIO Y RECONCILIACIÓN BRONZE")
    print("=" * ancho)

    print(
        f"{'ARCHIVO':<35}"
        f"{'VIA':<12}"
        f"{'ESPERADOS':>13}"
        f"{'CARGADOS':>13}"
        f"{'DIFERENCIA':>13}"
        f"{'PARQUET':>10}"
        f"{'VALIDO':>10}"
    )

    print("-" * ancho)

    for item in resultados:
        print(
            f"{item['archivo']:<35}"
            f"{item['via']:<12}"
            f"{item['esperados']:>13,}"
            f"{item['cargados']:>13,}"
            f"{item['diferencia']:>13,}"
            f"{item['archivos_parquet']:>10}"
            f"{'SI' if item['valido'] else 'NO':>10}"
        )

    print("-" * ancho)

    total_origen = sum(
        item["origen"] for item in resultados
    )
    total_esperados = sum(
        item["esperados"] for item in resultados
    )
    total_cargados = sum(
        item["cargados"] for item in resultados
    )

    print(
        f"{'TOTAL':<47}"
        f"{total_esperados:>13,}"
        f"{total_cargados:>13,}"
        f"{total_cargados - total_esperados:>13,}"
    )

    print("=" * ancho)

    print(f"Registros origen:    {total_origen:,}")
    print(f"Registros esperados: {total_esperados:,}")
    print(f"Registros Bronze:   {total_cargados:,}")
    print(
        f"Diferencia total:    "
        f"{total_cargados - total_esperados:,}"
    )

    return total_origen, total_esperados, total_cargados


# ============================================================
# GUARDAR EVIDENCIA JSON Y CSV
# ============================================================

def guardar_reportes(resultados, correcto):
    REPORTES.mkdir(parents=True, exist_ok=True)

    resumen = {
        "fecha_generacion_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "proyecto": "Proyecto 2 - Red Metropolitana",
        "total_esperados": sum(
            item["esperados"] for item in resultados
        ),
        "total_cargados": sum(
            item["cargados"] for item in resultados
        ),
        "diferencia_total": sum(
            item["diferencia"] for item in resultados
        ),
        "todas_las_fuentes_validas": correcto,
        "fuentes": resultados,
    }

    ruta_json = REPORTES / "reconciliacion_bronze.json"
    ruta_csv = REPORTES / "reconciliacion_bronze.csv"

    with ruta_json.open("w", encoding="utf-8") as archivo:
        json.dump(
            resumen,
            archivo,
            indent=4,
            ensure_ascii=False
        )

    columnas = [
        "archivo",
        "via",
        "origen",
        "esperados",
        "cargados",
        "diferencia",
        "archivos_parquet",
        "valido",
    ]

    with ruta_csv.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=columnas
        )
        escritor.writeheader()
        escritor.writerows(resultados)

    print(f"Reporte JSON: {ruta_json}")
    print(f"Reporte CSV:  {ruta_csv}")


# ============================================================
# EJECUCIÓN PRINCIPAL
# ============================================================

def main():
    resultados, correcto = construir_inventario()

    _, total_esperados, total_cargados = mostrar_inventario(
        resultados
    )

    guardar_reportes(resultados, correcto)

    if correcto and total_esperados == total_cargados:
        print(
            "RESULTADO: BRONZE COMPLETA Y RECONCILIADA "
            "CORRECTAMENTE"
        )
        return 0

    print(
        "RESULTADO: SE ENCONTRARON DIFERENCIAS "
        "EN LA CAPA BRONZE"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
