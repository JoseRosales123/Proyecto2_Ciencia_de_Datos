from pathlib import Path
from confluent_kafka import Producer
import argparse


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

ARCHIVO = RAIZ_PROYECTO / "datos_fuente" / "aerometro_boardings.csv"

TOPIC = "aerometro_boardings"
BOOTSTRAP_SERVERS = "localhost:9092"


def confirmar_entrega(err, msg):
    if err is not None:
        print(f"ERROR al enviar mensaje: {err}")


def publicar(limit=None):
    producer = Producer({
        "bootstrap.servers": BOOTSTRAP_SERVERS
    })

    enviados = 0

    with ARCHIVO.open("r", encoding="utf-8-sig") as archivo:

        encabezado = archivo.readline().strip()

        print(f"Archivo: {ARCHIVO.name}")
        print(f"Topic: {TOPIC}")
        print(f"Encabezado: {encabezado}")
        print("-" * 70)

        for linea in archivo:

            if limit is not None and enviados >= limit:
                break

            linea = linea.rstrip("\r\n")

            if not linea:
                continue

            # boarding_id será la key del mensaje.
            key = linea.split(",", 1)[0]

            producer.produce(
                TOPIC,
                key=key.encode("utf-8"),
                value=linea.encode("utf-8"),
                callback=confirmar_entrega
            )

            producer.poll(0)

            enviados += 1

    producer.flush()

    print(f"\nRegistros publicados correctamente: {enviados:,}")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Publica abordajes de Aerómetro hacia Kafka."
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cantidad máxima de registros a publicar."
    )

    args = parser.parse_args()

    publicar(args.limit)