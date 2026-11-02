
import csv
import os
from datetime import date, timedelta
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ / ".env")

SALIDA = RAIZ / "docs" / "reportes_fase1_2"

CORTES = [
    ("A", date(2026, 7, 1)),
    ("B", date(2026, 7, 31)),
]

SQL_EVENTOS = """
CREATE TEMP TABLE eventos_12 AS
WITH movimientos AS (
    SELECT
        'Transmetro'::text AS sistema,
        usuario_fuente::text AS identificador,
        fecha_hora_local AT TIME ZONE 'UTC' AS fecha
    FROM silver.silver_transmetro_validaciones

    UNION ALL

    SELECT
        'Transurbano',
        usuario_fuente::text,
        fecha_hora_local
    FROM silver.silver_transurbano_transacciones

    UNION ALL

    SELECT
        'MetroRiel',
        usuario_fuente::text,
        entry_ts
    FROM silver.silver_metroriel_viajes

    UNION ALL

    SELECT
        'Aerometro',
        usuario_fuente::text,
        fecha_hora_local
    FROM silver.silver_aerometro_boardings
)
SELECT
    m.sistema,
    m.identificador,
    m.fecha,
    i.usuario_seudonimo,
    m.sistema || '|' || m.identificador AS tarjeta_operador
FROM movimientos m
LEFT JOIN silver.silver_identidad_usuarios_seudonimizada i
  ON i.sistema = m.sistema
 AND i.llave_original = m.identificador
WHERE m.fecha >= TIMESTAMP '2026-06-03'
  AND m.fecha < TIMESTAMP '2026-08-30'
"""

SQL_ULTIMAS_OPERACIONES = """
CREATE TEMP TABLE ultimas_cdc_12 AS
SELECT DISTINCT ON (tarjeta)
       tarjeta,
       op
FROM staging.cdc_padron_usuarios
WHERE tarjeta IS NOT NULL
  AND commit_ts < %s
ORDER BY tarjeta, commit_ts DESC, seq DESC
"""

SQL_DISPONIBILIDAD = """
CREATE TEMP TABLE disponibilidad_12 AS
SELECT
    i.usuario_seudonimo,
    i.sistema || '|' || i.llave_original AS tarjeta_operador,
    CASE
        WHEN i.sistema <> 'Transmetro' THEN TRUE
        WHEN c.op = 'DELETE' THEN FALSE
        ELSE TRUE
    END AS habilitada
FROM silver.silver_identidad_usuarios_seudonimizada i
LEFT JOIN ultimas_cdc_12 c
  ON i.sistema = 'Transmetro'
 AND i.llave_original = c.tarjeta
"""

SQL_DISPONIBILIDAD_PERSONA = """
CREATE TEMP TABLE disponibilidad_persona_12 AS
SELECT
    usuario_seudonimo,
    BOOL_OR(habilitada) AS habilitada
FROM disponibilidad_12
GROUP BY usuario_seudonimo
"""

SQL_CONTEO_PERSONA = """
WITH actividad AS (
    SELECT
        usuario_seudonimo AS unidad,
        COUNT(*) FILTER (
            WHERE fecha >= %s
              AND fecha < %s
        ) AS abordajes_previos,
        COUNT(*) FILTER (
            WHERE fecha >= %s
              AND fecha < %s
        ) AS abordajes_posteriores
    FROM eventos_12
    WHERE usuario_seudonimo IS NOT NULL
      AND fecha >= %s
      AND fecha < %s
    GROUP BY usuario_seudonimo
),
elegibles AS (
    SELECT a.*
    FROM actividad a
    JOIN disponibilidad_persona_12 d
      ON d.usuario_seudonimo = a.unidad
    WHERE a.abordajes_previos >= 2
      AND d.habilitada
)
SELECT
    COUNT(*) AS poblacion_elegible,
    COUNT(*) FILTER (
        WHERE abordajes_posteriores = 0
    ) AS positivos,
    COUNT(*) FILTER (
        WHERE abordajes_posteriores > 0
    ) AS negativos
FROM elegibles
"""

SQL_CONTEO_TARJETA = """
WITH actividad AS (
    SELECT
        tarjeta_operador AS unidad,
        COUNT(*) FILTER (
            WHERE fecha >= %s
              AND fecha < %s
        ) AS abordajes_previos,
        COUNT(*) FILTER (
            WHERE fecha >= %s
              AND fecha < %s
        ) AS abordajes_posteriores
    FROM eventos_12
    WHERE fecha >= %s
      AND fecha < %s
    GROUP BY tarjeta_operador
),
elegibles AS (
    SELECT a.*
    FROM actividad a
    JOIN disponibilidad_12 d
      ON d.tarjeta_operador = a.unidad
    WHERE a.abordajes_previos >= 2
      AND d.habilitada
)
SELECT
    COUNT(*) AS poblacion_elegible,
    COUNT(*) FILTER (
        WHERE abordajes_posteriores = 0
    ) AS positivos,
    COUNT(*) FILTER (
        WHERE abordajes_posteriores > 0
    ) AS negativos
FROM elegibles
"""

