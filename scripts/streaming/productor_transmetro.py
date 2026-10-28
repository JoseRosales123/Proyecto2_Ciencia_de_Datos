
from pathlib import Path
from confluent_kafka import Producer
import argparse
import os


# ============================================================
# CONFIGURACION - PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

ARCHIVO = (
    RAIZ_PROYECTO
    / "datos_red"
    / "transmetro_validaciones.csv"
)

TOPIC = "transmetro_validaciones"

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9094"
)

ESPERADOS = 713786


# ============================================================
# PUBLICAR MENSAJES EN KAFKA
# ============================================================

def publicar(limit=None, skip=0):

    if not ARCHIVO.is_file():
        raise FileNotFoundError(
            f"No existe el archivo: {ARCHIVO}"
        )

    if limit is not None and limit <= 0:
        raise ValueError(
            "--limit debe ser mayor que cero."
        )

    if skip < 0 or skip > ESPERADOS:
        raise ValueError(
            f"--skip debe estar entre 0 y {ESPERADOS}."
        )

    productor = Producer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
    })

    intentados = 0
    confirmados = 0
    errores = []
    omitidos = 0

    def confirmar_entrega(err, msg):
        nonlocal confirmados

        if err is not None:
            errores.append(str(err))
        else:
            confirmados += 1

    print("=" * 75)
    print("PROYECTO 2 - PRODUCTOR TRANSMETRO")
    print("=" * 75)
    print(f"Archivo:   {ARCHIVO.name}")
    print(f"Topic:     {TOPIC}")
    print(f"Servidor:  {BOOTSTRAP_SERVERS}")
    print(f"Omitidos:  {skip:,}")
    print("=" * 75)

    with ARCHIVO.open(
        "r",
        encoding="utf-8-sig"
    ) as archivo:

        encabezado = archivo.readline().rstrip("\r\n")

        print(f"Encabezado: {encabezado}")

        for numero_fila, linea in enumerate(archivo):

            if numero_fila < skip:
                omitidos += 1
                continue

            if limit is not None and intentados >= limit:
                break

            raw_value = linea.rstrip("\r\n")

            if not raw_value:
                continue

            key = raw_value.split(",", 1)[0]

            while True:
                try:
                    productor.produce(
                        TOPIC,
                        key=key.encode("utf-8"),
                        value=raw_value.encode("utf-8"),
                        callback=confirmar_entrega,
                    )
                    break

                except BufferError:
                    productor.poll(1.0)

            productor.poll(0)
            intentados += 1

    pendientes = productor.flush(60)

    print("\n" + "=" * 75)
    print(f"Registros omitidos:   {omitidos:,}")
    print(f"Mensajes intentados:  {intentados:,}")
    print(f"Mensajes confirmados: {confirmados:,}")
    print(f"Errores de entrega:   {len(errores):,}")
    print(f"Mensajes pendientes:  {pendientes:,}")
    print("=" * 75)

    if errores or pendientes or confirmados != intentados:
        raise RuntimeError(
            "La publicación de Transmetro no se completó "
            "correctamente."
        )

    if limit is None:
        esperados_publicar = ESPERADOS - skip

        if intentados != esperados_publicar:
            raise RuntimeError(
                f"Conteo incorrecto de Transmetro: "
                f"esperados={esperados_publicar}, "
                f"publicados={intentados}"
            )

    print(
        "RESULTADO: TRANSMETRO PUBLICADO "
        "CORRECTAMENTE EN KAFKA"
    )


# ============================================================
# EJECUCION POR TERMINAL
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=(
            "Publica validaciones de Transmetro "
            "en Kafka para el Proyecto 2."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad maxima de mensajes a publicar."
    )

    parser.add_argument(
        "--skip",
        type=int,
        default=0,
        help="Cantidad de registros iniciales que se omiten."
    )

    args = parser.parse_args()

    publicar(
        limit=args.limit,
        skip=args.skip
    )
