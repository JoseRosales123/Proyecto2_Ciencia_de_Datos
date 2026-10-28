from pathlib import Path
import os

import psycopg
from dotenv import load_dotenv


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]

load_dotenv(RAIZ_PROYECTO / ".env")


def conectar():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5434")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
    )


def preparar(cursor):

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS staging.padron_transmetro_vigente (
            tarjeta TEXT PRIMARY KEY,
            perfil TEXT,
            zona_residencia TEXT,
            estado TEXT NOT NULL,
            activo BOOLEAN NOT NULL,

            primera_seq BIGINT NOT NULL,
            ultima_seq BIGINT NOT NULL,
            ultima_operacion VARCHAR(10) NOT NULL,
            fecha_ultima_operacion TIMESTAMP NOT NULL,

            tiene_cuerpo BOOLEAN NOT NULL,
            cantidad_eventos INTEGER NOT NULL
        );
        """
    )

    # Staging es reconstruible.
    cursor.execute(
        """
        TRUNCATE TABLE staging.padron_transmetro_vigente;
        """
    )

    # Los eventos sin identidad siguen existiendo.
    cursor.execute(
        """
        CREATE OR REPLACE VIEW
        staging.cdc_identidad_no_resuelta AS

        SELECT *
        FROM staging.cdc_padron_usuarios
        WHERE tarjeta = 'SIN-TARJETA';
        """
    )


def aplicar():

    with conectar() as conexion:

        with conexion.cursor() as cursor:

            preparar(cursor)

            # --------------------------------------------------
            # Leer TODO el CDC en secuencia
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT
                    seq,
                    commit_ts,
                    op,
                    tarjeta,
                    perfil,
                    zona_residencia,
                    estado
                FROM staging.cdc_padron_usuarios
                ORDER BY seq;
                """
            )

            eventos = cursor.fetchall()

            total_eventos = len(eventos)
            procesados = 0
            no_resueltos = 0

            for (
                seq,
                commit_ts,
                op,
                tarjeta,
                perfil,
                zona,
                estado,
            ) in eventos:

                # No convertir SIN-TARJETA en una identidad real.
                if tarjeta == "SIN-TARJETA":
                    no_resueltos += 1
                    continue

                # ----------------------------------------------
                # INSERT / UPDATE
                # ----------------------------------------------

                if op in ("INSERT", "UPDATE"):

                    cursor.execute(
                        """
                        INSERT INTO staging.padron_transmetro_vigente (
                            tarjeta,
                            perfil,
                            zona_residencia,
                            estado,
                            activo,
                            primera_seq,
                            ultima_seq,
                            ultima_operacion,
                            fecha_ultima_operacion,
                            tiene_cuerpo,
                            cantidad_eventos
                        )
                        VALUES (
                            %s, %s, %s, %s,
                            TRUE,
                            %s, %s, %s, %s,
                            TRUE,
                            1
                        )

                        ON CONFLICT (tarjeta)
                        DO UPDATE SET

                            perfil =
                                EXCLUDED.perfil,

                            zona_residencia =
                                EXCLUDED.zona_residencia,

                            estado =
                                COALESCE(
                                    EXCLUDED.estado,
                                    'ACTIVA'
                                ),

                            activo = TRUE,

                            ultima_seq =
                                EXCLUDED.ultima_seq,

                            ultima_operacion =
                                EXCLUDED.ultima_operacion,

                            fecha_ultima_operacion =
                                EXCLUDED.fecha_ultima_operacion,

                            tiene_cuerpo = TRUE,

                            cantidad_eventos =
                                staging.padron_transmetro_vigente
                                .cantidad_eventos + 1;
                        """,
                        (
                            tarjeta,
                            perfil,
                            zona,
                            estado or "ACTIVA",
                            seq,
                            seq,
                            op,
                            commit_ts,
                        )
                    )

                # ----------------------------------------------
                # DELETE
                # ----------------------------------------------

                elif op == "DELETE":

                    cursor.execute(
                        """
                        INSERT INTO staging.padron_transmetro_vigente (
                            tarjeta,
                            perfil,
                            zona_residencia,
                            estado,
                            activo,
                            primera_seq,
                            ultima_seq,
                            ultima_operacion,
                            fecha_ultima_operacion,
                            tiene_cuerpo,
                            cantidad_eventos
                        )
                        VALUES (
                            %s,
                            NULL,
                            NULL,
                            'INACTIVA',
                            FALSE,
                            %s,
                            %s,
                            'DELETE',
                            %s,
                            FALSE,
                            1
                        )

                        ON CONFLICT (tarjeta)
                        DO UPDATE SET

                            estado = 'INACTIVA',

                            activo = FALSE,

                            ultima_seq =
                                EXCLUDED.ultima_seq,

                            ultima_operacion =
                                'DELETE',

                            fecha_ultima_operacion =
                                EXCLUDED.fecha_ultima_operacion,

                            cantidad_eventos =
                                staging.padron_transmetro_vigente
                                .cantidad_eventos + 1;
                        """,
                        (
                            tarjeta,
                            seq,
                            seq,
                            commit_ts,
                        )
                    )

                else:
                    raise ValueError(
                        f"Operación CDC desconocida: {op}"
                    )

                procesados += 1

            # --------------------------------------------------
            # Métricas finales
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_tarjetas,

                    COUNT(*) FILTER (
                        WHERE activo = TRUE
                    ) AS activas,

                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                    ) AS inactivas,

                    COUNT(*) FILTER (
                        WHERE tiene_cuerpo = TRUE
                    ) AS con_cuerpo,

                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                          AND tiene_cuerpo = FALSE
                    ) AS tombstone_sin_cuerpo,

                    COUNT(*) FILTER (
                        WHERE activo = FALSE
                          AND tiene_cuerpo = TRUE
                    ) AS bajas_con_historial

                FROM staging.padron_transmetro_vigente;
                """
            )

            (
                total_tarjetas,
                activas,
                inactivas,
                con_cuerpo,
                tombstone_sin_cuerpo,
                bajas_con_historial,
            ) = cursor.fetchone()

            # --------------------------------------------------
            # Detectar mezcla de formatos
            # --------------------------------------------------

            cursor.execute(
                """
                SELECT
                    CASE
                        WHEN tarjeta LIKE 'TC-%'
                            THEN 'FORMATO_TM'

                        WHEN tarjeta LIKE 'MR%'
                            THEN 'FORMATO_MR'

                        WHEN tarjeta ~ '^[0-9]{10}$'
                            THEN 'FORMATO_TU'

                        ELSE 'OTRO'
                    END AS formato,

                    COUNT(*)

                FROM staging.padron_transmetro_vigente

                GROUP BY 1
                ORDER BY 1;
                """
            )

            formatos = cursor.fetchall()

    # ------------------------------------------------------
    # Resultado
    # ------------------------------------------------------

    print("=" * 85)
    print("APLICACION SECUENCIAL DEL CDC - PADRON VIGENTE")
    print("=" * 85)

    print(f"Eventos CDC totales:             {total_eventos:,}")
    print(f"Eventos procesados con llave:    {procesados:,}")
    print(f"Eventos SIN-TARJETA preservados: {no_resueltos:,}")

    print("-" * 85)

    print(f"Tarjetas distintas en padron:    {total_tarjetas:,}")
    print(f"Tarjetas ACTIVAS:                {activas:,}")
    print(f"Tarjetas INACTIVAS:              {inactivas:,}")

    print("-" * 85)

    print(f"Tarjetas con cuerpo conocido:    {con_cuerpo:,}")
    print(f"Bajas con historial previo:      {bajas_con_historial:,}")
    print(f"Tombstones sin cuerpo previo:    {tombstone_sin_cuerpo:,}")

    print("-" * 85)

    print("FORMATOS DE LLAVE ENCONTRADOS:")

    for formato, cantidad in formatos:
        print(f"  {formato:<15} {cantidad:>8,}")

    print("-" * 85)

    if activas + inactivas == total_tarjetas:
        print("Conteo del padron consistente: SI")
        print("RESULTADO: CDC APLICADO CORRECTAMENTE")
    else:
        print("Conteo del padron consistente: NO")
        print("RESULTADO: REVISAR CDC")

    print("=" * 85)


if __name__ == "__main__":
    aplicar()