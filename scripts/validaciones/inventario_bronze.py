from pathlib import Path
import pyarrow.parquet as pq


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
BRONZE = RAIZ_PROYECTO / "bronze"


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
        "esperados": 363221,
    },
    {
        "archivo": "transurbano_transacciones.csv",
        "bronze": "transurbano_transacciones",
        "via": "Batch",
        "esperados": 832791,
    },
    {
        "archivo": "metroriel_viajes.jsonl",
        "bronze": "metroriel_viajes",
        "via": "Batch",
        "esperados": 299100,
    },
    {
        "archivo": "aerometro_boardings.csv",
        "bronze": "aerometro",
        "via": "Streaming",
        "esperados": 203554,
    },
    {
        "archivo": "cdc_padron_usuarios.csv",
        "bronze": "cdc_padron_usuarios",
        "via": "CDC",
        "esperados": 31050,
    },
]


def contar_parquet(carpeta):
    archivos = list(carpeta.rglob("*.parquet"))

    total = 0

    for archivo in archivos:
        metadata = pq.ParquetFile(archivo).metadata
        total += metadata.num_rows

    return len(archivos), total


print("=" * 115)
print("INVENTARIO GLOBAL DE CAPA BRONZE - RED METROPOLITANA")
print("=" * 115)

print(
    f"{'ARCHIVO FUENTE':<35}"
    f"{'VIA':<12}"
    f"{'ESPERADOS':>15}"
    f"{'BRONZE':>15}"
    f"{'PARQUET':>10}"
    f"{'VALIDO':>10}"
)

print("-" * 115)

total_esperados = 0
total_bronze = 0
todo_correcto = True

for fuente in FUENTES:

    carpeta = BRONZE / fuente["bronze"]

    cantidad_parquet, registros = contar_parquet(carpeta)

    coincide = registros == fuente["esperados"]

    total_esperados += fuente["esperados"]
    total_bronze += registros

    if not coincide:
        todo_correcto = False

    print(
        f"{fuente['archivo']:<35}"
        f"{fuente['via']:<12}"
        f"{fuente['esperados']:>15,}"
        f"{registros:>15,}"
        f"{cantidad_parquet:>10}"
        f"{'SI' if coincide else 'NO':>10}"
    )

print("-" * 115)

print(
    f"{'TOTAL':<47}"
    f"{total_esperados:>15,}"
    f"{total_bronze:>15,}"
)

print("=" * 115)

print(
    f"Conteo global coincide: "
    f"{'SI' if total_esperados == total_bronze else 'NO'}"
)

print(
    f"Todas las fuentes validadas: "
    f"{'SI' if todo_correcto else 'NO'}"
)

if (
    total_esperados == total_bronze
    and todo_correcto
):
    print(
        "RESULTADO: CAPA BRONZE COMPLETA Y RECONCILIADA CORRECTAMENTE"
    )
else:
    print(
        "RESULTADO: SE ENCONTRARON DIFERENCIAS"
    )

print("=" * 115)