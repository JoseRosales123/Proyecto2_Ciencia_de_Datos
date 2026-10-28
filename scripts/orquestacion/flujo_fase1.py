from pathlib import Path
from datetime import datetime
import json
import os
import subprocess
import sys
import time

import psycopg
from dotenv import load_dotenv
from prefect import flow, task, get_run_logger


# ============================================================
# RUTAS DEL PROYECTO
# ============================================================

RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

DBT_DIR = RAIZ_PROYECTO / "dbt_red_metropolitana"

METRICAS_DIR = (
    RAIZ_PROYECTO
    / "docs"
    / "metricas_prefect"
)


# ============================================================
# ENTORNO
# ============================================================

def cargar_entorno():

    load_dotenv(
        RAIZ_PROYECTO / ".env",
        override=True
    )

    return os.environ.copy()


# ============================================================
# EJECUCIÓN DE COMANDOS
# ============================================================

def ejecutar_comando(
    nombre,
    comando,
    cwd=None,
):

    logger = get_run_logger()

    if cwd is None:
        cwd = RAIZ_PROYECTO

    logger.info("=" * 75)
    logger.info(nombre)
    logger.info("=" * 75)

    inicio = time.perf_counter()

    resultado = subprocess.run(
        comando,
        cwd=str(cwd),
        env=cargar_entorno(),
        text=True,
        capture_output=True,
    )

    duracion = time.perf_counter() - inicio

    if resultado.stdout:
        logger.info(resultado.stdout)

    if resultado.returncode != 0:

        if resultado.stderr:
            logger.error(resultado.stderr)

        raise RuntimeError(
            f"Falló la etapa: {nombre}"
        )

    logger.info(
        f"{nombre} completado en "
        f"{duracion:.2f} segundos."
    )

    return round(duracion, 2)


# ============================================================
# TAREAS PREFECT
# ============================================================

@task(
    name="Validar capa Bronze",
    retries=1,
    retry_delay_seconds=5,
)
def validar_bronze():

    return ejecutar_comando(
        "VALIDACIÓN GLOBAL DE BRONZE",
        [
            sys.executable,
            "scripts/validaciones/inventario_bronze.py",
        ],
    )


@task(
    name="Cargar CDC a Staging",
    retries=1,
    retry_delay_seconds=5,
)
def cargar_cdc_staging():

    return ejecutar_comando(
        "BRONZE -> STAGING | CDC",
        [
            sys.executable,
            "scripts/staging/cargar_cdc_staging.py",
        ],
    )


@task(
    name="Aplicar CDC del padrón",
    retries=1,
    retry_delay_seconds=5,
)
def aplicar_cdc():

    return ejecutar_comando(
        "APLICAR CDC AL PADRÓN",
        [
            sys.executable,
            "scripts/staging/aplicar_cdc_padron.py",
        ],
    )


@task(
    name="Construir catálogos de usuarios",
    retries=1,
    retry_delay_seconds=5,
)
def construir_catalogos_usuarios():

    return ejecutar_comando(
        "CATÁLOGOS MÍNIMOS DE USUARIOS",
        [
            sys.executable,
            "scripts/staging/construir_catalogos_usuarios.py",
        ],
    )


@task(
    name="Cargar operaciones a Staging",
    retries=1,
    retry_delay_seconds=5,
)
def cargar_operaciones_staging():

    return ejecutar_comando(
        "BRONZE -> STAGING | OPERACIONES",
        [
            sys.executable,
            "scripts/staging/cargar_operaciones_staging.py",
        ],
    )


@task(
    name="Cargar catálogos a Staging",
    retries=1,
    retry_delay_seconds=5,
)
def cargar_catalogos_staging():

    return ejecutar_comando(
        "BRONZE -> STAGING | CATÁLOGOS",
        [
            sys.executable,
            "scripts/staging/cargar_catalogos_staging.py",
        ],
    )


@task(
    name="Ejecutar modelos dbt",
    retries=1,
    retry_delay_seconds=5,
)
def ejecutar_dbt_run():

    return ejecutar_comando(
        "DBT RUN | SILVER + CUARENTENA + GOLD",
        [
            "dbt",
            "run",
        ],
        cwd=DBT_DIR,
    )


@task(
    name="Ejecutar pruebas dbt",
    retries=1,
    retry_delay_seconds=5,
)
def ejecutar_dbt_test():

    return ejecutar_comando(
        "DBT TEST | VALIDACIÓN GLOBAL",
        [
            "dbt",
            "test",
        ],
        cwd=DBT_DIR,
    )


# ============================================================
# MÉTRICAS
# ============================================================

