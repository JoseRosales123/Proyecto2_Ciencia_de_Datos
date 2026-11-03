"""Fase 1.4: exportar etiquetas individuales y features del corte A.

Reutiliza las consultas oficiales del apartado 1.2 sin modificar su archivo.
Solo crea tablas temporales en la sesión y un CSV local.
Ejecutar desde la raíz del Proyecto 2:
    python scripts/modelado/exportar_dataset_corte_a.py
"""

import os
import sys
from datetime import date
from pathlib import Path

import psycopg
from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
load_dotenv(RAIZ / ".env")

from scripts.etiquetado.calcular_etiquetas import (  # noqa: E402
    SQL_DISPONIBILIDAD,
    SQL_DISPONIBILIDAD_PERSONA,
    SQL_EVENTOS,
    SQL_ULTIMAS_OPERACIONES,
    preparar_fechas,
)

CORTE = date(2026, 7, 1)
SALIDA = RAIZ / "datos_modelado_local" / "fase1_4" / "dataset_corte_A.csv"

SQL_ETIQUETAS = """
CREATE TEMP TABLE etiquetas_14 AS
WITH actividad AS (
    SELECT
        usuario_seudonimo AS usuario_seudonimo,
        COUNT(*) FILTER (WHERE fecha >= %s AND fecha < %s) AS abordajes_previos,
        COUNT(*) FILTER (WHERE fecha >= %s AND fecha < %s) AS abordajes_posteriores
    FROM eventos_12
    WHERE usuario_seudonimo IS NOT NULL
      AND fecha >= %s AND fecha < %s
    GROUP BY usuario_seudonimo
)
SELECT
    a.usuario_seudonimo,
    CASE WHEN a.abordajes_posteriores = 0 THEN 1 ELSE 0 END::integer AS abandono
FROM actividad a
JOIN disponibilidad_persona_12 d
  ON d.usuario_seudonimo = a.usuario_seudonimo
WHERE a.abordajes_previos >= 2
  AND d.habilitada
"""

SQL_AUDITORIA = """
WITH features_a AS (
    SELECT usuario_seudonimo
    FROM features.feat_abandono_cortes
    WHERE corte = 'A' AND fecha_corte = DATE '2026-07-01'
)
SELECT
    (SELECT COUNT(*) FROM etiquetas_14) AS filas_etiquetas,
    (SELECT COUNT(*) FROM etiquetas_14 WHERE abandono = 1) AS positivos,
    (SELECT COUNT(*) FROM etiquetas_14 WHERE abandono = 0) AS negativos,
    (SELECT COUNT(*) FROM features_a) AS filas_features,
    (SELECT COUNT(*) FROM etiquetas_14 e LEFT JOIN features_a f USING (usuario_seudonimo)
      WHERE f.usuario_seudonimo IS NULL) AS etiquetas_sin_features,
    (SELECT COUNT(*) FROM features_a f LEFT JOIN etiquetas_14 e USING (usuario_seudonimo)
      WHERE e.usuario_seudonimo IS NULL) AS features_sin_etiqueta
"""

SQL_EXPORT = """
COPY (
    SELECT
        f.usuario_seudonimo,
        f.eventos_ultimos_7_dias,
        f.eventos_ultimos_28_dias,
        f.modo_mas_usado,
        f.cantidad_modos_distintos,
        f.dias_desde_ultimo_evento,
        f.proporcion_eventos_hora_pico,
        f.zona_origen_mas_frecuente,
        f.gasto_acumulado_gtq,
        f.gasto_promedio_evento_gtq,
        e.abandono
    FROM features.feat_abandono_cortes f
    JOIN etiquetas_14 e USING (usuario_seudonimo)
    WHERE f.corte = 'A' AND f.fecha_corte = DATE '2026-07-01'
    ORDER BY f.usuario_seudonimo
) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)
"""


def main():
    print("PREPARANDO ETIQUETAS INDIVIDUALES — CORTE A (2026-07-01)")
    with psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5434"),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
        options="-c timezone=UTC",
    ) as conn:
        with conn.cursor() as cur:
            print("1. Unificando eventos Silver (misma lógica de 1.2)...")
            cur.execute(SQL_EVENTOS)
            cur.execute(
                "CREATE INDEX idx_eventos14_persona_fecha "
                "ON eventos_12 (usuario_seudonimo, fecha)"
            )
            cur.execute("ANALYZE eventos_12")

            cur.execute(
                "SELECT COUNT(*) FROM eventos_12 WHERE usuario_seudonimo IS NULL"
            )
            sin_identidad = cur.fetchone()[0]
            if sin_identidad:
                raise RuntimeError(
                    f"Hay {sin_identidad} eventos sin identidad seudonimizada."
                )

            print("2. Recuperando el estado CDC anterior al corte A...")
            cur.execute(SQL_ULTIMAS_OPERACIONES, (CORTE,))
            cur.execute(SQL_DISPONIBILIDAD)
            cur.execute(SQL_DISPONIBILIDAD_PERSONA)

            print("3. Etiquetando a cada persona elegible...")
            cur.execute(SQL_ETIQUETAS, preparar_fechas(CORTE))
            cur.execute(
                "CREATE UNIQUE INDEX idx_etiquetas14_usuario "
                "ON etiquetas_14 (usuario_seudonimo)"
            )
            cur.execute("ANALYZE etiquetas_14")

            print("4. Conciliando etiquetas con las features de 1.3...")
            cur.execute(SQL_AUDITORIA)
            columnas = [d.name for d in cur.description]
            auditoria = dict(zip(columnas, cur.fetchone()))
            for campo, valor in auditoria.items():
                print(f"  {campo}: {valor:,}")

            valores_esperados = {
                "filas_etiquetas": 60664,
                "positivos": 8110,
                "negativos": 52554,
                "filas_features": 60664,
                "etiquetas_sin_features": 0,
                "features_sin_etiqueta": 0,
            }
            diferencias = {
                k: (auditoria[k], esperado)
                for k, esperado in valores_esperados.items()
                if auditoria[k] != esperado
            }
            if diferencias:
                raise RuntimeError(
                    "Conciliación fallida; no se exporta el dataset. "
                    f"Diferencias (observado, esperado): {diferencias}"
                )

            SALIDA.parent.mkdir(parents=True, exist_ok=True)
            print("5. Exportando CSV local...")
            with SALIDA.open("wb") as archivo:
                with cur.copy(SQL_EXPORT) as copia:
                    for bloque in copia:
                        archivo.write(bloque)

    print("RESULTADO: OK — 60,664 filas; 8,110 positivos; 52,554 negativos")
    print(f"Dataset: {SALIDA}")
    print("No se modificaron tablas permanentes de PostgreSQL.")
    print("Nota: el CSV contiene seudónimos; no lo publiques en GitHub.")


if __name__ == "__main__":
    main()
