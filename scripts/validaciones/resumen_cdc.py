from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ_PROYECTO / ".env")


def conectar():
    return psycopg.connect(
        host="localhost",
        port=5433,
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def main():

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            # -------------------------------------------------
            # Total de eventos por operación
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE op = 'INSERT'
                    ),
                    COUNT(*) FILTER (
                        WHERE op = 'UPDATE'
                    ),
                    COUNT(*) FILTER (
                        WHERE op = 'DELETE'
                    ),
                    COUNT(*) FILTER (
                        WHERE tarjeta = 'SIN-TARJETA'
                    )
                FROM staging.cdc_padron_usuarios;
                """
            )

            (
                inserts,
                updates,
                deletes,
                sin_tarjeta,
            ) = cursor.fetchone()

            # -------------------------------------------------
            # Antes de aplicar bajas:
            # tarjetas con al menos un INSERT o UPDATE
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(DISTINCT tarjeta)

                FROM staging.cdc_padron_usuarios

                WHERE tarjeta <> 'SIN-TARJETA'
                  AND op IN ('INSERT', 'UPDATE');
                """
            )

            antes_bajas = cursor.fetchone()[0]

            # -------------------------------------------------
            # Estado final del padrón
            # -------------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE activo = TRUE
                    ) AS activas,
                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                    ) AS inactivas,
                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                          AND tiene_cuerpo = TRUE
                    ) AS bajas_con_historial,
                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                          AND tiene_cuerpo = FALSE
                    ) AS tombstones
                FROM staging.padron_transmetro_vigente;
                """
            )

            (
                total_padron,
                activas,
                inactivas,
                bajas_con_historial,
                tombstones,
            ) = cursor.fetchone()

    print("=" * 85)
    print("RESUMEN FORMAL DEL CDC - PADRON DE USUARIOS")
    print("=" * 85)

    print("EVENTOS RECIBIDOS")
    print("-" * 85)

    print(f"INSERT:       {inserts:>10,}")
    print(f"UPDATE:       {updates:>10,}")
    print(f"DELETE:       {deletes:>10,}")
    print(f"SIN-TARJETA:  {sin_tarjeta:>10,}")

    print("\n" + "=" * 85)
    print("CONTEO ANTES / DESPUES DE APLICAR BAJAS")
    print("=" * 85)

    print(
        f"Tarjetas conocidas antes de aplicar DELETE: "
        f"{antes_bajas:,}"
    )

    print("-" * 85)

    print(
        f"Tarjetas ACTIVAS despues del CDC:           "
        f"{activas:,}"
    )

    print(
        f"Tarjetas INACTIVAS despues del CDC:         "
        f"{inactivas:,}"
    )

    print(
        f"Total de llaves conservadas en el padron:   "
        f"{total_padron:,}"
    )

    print("-" * 85)

    print(
        f"Bajas con historial previo:                 "
        f"{bajas_con_historial:,}"
    )

    print(
        f"Tombstones sin cuerpo previo:               "
        f"{tombstones:,}"
    )

    print("-" * 85)

    diferencia = antes_bajas - activas

    print(
        f"Reduccion de tarjetas activas conocidas:    "
        f"{diferencia:,}"
    )

    consistente = (
        activas + inactivas == total_padron
        and diferencia == bajas_con_historial
    )

    print(
        f"Conteos consistentes: "
        f"{'SI' if consistente else 'NO'}"
    )

    if consistente:
        print(
            "RESULTADO: MODELO CDC VALIDADO CORRECTAMENTE"
        )
    else:
        print(
            "RESULTADO: REVISAR CONTEOS DEL CDC"
        )

    print("=" * 85)


if __name__ == "__main__":
    main()