SQL_IDENTIDADES = """
WITH resumen AS (
    SELECT
        usuario_seudonimo,
        COUNT(*) AS identificadores,
        COUNT(DISTINCT sistema) AS sistemas
    FROM silver.silver_identidad_usuarios_seudonimizada
    GROUP BY usuario_seudonimo
)
SELECT
    COUNT(*) AS personas_aproximadas,
    SUM(identificadores) AS identificadores_originales,
    COUNT(*) FILTER (
        WHERE sistemas > 1
    ) AS personas_multisistema,
    SUM(identificadores) - COUNT(*) AS reduccion_unidades
FROM resumen
"""


def escribir_csv(ruta, columnas, filas):
    with ruta.open(
        "w", newline="", encoding="utf-8-sig"
    ) as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(columnas)
        escritor.writerows(filas)


def preparar_fechas(corte):
    inicio_previo = corte - timedelta(days=28)
    fin_posterior = corte + timedelta(days=30)

    return (
        inicio_previo,
        corte,
        corte,
        fin_posterior,
        inicio_previo,
        fin_posterior,
    )


def tasa_positiva(positivos, poblacion):
    if poblacion == 0:
        return 0.0

    return round(positivos * 100.0 / poblacion, 4)


def main():
    SALIDA.mkdir(parents=True, exist_ok=True)

    filas_resultado = []

    with psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5434"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
        options="-c timezone=UTC",
    ) as conn:

        with conn.cursor() as cur:
            print("\nPREPARANDO EVENTOS SILVER...")
            cur.execute(SQL_EVENTOS)

            cur.execute("""
                CREATE INDEX idx_eventos12_persona
                ON eventos_12 (usuario_seudonimo)
            """)

            cur.execute("""
                CREATE INDEX idx_eventos12_tarjeta
                ON eventos_12 (tarjeta_operador)
            """)

            cur.execute("""
                SELECT COUNT(*),
                       COUNT(*) FILTER (
                           WHERE usuario_seudonimo IS NULL
                       )
                FROM eventos_12
            """)

            total_eventos, sin_identidad = cur.fetchone()

            print(f"Eventos preparados: {total_eventos:,}")
            print(f"Eventos sin identidad: {sin_identidad:,}")

            if sin_identidad:
                raise RuntimeError(
                    "Existen eventos sin identidad. "
                    "No se calcularan etiquetas incompletas."
                )

            print("\nCOMPARACION GLOBAL DE IDENTIDADES")

            cur.execute(SQL_IDENTIDADES)
            identidad = cur.fetchone()

            nombres_identidad = [
                "personas_aproximadas",
                "identificadores_originales",
                "personas_multisistema",
                "reduccion_unidades",
            ]

            for nombre, valor in zip(
                nombres_identidad, identidad
            ):
                print(f"{nombre}: {valor:,}")

            escribir_csv(
                SALIDA / "comparacion_identidades.csv",
                nombres_identidad,
                [identidad],
            )

            for nombre_corte, fecha_corte in CORTES:
                print(
                    f"\nCORTE {nombre_corte}: {fecha_corte}"
                )

                cur.execute(
                    "DROP TABLE IF EXISTS "
                    "disponibilidad_persona_12"
                )
                cur.execute(
                    "DROP TABLE IF EXISTS "
                    "disponibilidad_12"
                )
                cur.execute(
                    "DROP TABLE IF EXISTS "
                    "ultimas_cdc_12"
                )

                cur.execute(
                    SQL_ULTIMAS_OPERACIONES,
                    (fecha_corte,),
                )

                cur.execute(SQL_DISPONIBILIDAD)
                cur.execute(SQL_DISPONIBILIDAD_PERSONA)

                parametros = preparar_fechas(
                    fecha_corte
                )

                for unidad, consulta in [
                    ("PERSONA_APROX", SQL_CONTEO_PERSONA),
                    ("TARJETA_OPERADOR", SQL_CONTEO_TARJETA),
                ]:
                    cur.execute(consulta, parametros)

                    poblacion, positivos, negativos = (
                        cur.fetchone()
                    )

                    tasa = tasa_positiva(
                        positivos, poblacion
                    )

                    filas_resultado.append([
                        nombre_corte,
                        str(fecha_corte),
                        unidad,
                        poblacion,
                        positivos,
                        negativos,
                        tasa,
                    ])

                    print(
                        f"  {unidad}: "
                        f"poblacion={poblacion:,}, "
                        f"positivos={positivos:,}, "
                        f"negativos={negativos:,}, "
                        f"tasa={tasa:.4f}%"
                    )

                    if positivos + negativos != poblacion:
                        raise RuntimeError(
                            "Error de reconciliacion "
                            "en las etiquetas."
                        )

    columnas = [
        "corte",
        "fecha_corte",
        "unidad",
        "poblacion_elegible",
        "positivos",
        "negativos",
        "tasa_positiva_pct",
    ]

    destino = SALIDA / "comparacion_unidades_cortes.csv"

    escribir_csv(
        destino,
        columnas,
        filas_resultado,
    )

    print("\nRESULTADO: COMPARACION COMPLETADA")
    print(f"Reporte: {destino}")
    print(
        "No se modificaron las tablas permanentes."
    )


if __name__ == "__main__":
    main()
