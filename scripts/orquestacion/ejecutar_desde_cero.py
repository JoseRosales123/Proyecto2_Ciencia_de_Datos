
from pathlib import Path
import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time

import psycopg
import pyarrow.parquet as pq
from dotenv import dotenv_values
from confluent_kafka import Consumer, TopicPartition
from confluent_kafka.admin import AdminClient, NewTopic


# ============================================================
# PROYECTO 2 - ORQUESTADOR INTEGRADO
# ============================================================

RAIZ = Path(__file__).resolve().parents[2]
PYTHON = sys.executable

PROYECTO_DOCKER = "proyecto2_ciencia_datos"

VOLUMENES_P2 = {
    "proyecto2_ciencia_datos_kafka_data",
    "proyecto2_ciencia_datos_postgres_data",
}

SERVICIOS_P2 = {"kafka", "postgres"}

BRONZE_DIR = RAIZ / "bronze"
REPORTES_DIR = RAIZ / "docs" / "reportes_fase1"

DBT_DIR = RAIZ / "dbt_red_metropolitana"
PROFILES_DIR = DBT_DIR / "config"

FUENTES_STREAMING = [
    {
        "fuente": "transmetro",
        "topic": "transmetro_validaciones",
        "esperados": 713786,
        "productor": "scripts/streaming/productor_transmetro.py",
    },
    {
        "fuente": "aerometro",
        "topic": "aerometro_boardings",
        "esperados": 387053,
        "productor": "scripts/streaming/productor_aerometro.py",
    },
]

TIEMPOS = []
MODO_DESDE_CERO = False


# ============================================================
# CONFIGURACION
# ============================================================

def argumentos():
    parser = argparse.ArgumentParser(
        description="Pipeline integrado del Proyecto 2"
    )

    parser.add_argument(
        "--desde-cero",
        action="store_true",
        help="Reinicializa exclusivamente los datos generados P2",
    )

    parser.add_argument(
        "--confirmar-borrado-p2",
        action="store_true",
        help="Autoriza el borrado de los datos P2",
    )

    return parser.parse_args()


def preparar_entorno():
    env_path = RAIZ / ".env"

    if not env_path.is_file():
        raise RuntimeError(
            "Falta .env con la configuración del Proyecto 2."
        )

    for clave, valor in dotenv_values(env_path).items():
        if valor is not None:
            os.environ[clave] = valor

    os.environ.setdefault("POSTGRES_HOST", "localhost")
    os.environ.setdefault("POSTGRES_PORT", "5434")
    os.environ.setdefault(
        "KAFKA_BOOTSTRAP_SERVERS",
        "localhost:9094",
    )

    os.environ["DBT_PROFILES_DIR"] = str(PROFILES_DIR)

    if not (PROFILES_DIR / "profiles.yml").is_file():
        raise RuntimeError(
            "Falta dbt_red_metropolitana/config/profiles.yml"
        )

    clave = os.environ.get("PSEUDONYMIZATION_KEY")

    if not clave:
        raise RuntimeError(
            "Falta PSEUDONYMIZATION_KEY en .env."
        )

    os.environ["PGOPTIONS"] = (
        f"-c app.pseudonymization_key={clave}"
    )

    if os.environ["POSTGRES_HOST"] not in (
        "localhost", "127.0.0.1"
    ):
        raise RuntimeError(
            "El reinicio seguro requiere PostgreSQL local."
        )

    if os.environ["POSTGRES_PORT"] != "5434":
        raise RuntimeError(
            "El puerto PostgreSQL P2 debe ser 5434."
        )

    if (
        os.environ["KAFKA_BOOTSTRAP_SERVERS"]
        != "localhost:9094"
    ):
        raise RuntimeError(
            "Kafka P2 debe utilizar localhost:9094."
        )


# ============================================================
# EJECUCION Y REGISTRO DE TIEMPOS
# ============================================================

def ejecutar(nombre, comando, cwd=None):
    print("\n" + "=" * 75, flush=True)
    print("ETAPA:", nombre, flush=True)
    print("=" * 75, flush=True)

    inicio = time.perf_counter()
    estado = "ERROR"

    try:
        subprocess.run(
            comando,
            cwd=str(cwd or RAIZ),
            env=os.environ.copy(),
            check=True,
        )

        estado = "OK"

    finally:
        duracion = round(
            time.perf_counter() - inicio, 2
        )

        TIEMPOS.append({
            "etapa": nombre,
            "segundos": duracion,
            "estado": estado,
        })

        print(
            f"{nombre}: {duracion:.2f}s [{estado}]",
            flush=True,
        )


