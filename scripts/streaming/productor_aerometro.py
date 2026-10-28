
from pathlib import Path
from confluent_kafka import Producer
import argparse
import os


# ============================================================
# CONFIGURACIÓN DEL PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

ARCHIVO = (
    RAIZ_PROYECTO
    / "datos_red"
    / "aerometro_boardings.csv"
)

TOPIC = "aerometro_boardings"

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9094"
)

ESPERADOS = 387053


# ============================================================
# PUBLICACIÓN EN KAFKA
# ============================================================

def publicar(limit=None):
    if not ARCHIVO.is_file():
        raise FileNotFoundError(
            f"No existe el archivo: {ARCHIVO}"
        )

    if limit is not None and limit <= 0:
        raise ValueError(
            "--limit debe ser mayor que cero."
        )

    productor = Producer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
    })

    intentados = 0
    confirmados = 0
    errores = []

    def confirmar_entrega(err, msg):
        nonlocal confirmados

        if err is not None:
            errores.append(str(err))
        else:
            confirmados += 1

    print("=" * 75)
    print("PROYECTO 2 - PRODUCTOR AERÓMETRO")
    print("=" * 75)
    print(f"Archivo:  {ARCHIVO.name}")
    print(f"Topic:    {TOPIC}")
    print(f"Servidor: {BOOTSTRAP_SERVERS}")
    print("=" * 75)

    with ARCHIVO.open(
        "r",
        encoding="utf-8-sig"
    ) as archivo:

        encabezado = archivo.readline().rstrip("\r\n")

        print(f"Encabezado: {encabezado}")

        for linea in archivo:

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
    print(f"Mensajes intentados:  {intentados:,}")
    print(f"Mensajes confirmados: {confirmados:,}")
    print(f"Errores de entrega:   {len(errores):,}")
    print(f"Mensajes pendientes:  {pendientes:,}")
    print("=" * 75)

    if errores or pendientes or confirmados != intentados:
        raise RuntimeError(
            "La publicación de Aerómetro no se completó "
            "correctamente."
        )

    if limit is None and intentados != ESPERADOS:
        raise RuntimeError(
            f"Conteo incorrecto de Aerómetro: "
            f"esperados={ESPERADOS}, "
            f"publicados={intentados}"
        )

    print(
        "RESULTADO: AERÓMETRO PUBLICADO "
        "CORRECTAMENTE EN KAFKA"
    )


# ============================================================
# EJECUCIÓN POR TERMINAL
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Publica abordajes de Aerómetro "
            "en Kafka para el Proyecto 2."
        )
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad máxima de mensajes a publicar."
    )

    args = parser.parse_args()
    publicar(args.limit)
