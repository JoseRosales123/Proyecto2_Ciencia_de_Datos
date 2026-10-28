
from pathlib import Path
import csv
import sys


# ============================================================
# RUTAS DEL PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]
CARPETA_DATOS = RAIZ_PROYECTO / "datos_red"


# ============================================================
# FUENTES Y CONTEOS OFICIALES DEL PROYECTO 2
# ============================================================

FUENTES = [
    ("tm_estaciones.csv", "CSV", "Catalogo Transmetro", 104),
    ("tu_paradas.csv", "CSV", "Catalogo Transurbano", 328),
    ("mr_estaciones.csv", "CSV", "Catalogo MetroRiel", 22),
    ("am_estaciones.csv", "CSV", "Catalogo Aerometro", 14),
    ("transmetro_validaciones.csv", "CSV", "Operacion Transmetro", 713786),
    ("transurbano_transacciones.csv", "CSV", "Operacion Transurbano", 1635788),
    ("metroriel_viajes.jsonl", "JSONL", "Operacion MetroRiel", 590844),
    ("aerometro_boardings.csv", "CSV", "Operacion Aerometro", 387053),
    ("cdc_padron_usuarios.csv", "CSV", "CDC padron usuarios", 77636),
]


# ============================================================
# FUNCIONES DE CONTEO
# ============================================================

def contar_csv(ruta):
    with ruta.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:
        lector = csv.reader(archivo)

        # Omitir encabezado
        next(lector, None)

        return sum(1 for fila in lector if fila)


def contar_jsonl(ruta):
    with ruta.open(
        "r",
        encoding="utf-8"
    ) as archivo:
        return sum(
            1 for linea in archivo
            if linea.strip()
        )


# ============================================================
# INVENTARIO INICIAL
# ============================================================

def main():

    print("=" * 112)
    print("PROYECTO 2 - INVENTARIO INICIAL DE DATOS")
    print("=" * 112)

    print(
        f"{'ARCHIVO':<35}"
        f"{'FORMATO':<9}"
        f"{'ESPERADOS':>13}"
        f"{'ENCONTRADOS':>15}"
        f"{'DIFERENCIA':>13}"
        f"{'ESTADO':>12}"
    )

    print("-" * 112)

    total_esperados = 0
    total_encontrados = 0
    todo_correcto = True

    for nombre, formato, tipo, esperados in FUENTES:

        ruta = CARPETA_DATOS / nombre
        total_esperados += esperados

        if not ruta.is_file():
            todo_correcto = False

            print(
                f"{nombre:<35}"
                f"{formato:<9}"
                f"{esperados:>13,}"
                f"{'---':>15}"
                f"{'---':>13}"
                f"{'NO EXISTE':>12}"
            )
            continue

        if formato == "CSV":
            encontrados = contar_csv(ruta)
        else:
            encontrados = contar_jsonl(ruta)

        total_encontrados += encontrados
        diferencia = encontrados - esperados
        correcto = diferencia == 0

        if not correcto:
            todo_correcto = False

        print(
            f"{nombre:<35}"
            f"{formato:<9}"
            f"{esperados:>13,}"
            f"{encontrados:>15,}"
            f"{diferencia:>13,}"
            f"{'OK' if correcto else 'ERROR':>12}"
        )

    print("-" * 112)

    print(
        f"{'TOTAL':<44}"
        f"{total_esperados:>13,}"
        f"{total_encontrados:>15,}"
        f"{total_encontrados - total_esperados:>13,}"
    )

    print("=" * 112)

    print(f"Fuentes esperadas:   {len(FUENTES)}")
    print(f"Registros esperados: {total_esperados:,}")
    print(f"Registros hallados:  {total_encontrados:,}")
    print(
        f"Diferencia total:    "
        f"{total_encontrados - total_esperados:,}"
    )

    if todo_correcto:
        print(
            "RESULTADO: LAS 9 FUENTES ORIGINALES "
            "FUERON VALIDADAS CORRECTAMENTE"
        )
        return 0

    print(
        "RESULTADO: SE ENCONTRARON DIFERENCIAS "
        "EN LOS DATOS DE ORIGEN"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