@task(name="Capturar métricas finales")
def capturar_metricas():

    logger = get_run_logger()

    cargar_entorno()

    with psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5434")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    ) as conexion:

        with conexion.cursor() as cursor:

            def contar(tabla):

                cursor.execute(
                    f"SELECT COUNT(*) FROM {tabla};"
                )

                return cursor.fetchone()[0]

            metricas = {

                "staging": {
                    "transmetro": contar(
                        "staging.transmetro_validaciones"
                    ),
                    "transurbano": contar(
                        "staging.transurbano_transacciones"
                    ),
                    "metroriel": contar(
                        "staging.metroriel_viajes"
                    ),
                    "aerometro": contar(
                        "staging.aerometro_boardings"
                    ),
                    "cdc": contar(
                        "staging.cdc_padron_usuarios"
                    ),
                },

                "silver": {
                    "transmetro_validos": contar(
                        "silver.silver_transmetro_validaciones"
                    ),
                    "transurbano_validos": contar(
                        "silver.silver_transurbano_transacciones"
                    ),
                    "metroriel_validos": contar(
                        "silver.silver_metroriel_viajes"
                    ),
                    "aerometro_validos": contar(
                        "silver.silver_aerometro_boardings"
                    ),
                    "versiones_scd2": contar(
                        "silver.silver_padron_usuarios_scd2"
                    ),
                },

                "cuarentena": {
                    "total": contar(
                        "cuarentena.cuarentena_global"
                    ),
                },

                "gold": {
                    "dim_tiempo": contar(
                        "gold.dim_tiempo"
                    ),
                    "dim_usuario": contar(
                        "gold.dim_usuario"
                    ),
                    "dim_zona": contar(
                        "gold.dim_zona"
                    ),
                    "dim_modo_transporte": contar(
                        "gold.dim_modo_transporte"
                    ),
                    "dim_punto_servicio": contar(
                        "gold.dim_punto_servicio"
                    ),
                    "fact_abordajes": contar(
                        "gold.fact_abordajes"
                    ),
                    "fact_viajes_metroriel": contar(
                        "gold.fact_viajes_metroriel"
                    ),
                },
            }

            # --------------------------------------------
            # Estado actual del padrón
            # --------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE es_version_actual
                    ),
                    COUNT(*) FILTER (
                        WHERE es_version_actual
                          AND activo
                    ),
                    COUNT(*) FILTER (
                        WHERE es_version_actual
                          AND NOT activo
                    )
                FROM silver.silver_padron_usuarios_scd2;
                """
            )

            (
                versiones_actuales,
                usuarios_activos,
                usuarios_inactivos,
            ) = cursor.fetchone()

            metricas["padron"] = {
                "versiones_actuales": versiones_actuales,
                "activos": usuarios_activos,
                "inactivos": usuarios_inactivos,
            }

            # --------------------------------------------
            # Calidad por regla
            # --------------------------------------------

            cursor.execute(
                """
                SELECT
                    regla,
                    registros_regla
                FROM silver.silver_resumen_calidad
                ORDER BY regla;
                """
            )

            metricas["calidad"] = {
                regla: cantidad
                for regla, cantidad
                in cursor.fetchall()
            }

    logger.info("=" * 75)
    logger.info("MÉTRICAS FINALES DE LA CORRIDA")
    logger.info("=" * 75)

    logger.info(
        json.dumps(
            metricas,
            indent=2,
            ensure_ascii=False,
        )
    )

    return metricas


# ============================================================
# GUARDAR EVIDENCIA DE CORRIDA
# ============================================================

@task(name="Guardar métricas de la corrida")
def guardar_metricas(
    metricas,
    tiempos,
    duracion_total,
):

    logger = get_run_logger()

    METRICAS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    corrida_id = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    salida = {
        "corrida_id": corrida_id,
        "metricas": metricas,
        "tiempos_segundos": tiempos,
        "duracion_total_segundos": round(
            duracion_total,
            2
        ),
    }

    ruta = (
        METRICAS_DIR
        / f"corrida_{corrida_id}.json"
    )

    with ruta.open(
        "w",
        encoding="utf-8",
    ) as archivo:

        json.dump(
            salida,
            archivo,
            indent=4,
            ensure_ascii=False,
        )

    logger.info(
        f"Métricas guardadas en: "
        f"{ruta.relative_to(RAIZ_PROYECTO)}"
    )

    return str(ruta)


# ============================================================
# FLOW PRINCIPAL
# ============================================================

@flow(
    name="Fase 1 - Red Metropolitana",
    log_prints=True,
)
def flujo_fase1():

    logger = get_run_logger()

    logger.info("=" * 75)
    logger.info(
        "INICIO DEL PIPELINE COMPLETO - FASE 1"
    )
    logger.info("=" * 75)

    inicio_total = time.perf_counter()

    tiempos = {}

    # 1. Bronze
    tiempos["validar_bronze"] = (
        validar_bronze()
    )

    # 2. Staging + CDC
    tiempos["cargar_cdc_staging"] = (
        cargar_cdc_staging()
    )

    tiempos["aplicar_cdc"] = (
        aplicar_cdc()
    )

    tiempos["catalogos_usuarios"] = (
        construir_catalogos_usuarios()
    )

    tiempos["operaciones_staging"] = (
        cargar_operaciones_staging()
    )

    tiempos["catalogos_staging"] = (
        cargar_catalogos_staging()
    )

    # 3. Silver + Gold con dbt
    tiempos["dbt_run"] = (
        ejecutar_dbt_run()
    )

    tiempos["dbt_test"] = (
        ejecutar_dbt_test()
    )

    # 4. Métricas
    metricas = capturar_metricas()

    duracion_total = (
        time.perf_counter()
        - inicio_total
    )

    ruta_metricas = guardar_metricas(
        metricas,
        tiempos,
        duracion_total,
    )

    logger.info("=" * 75)
    logger.info(
        "PIPELINE FASE 1 COMPLETADO CORRECTAMENTE"
    )
    logger.info(
        f"Duración total: "
        f"{duracion_total:.2f} segundos"
    )
    logger.info(
        f"Evidencia: {ruta_metricas}"
    )
    logger.info("=" * 75)

    return metricas


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == "__main__":
    flujo_fase1()