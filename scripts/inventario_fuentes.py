from pathlib import Path
import csv

# ---------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------
RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
CARPETA_DATOS = RAIZ_PROYECTO / "datos_fuente"

# ---------------------------------------------------------
# Fuentes entregadas para el proyecto
# ---------------------------------------------------------
FUENTES = [
    ("tm_estaciones.csv", "CSV", "Catálogo Transmetro"),
    ("tu_paradas.csv", "CSV", "Catálogo Transurbano"),
    ("mr_estaciones.csv", "CSV", "Catálogo MetroRiel"),
    ("am_estaciones.csv", "CSV", "Catálogo Aerómetro"),
    ("transmetro_validaciones.csv", "CSV", "Operación Transmetro"),
    ("transurbano_transacciones.csv", "CSV", "Operación Transurbano"),
    ("metroriel_viajes.jsonl", "JSONL", "Operación MetroRiel"),
    ("aerometro_boardings.csv", "CSV", "Operación Aerómetro"),
    ("cdc_padron_usuarios.csv", "CSV", "CDC padrón usuarios"),
]


def contar_csv(ruta):
    with ruta.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.reader(archivo)

        # Ignorar encabezado
        next(lector, None)

        return sum(1 for _ in lector)


def contar_jsonl(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return sum(1 for linea in archivo if linea.strip())


print("=" * 100)
print("INVENTARIO INICIAL DE FUENTES - RED METROPOLITANA")
print("=" * 100)

print(
    f"{'ARCHIVO':<35}"
    f"{'FORMATO':<10}"
    f"{'TIPO':<25}"
    f"{'REGISTROS':>12}"
    f"{'TAMAÑO MB':>12}"
)

print("-" * 100)

total_registros = 0
total_mb = 0

for nombre, formato, tipo in FUENTES:
    ruta = CARPETA_DATOS / nombre

    if not ruta.exists():
        print(f"{nombre:<35}{'NO ENCONTRADO'}")
        continue

    if formato == "CSV":
        registros = contar_csv(ruta)
    else:
        registros = contar_jsonl(ruta)

    tamano_mb = ruta.stat().st_size / (1024 * 1024)

    total_registros += registros
    total_mb += tamano_mb

    print(
        f"{nombre:<35}"
        f"{formato:<10}"
        f"{tipo:<25}"
        f"{registros:>12,}"
        f"{tamano_mb:>12.2f}"
    )

print("-" * 100)

print(
    f"{'TOTAL':<70}"
    f"{total_registros:>12,}"
    f"{total_mb:>12.2f}"
)

print("=" * 100)
print("Inventario completado correctamente.")