def medir(nombre, funcion):
    inicio = time.perf_counter()
    estado = "ERROR"

    try:
        resultado = funcion()
        estado = "OK"
        return resultado

    finally:
        duracion = round(
            time.perf_counter() - inicio, 2
        )

        TIEMPOS.append({
            "etapa": nombre,
            "segundos": duracion,
            "estado": estado,
        })

        print(
            f"{nombre}: {duracion:.2f}s [{estado}]",
            flush=True,
        )


def ejecutar_python(nombre, archivo, *args):
    ejecutar(
        nombre,
        [PYTHON, str(RAIZ / archivo), *args],
    )


# ============================================================
# COMPROBACIONES DE SEGURIDAD
# ============================================================

def comprobar_compose():
    resultado = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        check=True,
    )

    config = json.loads(resultado.stdout)

    if config.get("name") != PROYECTO_DOCKER:
        raise RuntimeError(
            "SEGURIDAD: nombre inesperado del proyecto Docker."
        )

    servicios = set(config.get("services", {}).keys())

    if servicios != SERVICIOS_P2:
        raise RuntimeError(
            f"SEGURIDAD: servicios inesperados: {servicios}"
        )

    volumenes = set(config.get("volumes", {}).keys())

    if volumenes != {"kafka_data", "postgres_data"}:
        raise RuntimeError(
            f"SEGURIDAD: volúmenes inesperados: {volumenes}"
        )

    for nombre, volumen in config["volumes"].items():
        nombre_real = volumen.get(
            "name",
            f"{PROYECTO_DOCKER}_{nombre}",
        )

        if nombre_real not in VOLUMENES_P2:
            raise RuntimeError(
                "SEGURIDAD: volumen fuera del Proyecto 2: "
                + nombre_real
            )

    # Evita bajar servicios que monten otros volúmenes
    # nombrados o rutas del host.
    for servicio, datos in config["services"].items():
        for montaje in datos.get("volumes", []):
            if montaje.get("type") != "volume":
                raise RuntimeError(
                    "SEGURIDAD: montaje no permitido en "
                    + servicio
                )

            if montaje.get("source") not in {
                "kafka_data",
                "postgres_data",
            }:
                raise RuntimeError(
                    "SEGURIDAD: origen de volumen inesperado."
                )

    print("Compose validado: solamente Proyecto 2.")


def comprobar_volumenes():
    resultado = subprocess.run(
        [
            "docker", "volume", "inspect",
            *sorted(VOLUMENES_P2),
        ],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
    )

    # En el primer arranque los volúmenes pueden
    # no existir todavía.
    if resultado.returncode != 0:
        existentes = []

        for volumen in sorted(VOLUMENES_P2):
            individual = subprocess.run(
                ["docker", "volume", "inspect", volumen],
                capture_output=True,
                text=True,
            )

            if individual.returncode == 0:
                existentes.extend(
                    json.loads(individual.stdout)
                )

    else:
        existentes = json.loads(resultado.stdout)

    for volumen in existentes:
        nombre = volumen["Name"]
        etiquetas = volumen.get("Labels") or {}

        if nombre not in VOLUMENES_P2:
            raise RuntimeError(
                "SEGURIDAD: volumen desconocido."
            )

        if (
            etiquetas.get("com.docker.compose.project")
            != PROYECTO_DOCKER
        ):
            raise RuntimeError(
                "SEGURIDAD: etiquetas incorrectas en "
                + nombre
            )

    print("Volúmenes existentes identificados como P2.")


def limpiar_bronze_con_reintentos():
    comprobar_ruta_bronze()

    if not BRONZE_DIR.exists():
        print("Bronze ya está vacía.")
        return

    # Eliminar archivos generados sin borrar los directorios.
    # Importante para carpetas administradas por OneDrive.
    archivos = [
        ruta
        for ruta in BRONZE_DIR.rglob("*")
        if ruta.is_file()
    ]

    print(
        f"Archivos generados encontrados: {len(archivos)}"
    )

    errores = []

    for archivo in archivos:
        eliminado = False

        for intento in range(1, 7):
            try:
                archivo.unlink()
                eliminado = True
                break

            except PermissionError:
                print(
                    f"Archivo bloqueado: {archivo.name}. "
                    f"Reintento {intento}/6..."
                )
                time.sleep(3)

        if not eliminado:
            errores.append(str(archivo))

    if errores:
        raise RuntimeError(
            "No se pudieron eliminar estos archivos "
            "de Bronze:\n" + "\n".join(errores[:10])
        )

    restantes = [
        ruta
        for ruta in BRONZE_DIR.rglob("*")
        if ruta.is_file()
    ]

    if restantes:
        raise RuntimeError(
            "Bronze todavía contiene archivos."
        )

    print(
        "Bronze P2 limpia. "
        "Se conservaron los directorios existentes."
    )


