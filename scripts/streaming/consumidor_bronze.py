
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict
import argparse
import os
import time

import pyarrow as pa
import pyarrow.parquet as pq

from confluent_kafka import (
    Consumer,
    KafkaError,
    TopicPartition,
)


# ============================================================
# CONFIGURACION - PROYECTO 2
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
BRONZE = RAIZ_PROYECTO / "bronze"

BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9094"
)

FUENTES = {
    "transmetro": {
        "topic": "transmetro_validaciones",
        "archivo": "transmetro_validaciones.csv",
        "esperados": 713786,
    },
    "aerometro": {
        "topic": "aerometro_boardings",
        "archivo": "aerometro_boardings.csv",
        "esperados": 387053,
    },
}

TIEMPO_MAXIMO_INACTIVIDAD = 90


# ============================================================
# LEER OFFSETS YA GUARDADOS EN BRONZE
# ============================================================

def leer_estado_bronze(fuente):
    carpeta = BRONZE / fuente

    offsets_existentes = set()
    total = 0

    if not carpeta.exists():
        return offsets_existentes, total

    archivos = sorted(carpeta.rglob("*.parquet"))

    for ruta in archivos:
        tabla = pq.read_table(
            ruta,
            columns=[
                "kafka_partition",
                "kafka_offset",
            ]
        )

        particiones = tabla["kafka_partition"].to_pylist()
        offsets = tabla["kafka_offset"].to_pylist()

        for particion, offset in zip(particiones, offsets):
            clave = (int(particion), int(offset))

            if clave in offsets_existentes:
                raise RuntimeError(
                    "Offset duplicado en Bronze: "
                    f"particion={particion}, "
                    f"offset={offset}. Archivo: {ruta}"
                )

            offsets_existentes.add(clave)
            total += 1

    return offsets_existentes, total


# ============================================================
# ESCRITURA SEGURA DE PARQUET
# ============================================================

def escribir_batch(registros, fuente):
    if not registros:
        return 0

    grupos = defaultdict(list)

    for registro in registros:
        clave = (
            registro["ingestion_date"],
            registro["kafka_partition"],
        )
        grupos[clave].append(registro)

    escritos = 0

    for (fecha, particion), filas in grupos.items():
        carpeta = (
            BRONZE
            / fuente
            / f"ingestion_date={fecha}"
        )

        carpeta.mkdir(
            parents=True,
            exist_ok=True
        )

        offset_inicio = min(
            fila["kafka_offset"]
            for fila in filas
        )

        offset_fin = max(
            fila["kafka_offset"]
            for fila in filas
        )

        nombre = (
            f"part-p{particion}-"
            f"{offset_inicio:012d}-"
            f"{offset_fin:012d}.parquet"
        )

        ruta = carpeta / nombre
        temporal = ruta.with_suffix(".parquet.tmp")

        if ruta.exists():
            raise RuntimeError(
                f"Ya existe un lote con el mismo nombre: {ruta}. "
                "Se requiere revisar sus offsets."
            )

        tabla = pa.Table.from_pylist(filas)

        try:
            pq.write_table(
                tabla,
                temporal,
                compression="snappy"
            )

            filas_guardadas = (
                pq.ParquetFile(temporal).metadata.num_rows
            )

            if filas_guardadas != len(filas):
                raise RuntimeError(
                    f"Conteo incorrecto en el lote: {ruta}"
                )

            temporal.replace(ruta)

        finally:
            if temporal.exists():
                temporal.unlink()

        escritos += len(filas)

        print(
            f"Bronze -> "
            f"{ruta.relative_to(RAIZ_PROYECTO)} "
            f"({len(filas):,} registros)"
        )

    return escritos


# ============================================================
# CONSUMIR MENSAJES DESDE KAFKA
# ============================================================

