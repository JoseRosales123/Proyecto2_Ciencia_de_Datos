from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
from confluent_kafka import Consumer, KafkaError
import pyarrow as pa
import pyarrow.parquet as pq
import argparse
import time


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
BRONZE = RAIZ_PROYECTO / "bronze"

FUENTES = {
    "transmetro": {
        "topic": "transmetro_validaciones",
        "archivo": "transmetro_validaciones.csv",
    },
    "aerometro": {
        "topic": "aerometro_boardings",
        "archivo": "aerometro_boardings.csv",
    },
}


def escribir_batch(registros, fuente):
    """
    Escribe un lote en Parquet.
    El valor original del mensaje se conserva en raw_value.
    """

    if not registros:
        return 0

    # Separamos por fecha de ingesta
    grupos = defaultdict(list)

    for registro in registros:
        grupos[registro["ingestion_date"]].append(registro)

    escritos = 0

    for fecha, filas in grupos.items():

        carpeta = (
            BRONZE
            / fuente
            / f"ingestion_date={fecha}"
        )

        carpeta.mkdir(parents=True, exist_ok=True)

        particion = filas[0]["kafka_partition"]

        offset_inicio = min(
            fila["kafka_offset"] for fila in filas
        )

        offset_fin = max(
            fila["kafka_offset"] for fila in filas
        )

        nombre = (
            f"part-p{particion}-"
            f"{offset_inicio:012d}-"
            f"{offset_fin:012d}.parquet"
        )

        ruta = carpeta / nombre

        tabla = pa.Table.from_pylist(filas)

        pq.write_table(
            tabla,
            ruta,
            compression="snappy"
        )

        escritos += len(filas)

        print(
            f"Bronze -> {ruta.relative_to(RAIZ_PROYECTO)} "
            f"({len(filas):,} registros)"
        )

    return escritos


def consumir(fuente, expected=None, batch_size=50000):

    config_fuente = FUENTES[fuente]

    topic = config_fuente["topic"]
    archivo = config_fuente["archivo"]

    consumer = Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": f"bronze_{fuente}_v1",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    consumer.subscribe([topic])

    buffer = []

    procesados = 0
    escritos = 0

    ultima_actividad = time.monotonic()

    print("=" * 70)
    print("CONSUMIDOR KAFKA -> BRONZE")
    print("=" * 70)
    print(f"Fuente: {fuente}")
    print(f"Topic: {topic}")
    print(f"Archivo origen: {archivo}")
    print(f"Batch size: {batch_size:,}")
    print("=" * 70)

    try:

        while True:

            mensaje = consumer.poll(1.0)

            if mensaje is None:

                # Si ya se llegó al total esperado terminamos
                if expected is not None and procesados >= expected:
                    break

                # Protección para no quedar esperando indefinidamente
                if time.monotonic() - ultima_actividad > 15:
                    print("\nNo llegaron más mensajes durante 15 segundos.")
                    break

                continue

            if mensaje.error():

                if mensaje.error().code() == KafkaError._PARTITION_EOF:
                    continue

                raise RuntimeError(mensaje.error())

            ahora = datetime.now(timezone.utc)

            registro = {
                "source_system": fuente,
                "source_file": archivo,

                # Dato crudo tal como llegó desde Kafka
                "raw_value": mensaje.value().decode("utf-8"),

                # Metadatos de Kafka
                "kafka_topic": mensaje.topic(),
                "kafka_partition": mensaje.partition(),
                "kafka_offset": mensaje.offset(),

                # Metadatos de ingesta
                "ingestion_timestamp": ahora.isoformat(),
                "ingestion_date": ahora.date().isoformat(),
            }

            buffer.append(registro)

            procesados += 1
            ultima_actividad = time.monotonic()

            if len(buffer) >= batch_size:

                escritos += escribir_batch(
                    buffer,
                    fuente
                )

                buffer.clear()

                consumer.commit(
                    asynchronous=False
                )

            if expected is not None and procesados >= expected:
                break

        # Último lote
        if buffer:

            escritos += escribir_batch(
                buffer,
                fuente
            )

            buffer.clear()

            consumer.commit(
                asynchronous=False
            )

    finally:

        consumer.close()

    print("\n" + "=" * 70)
    print(f"Mensajes consumidos: {procesados:,}")
    print(f"Registros escritos en Bronze: {escritos:,}")
    print("=" * 70)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        choices=["transmetro", "aerometro"],
        required=True
    )

    parser.add_argument(
        "--expected",
        type=int,
        default=None
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=50000
    )

    args = parser.parse_args()

    consumir(
        fuente=args.source,
        expected=args.expected,
        batch_size=args.batch_size
    )