def comprobar_ruta_bronze():
    raiz_real = RAIZ.resolve()
    bronze_real = BRONZE_DIR.resolve()

    if bronze_real != raiz_real / "bronze":
        raise RuntimeError(
            "SEGURIDAD: ruta Bronze inesperada."
        )

    if BRONZE_DIR.is_symlink():
        raise RuntimeError(
            "SEGURIDAD: Bronze no puede ser un enlace simbólico."
        )


# ============================================================
# REINICIO CONTROLADO DEL PROYECTO 2
# ============================================================

def reinicializar_p2():
    comprobar_compose()
    comprobar_volumenes()
    comprobar_ruta_bronze()

    print("\n" + "!" * 75)
    print("REINICIALIZACION EXCLUSIVA DEL PROYECTO 2")
    print("!" * 75)
    print("Se eliminarán:")
    print("  - Volumen Kafka P2")
    print("  - Volumen PostgreSQL P2")
    print("  - Archivos Parquet y manifiestos en bronze/")
    print()
    print("Se conservarán:")
    print("  - Datos originales datos_red/")
    print("  - Código, Git, README y .env")
    print("  - Evidencias y reportes anteriores")
    print("  - Todos los recursos del Proyecto 1")
    print()

    confirmacion = input(
        "Escribe REINICIAR PROYECTO 2 para continuar: "
    ).strip()

    if confirmacion != "REINICIAR PROYECTO 2":
        raise RuntimeError(
            "Reinicio cancelado. No se eliminaron datos."
        )

    # El comando solo actúa sobre los servicios
    # declarados en este Docker Compose validado.
    ejecutar(
        "Reiniciar volúmenes Docker P2",
        [
            "docker",
            "compose",
            "down",
            "--volumes",
        ],
    )

    comprobar_ruta_bronze()

    limpiar_bronze_con_reintentos()

    print("Bronze P2 reinicializada.")
    print("Proyecto 1 no modificado.")


# ============================================================
# POSTGRESQL
# ============================================================

def conectar_postgres():
    return psycopg.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def preparar_postgres():
    ultimo_error = None

    for _ in range(30):
        try:
            with conectar_postgres() as conexion:
                with conexion.cursor() as cursor:
                    for esquema in [
                        "staging",
                        "silver",
                        "gold",
                        "cuarentena",
                        "features",
                    ]:
                        cursor.execute(
                            "CREATE SCHEMA IF NOT EXISTS "
                            + esquema
                        )

                    cursor.execute(
                        "CREATE EXTENSION IF NOT EXISTS pgcrypto"
                    )

            print("PostgreSQL P2 preparado.")
            return

        except psycopg.OperationalError as error:
            ultimo_error = error
            time.sleep(2)

    raise RuntimeError(
        "PostgreSQL P2 no respondió."
    ) from ultimo_error


# ============================================================
# KAFKA
# ============================================================

def crear_admin_kafka():
    return AdminClient({
        "bootstrap.servers":
            os.environ["KAFKA_BOOTSTRAP_SERVERS"]
    })


def preparar_kafka():
    admin = crear_admin_kafka()
    ultimo_error = None

    for _ in range(30):
        try:
            metadata = admin.list_topics(timeout=10)
            break

        except Exception as error:
            ultimo_error = error
            time.sleep(2)

    else:
        raise RuntimeError(
            "Kafka P2 no respondió."
        ) from ultimo_error

    existentes = set(metadata.topics.keys())

    nuevos = [
        NewTopic(
            item["topic"],
            num_partitions=1,
            replication_factor=1,
        )
        for item in FUENTES_STREAMING
        if item["topic"] not in existentes
    ]

    if nuevos:
        resultados = admin.create_topics(nuevos)

        for futuro in resultados.values():
            futuro.result(timeout=30)

    print("Kafka P2 preparado.")


def mensajes_kafka(topic):
    consumidor = Consumer({
        "bootstrap.servers":
            os.environ["KAFKA_BOOTSTRAP_SERVERS"],
        "group.id": "verificador_p2",
        "enable.auto.commit": False,
    })

    try:
        inicio, final = consumidor.get_watermark_offsets(
            TopicPartition(topic, 0),
            timeout=15,
            cached=False,
        )

        if inicio != 0:
            raise RuntimeError(
                f"{topic}: Kafka perdió eventos iniciales."
            )

        return final

    finally:
        consumidor.close()


def contar_bronze(fuente):
    carpeta = BRONZE_DIR / fuente

    return sum(
        pq.ParquetFile(ruta).metadata.num_rows
        for ruta in carpeta.rglob("*.parquet")
    )


