from pathlib import Path
import json
import sys


RAIZ = Path(__file__).resolve().parents[2]
CARPETA = RAIZ / "docs" / "metricas_prefect"


def cargar_json(ruta):
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def aplanar(diccionario, prefijo=""):
    resultado = {}

    for clave, valor in diccionario.items():

        nombre = (
            f"{prefijo}.{clave}"
            if prefijo
            else clave
        )

        if isinstance(valor, dict):
            resultado.update(
                aplanar(valor, nombre)
            )
        else:
            resultado[nombre] = valor

    return resultado


def main():

    archivos = sorted(
        CARPETA.glob("corrida_*.json"),
        key=lambda x: x.stat().st_mtime,
    )

    if len(archivos) < 2:
        print("Se necesitan al menos dos corridas.")
        sys.exit(1)

    primera = archivos[-2]
    segunda = archivos[-1]

    datos_1 = cargar_json(primera)
    datos_2 = cargar_json(segunda)

    metricas_1 = aplanar(
        datos_1["metricas"]
    )

    metricas_2 = aplanar(
        datos_2["metricas"]
    )

    print("=" * 100)
    print("VALIDACION DE IDEMPOTENCIA - FASE 1")
    print("=" * 100)

    print(f"Primera corrida: {primera.name}")
    print(f"Segunda corrida: {segunda.name}")

    print("-" * 100)

    print(
        f"{'METRICA':<55}"
        f"{'CORRIDA 1':>14}"
        f"{'CORRIDA 2':>14}"
        f"{'COINCIDE':>12}"
    )

    print("-" * 100)

    todas_coinciden = True

    claves = sorted(
        set(metricas_1)
        | set(metricas_2)
    )

    for clave in claves:

        valor_1 = metricas_1.get(clave)
        valor_2 = metricas_2.get(clave)

        coincide = valor_1 == valor_2

        if not coincide:
            todas_coinciden = False

        print(
            f"{clave:<55}"
            f"{str(valor_1):>14}"
            f"{str(valor_2):>14}"
            f"{'SI' if coincide else 'NO':>12}"
        )

    print("-" * 100)

    duracion_1 = datos_1[
        "duracion_total_segundos"
    ]

    duracion_2 = datos_2[
        "duracion_total_segundos"
    ]

    print(
        f"Duracion corrida 1: "
        f"{duracion_1:.2f} segundos"
    )

    print(
        f"Duracion corrida 2: "
        f"{duracion_2:.2f} segundos"
    )

    print()

    if todas_coinciden:

        print(
            "RESULTADO: PIPELINE IDEMPOTENTE"
        )

        print(
            "La segunda ejecucion produjo "
            "exactamente los mismos conteos."
        )

        sys.exit(0)

    else:

        print(
            "RESULTADO: SE DETECTARON DIFERENCIAS"
        )

        sys.exit(1)


if __name__ == "__main__":
    main()
    