def consumir(fuente, expected=None, batch_size=50000):

    if batch_size <= 0:
        raise ValueError(
            "El tamaño del lote debe ser mayor que cero."
        )

    config = FUENTES[fuente]

    if expected is None:
        expected = config["esperados"]

    if expected <= 0:
        raise ValueError(
            "El total esperado debe ser mayor que cero."
        )

    topic = config["topic"]

    offsets_existentes, total_inicial = (
        leer_estado_bronze(fuente)
    )

    print("=" * 75)
    print("PROYECTO 2 - KAFKA -> BRONZE")
    print("=" * 75)
    print(f"Fuente:                {fuente}")
    print(f"Topic:                 {topic}")
    print(f"Servidor:              {BOOTSTRAP_SERVERS}")
    print(f"Registros existentes:  {total_inicial:,}")
    print(f"Objetivo:              {expected:,}")
    print("=" * 75)

    if total_inicial > expected:
        raise RuntimeError(
            f"Bronze contiene {total_inicial:,} registros "
            f"y solo se esperan {expected:,}."
        )

    if total_inicial == expected:
        print(
            "RESULTADO: BRONZE YA ESTA COMPLETA. "
            "SE OMITE EL CONSUMO POR IDEMPOTENCIA."
        )
        return

    consumidor = Consumer({
        "bootstrap.servers": BOOTSTRAP_SERVERS,
        "group.id": f"bronze_p2_{fuente}",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })

    buffer = []
    offsets_buffer = set()
    ultimos_offsets = {}

    nuevos = 0
    duplicados_omitidos = 0
    ultima_actividad = time.monotonic()

    def guardar_y_confirmar():
        nonlocal nuevos

        if buffer:
            escribir_batch(buffer, fuente)

            for clave in offsets_buffer:
                offsets_existentes.add(clave)

            nuevos += len(buffer)

            buffer.clear()
            offsets_buffer.clear()

        # Confirmar solamente offsets de mensajes que
        # ya quedaron almacenados o fueron verificados
        # como existentes en Bronze.
        if ultimos_offsets:
            posiciones = [
                TopicPartition(
                    topic,
                    particion,
                    offset + 1
                )
                for particion, offset
                in ultimos_offsets.items()
            ]

            consumidor.commit(
                offsets=posiciones,
                asynchronous=False
            )

            ultimos_offsets.clear()

    try:
        # Obtener las particiones del topic.
        metadata = consumidor.list_topics(
            topic=topic,
            timeout=20
        )

        if topic not in metadata.topics:
            raise RuntimeError(
                f"El topic {topic} no existe en Kafka."
            )

        info_topic = metadata.topics[topic]

        if info_topic.error is not None:
            raise RuntimeError(
                f"Error en topic {topic}: "
                f"{info_topic.error}"
            )

        particiones = []

        for numero in sorted(info_topic.partitions):
            particion = TopicPartition(topic, numero)

            minimo, _ = consumidor.get_watermark_offsets(
                particion,
                timeout=20
            )

            particiones.append(
                TopicPartition(topic, numero, minimo)
            )

        if not particiones:
            raise RuntimeError(
                f"El topic {topic} no tiene particiones."
            )

        # Releer desde el inicio disponible de Kafka.
        # Los offsets ya escritos en Bronze se omiten.
        consumidor.assign(particiones)

        while total_inicial + nuevos < expected:

            mensaje = consumidor.poll(1.0)

            if mensaje is None:
                if (
                    time.monotonic() - ultima_actividad
                    > TIEMPO_MAXIMO_INACTIVIDAD
                ):
                    raise TimeoutError(
                        f"Ingesta incompleta para {fuente}. "
                        f"Bronze inicial={total_inicial:,}; "
                        f"nuevos={nuevos:,}; "
                        f"esperados={expected:,}."
                    )

                continue

            if mensaje.error():
                if (
                    mensaje.error().code()
                    == KafkaError._PARTITION_EOF
                ):
                    continue

                raise RuntimeError(
                    str(mensaje.error())
                )

            particion = mensaje.partition()
            offset = mensaje.offset()
            clave = (particion, offset)

            ultima_actividad = time.monotonic()

            # Un offset existente no vuelve a escribirse.
            if clave in offsets_existentes:
                duplicados_omitidos += 1
                ultimos_offsets[particion] = offset
                continue

            if clave in offsets_buffer:
                raise RuntimeError(
                    f"Offset repetido en buffer: {clave}"
                )

            ahora = datetime.now(timezone.utc)

            registro = {
                "source_system": fuente,
                "source_file": config["archivo"],
                "raw_value": mensaje.value().decode("utf-8"),
                "kafka_topic": mensaje.topic(),
                "kafka_partition": particion,
                "kafka_offset": offset,
                "ingestion_timestamp": ahora.isoformat(),
                "ingestion_date": ahora.date().isoformat(),
            }

            buffer.append(registro)
            offsets_buffer.add(clave)

            ultimos_offsets[particion] = offset

            if len(buffer) >= batch_size:
                guardar_y_confirmar()

            if (
                total_inicial + nuevos + len(buffer)
                >= expected
            ):
                guardar_y_confirmar()
                break

        # Validación final directamente contra Parquet.
        _, total_final = leer_estado_bronze(fuente)

        print("\n" + "=" * 75)
        print(f"Registros anteriores:    {total_inicial:,}")
        print(f"Registros nuevos:        {nuevos:,}")
        print(f"Duplicados omitidos:     {duplicados_omitidos:,}")
        print(f"Total final en Bronze:   {total_final:,}")
        print(f"Registros esperados:     {expected:,}")
        print(f"Diferencia:              {total_final - expected:,}")
        print("=" * 75)

        if total_final != expected:
            raise RuntimeError(
                f"Conteo final incorrecto para {fuente}: "
                f"{total_final} != {expected}"
            )

        print(
            "RESULTADO: STREAMING RECONCILIADO CORRECTAMENTE"
        )

    finally:
        consumidor.close()


# ============================================================
# EJECUCION POR TERMINAL
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--source",
        choices=list(FUENTES.keys()),
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
        batch_size=args.batch_size,
    )