def publicar(item):
    cantidad = mensajes_kafka(item["topic"])
    esperados = item["esperados"]

    if cantidad == esperados:
        print(
            f"{item['topic']}: publicación completa existente."
        )
        return

    if cantidad == 0:
        ejecutar_python(
            "Publicar " + item["fuente"],
            item["productor"],
        )
        return

    if (
        not MODO_DESDE_CERO
        and item["fuente"] == "transmetro"
        and cantidad == 100
    ):
        ejecutar_python(
            "Completar publicación Transmetro",
            item["productor"],
            "--skip",
            "100",
        )
        return

    raise RuntimeError(
        f"Publicación parcial en {item['topic']}: "
        f"{cantidad:,} eventos. "
        "No se reintentará automáticamente para "
        "evitar duplicados."
    )


def consumir(item):
    cantidad = mensajes_kafka(item["topic"])

    if cantidad != item["esperados"]:
        raise RuntimeError(
            f"Kafka {item['topic']}: "
            f"{cantidad:,} de {item['esperados']:,}."
        )

    registros = contar_bronze(item["fuente"])

    if registros == item["esperados"]:
        print(
            f"Bronze {item['fuente']}: carga completa existente."
        )
        return

    if registros > item["esperados"]:
        raise RuntimeError(
            "Bronze tiene más registros de los esperados."
        )

    ejecutar_python(
        "Consumir " + item["fuente"],
        "scripts/streaming/consumidor_bronze.py",
        "--source",
        item["fuente"],
        "--expected",
        str(item["esperados"]),
    )


# ============================================================
# REPORTE DE TIEMPOS
# ============================================================

def guardar_tiempos():
    REPORTES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    destino = REPORTES_DIR / "tiempos_etapas.csv"

    with destino.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as archivo:
        escritor = csv.DictWriter(
            archivo,
            fieldnames=[
                "etapa",
                "segundos",
                "estado",
            ],
        )
        escritor.writeheader()
        escritor.writerows(TIEMPOS)

    print("\nReporte:", destino)


# ============================================================
# EJECUCION PRINCIPAL
# ============================================================

def main():
    global MODO_DESDE_CERO

    args = argumentos()
    MODO_DESDE_CERO = args.desde_cero

    if args.confirmar_borrado_p2 and not args.desde_cero:
        raise RuntimeError(
            "--confirmar-borrado-p2 requiere --desde-cero."
        )

    if args.desde_cero and not args.confirmar_borrado_p2:
        raise RuntimeError(
            "Para reiniciar, añade "
            "--confirmar-borrado-p2. "
            "No se ha eliminado ningún dato."
        )

    inicio_total = time.perf_counter()
    estado_final = "ERROR"

    try:
        preparar_entorno()

        # Siempre comprobar el proyecto Docker.
        medir(
            "Verificar aislamiento Docker P2",
            comprobar_compose,
        )

        # Verificar fuentes antes de cualquier borrado.
        ejecutar_python(
            "Validar fuentes originales",
            "scripts/inventario_fuentes.py",
        )

        if MODO_DESDE_CERO:
            medir(
                "Reinicialización de datos P2",
                reinicializar_p2,
            )

        ejecutar(
            "Iniciar Docker Compose",
            ["docker", "compose", "up", "-d"],
        )

        medir(
            "Preparar PostgreSQL",
            preparar_postgres,
        )

        medir(
            "Preparar Kafka",
            preparar_kafka,
        )

        ejecutar_python(
            "Ingesta Batch",
            "scripts/batch/cargar_batch_bronze.py",
            "--source",
            "all",
        )

        ejecutar_python(
            "Ingesta CDC Bronze",
            "scripts/cdc/cargar_cdc_bronze.py",
        )

        for item in FUENTES_STREAMING:
            medir(
                "Publicación Streaming " + item["fuente"],
                lambda item=item: publicar(item),
            )

            medir(
                "Consumo Streaming " + item["fuente"],
                lambda item=item: consumir(item),
            )

        ejecutar_python(
            "Reconciliación global Bronze",
            "scripts/validaciones/inventario_bronze.py",
        )

        for fuente in ("transmetro", "aerometro"):
            ejecutar_python(
                "Validar integridad " + fuente,
                "scripts/validaciones/validar_bronze.py",
                "--source",
                fuente,
            )

        ejecutar_python(
            "Pipeline Prefect Staging Silver Gold",
            "scripts/orquestacion/flujo_fase1.py",
        )

        estado_final = "OK"

        print("\n" + "=" * 75)
        print("PIPELINE PROYECTO 2 COMPLETADO")
        print("RESULTADO: OK")
        print("=" * 75)

    finally:
        TIEMPOS.append({
            "etapa": "TOTAL",
            "segundos": round(
                time.perf_counter() - inicio_total,
                2,
            ),
            "estado": estado_final,
        })

        guardar_tiempos()


if __name__ == "__main__":
    main()
