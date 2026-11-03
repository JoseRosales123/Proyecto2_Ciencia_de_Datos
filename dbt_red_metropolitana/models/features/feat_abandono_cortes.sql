
{{ config(
    materialized='table',
    schema='features',
    pre_hook="SET work_mem = '64MB'"
) }}

{# Fechas configurables de los cortes #}
{% set cortes = var(
    'feature_cortes',
    ['2026-07-01', '2026-07-31', '2026-08-29']
) %}

{# Limite temporal utilizado para auditoria de fuga #}
{% set limite = var(
    'feature_max_timestamp',
    '2026-08-30'
) %}

WITH cortes AS (

    {% for fecha in cortes %}
    SELECT
        '{{ ["A", "B", "C"][loop.index0] }}'::text
            AS corte,
        '{{ fecha }}'::date
            AS fecha_corte

    {% if not loop.last %}
    UNION ALL
    {% endif %}
    {% endfor %}

),

-- =====================================================
-- 1. OBTENER ULTIMA OPERACION CDC ANTES DE CADA CORTE
-- =====================================================

ultima_cdc AS (

    SELECT DISTINCT ON (c.corte, p.tarjeta)
        c.corte,
        p.tarjeta,
        UPPER(p.op) AS ultima_operacion

    FROM cortes c

    JOIN staging.cdc_padron_usuarios p
      ON p.commit_ts < c.fecha_corte

    ORDER BY
        c.corte,
        p.tarjeta,
        p.commit_ts DESC,
        p.seq DESC

),

-- =====================================================
-- 2. VERIFICAR DISPONIBILIDAD DE IDENTIFICADORES
-- =====================================================

estado_personas AS (

    SELECT
        c.corte,
        i.usuario_seudonimo,

        BOOL_OR(
            i.sistema <> 'Transmetro'
            OR u.ultima_operacion IS DISTINCT FROM 'DELETE'
        ) AS tiene_identificador_disponible

    FROM cortes c

    CROSS JOIN {{
        ref('silver_identidad_usuarios_seudonimizada')
    }} i

    LEFT JOIN ultima_cdc u
      ON u.corte = c.corte
     AND i.sistema = 'Transmetro'
     AND i.llave_original = u.tarjeta

    GROUP BY
        c.corte,
        i.usuario_seudonimo

),

-- =====================================================
-- 3. UNIFICAR EVENTOS DE LOS CUATRO SISTEMAS
-- =====================================================

eventos AS MATERIALIZED (

    -- TRANSMETRO
    SELECT
        i.usuario_seudonimo,
        'Transmetro'::text AS modo,
        t.fecha_hora_local AT TIME ZONE 'UTC' AS fecha,
        t.zona_conformada AS zona,
        t.tarifa_gtq::numeric AS gasto

    FROM {{ ref('silver_transmetro_validaciones') }} t

    JOIN {{ ref('silver_identidad_usuarios_seudonimizada') }} i
      ON i.sistema = 'Transmetro'
     AND i.llave_original = t.usuario_fuente

    UNION ALL

    -- TRANSURBANO
    SELECT
        i.usuario_seudonimo,
        'Transurbano'::text AS modo,
        t.fecha_hora_local AS fecha,
        t.zona_conformada AS zona,
        t.monto_gtq::numeric AS gasto

    FROM {{ ref('silver_transurbano_transacciones') }} t

    JOIN {{ ref('silver_identidad_usuarios_seudonimizada') }} i
      ON i.sistema = 'Transurbano'
     AND i.llave_original = t.usuario_fuente

    UNION ALL

    -- METRORIEL
    SELECT
        i.usuario_seudonimo,
        'MetroRiel'::text AS modo,
        t.entry_ts AS fecha,
        t.zona_origen_conformada AS zona,
        t.fare_gtq::numeric AS gasto

    FROM {{ ref('silver_metroriel_viajes') }} t

    JOIN {{ ref('silver_identidad_usuarios_seudonimizada') }} i
      ON i.sistema = 'MetroRiel'
     AND i.llave_original = t.usuario_fuente

    UNION ALL

    -- AEROMETRO
    SELECT
        i.usuario_seudonimo,
        'Aerometro'::text AS modo,
        t.fecha_hora_local AS fecha,
        t.zona_conformada AS zona,
        t.tarifa_gtq::numeric AS gasto

    FROM {{ ref('silver_aerometro_boardings') }} t

    JOIN {{ ref('silver_identidad_usuarios_seudonimizada') }} i
      ON i.sistema = 'Aerometro'
     AND i.llave_original = t.usuario_fuente

),

-- =====================================================
-- 4. FILTRAR UNICAMENTE LOS 28 DIAS ANTES DEL CORTE
-- =====================================================

eventos_previos AS MATERIALIZED (

    SELECT
        c.corte,
        c.fecha_corte,
        e.usuario_seudonimo,
        e.modo,
        e.fecha,
        e.zona,
        e.gasto

    FROM cortes c

    JOIN eventos e
      ON e.fecha >= c.fecha_corte - INTERVAL '28 days'
     AND e.fecha < c.fecha_corte
     AND e.fecha < '{{ limite }}'::timestamp

),

-- =====================================================
-- 5. CALCULAR CARACTERISTICAS POR PERSONA Y CORTE
-- =====================================================

agregados AS (

    SELECT
        corte,
        fecha_corte,
        usuario_seudonimo,

        COUNT(*)::integer
            AS eventos_ultimos_28_dias,

        COUNT(*) FILTER (
            WHERE fecha >= fecha_corte - INTERVAL '7 days'
        )::integer
            AS eventos_ultimos_7_dias,

        COUNT(DISTINCT modo)::integer
            AS cantidad_modos_distintos,

        (
            fecha_corte - MAX(fecha)::date
        )::integer
            AS dias_desde_ultimo_evento,

        AVG(
            CASE
                WHEN EXTRACT(HOUR FROM fecha) BETWEEN 5 AND 8
                  OR EXTRACT(HOUR FROM fecha) BETWEEN 16 AND 19
                THEN 1.0
                ELSE 0.0
            END
        )::numeric(10,4)
            AS proporcion_eventos_hora_pico,

        SUM(
            COALESCE(gasto, 0)
        )::numeric(14,2)
            AS gasto_acumulado_gtq,

        AVG(
            COALESCE(gasto, 0)
        )::numeric(14,2)
            AS gasto_promedio_evento_gtq,

        MAX(fecha)
            AS ultimo_evento_previo

    FROM eventos_previos

    GROUP BY
        corte,
        fecha_corte,
        usuario_seudonimo

    HAVING COUNT(*) >= 2

),

-- =====================================================
-- 6. IDENTIFICAR MODO DE TRANSPORTE MAS UTILIZADO
-- =====================================================

conteo_modos AS (

    SELECT
        corte,
        usuario_seudonimo,
        modo,
        COUNT(*) AS cantidad

    FROM eventos_previos

    GROUP BY
        corte,
        usuario_seudonimo,
        modo

),

modo_principal AS (

    SELECT DISTINCT ON (corte, usuario_seudonimo)
        corte,
        usuario_seudonimo,
        modo AS modo_mas_usado

    FROM conteo_modos

    ORDER BY
        corte,
        usuario_seudonimo,
        cantidad DESC,
        modo

),

-- =====================================================
-- 7. IDENTIFICAR ZONA DE ORIGEN MAS FRECUENTE
-- =====================================================

conteo_zonas AS (

    SELECT
        corte,
        usuario_seudonimo,
        zona,
        COUNT(*) AS cantidad

    FROM eventos_previos

    WHERE zona IS NOT NULL

    GROUP BY
        corte,
        usuario_seudonimo,
        zona

),

zona_principal AS (

    SELECT DISTINCT ON (corte, usuario_seudonimo)
        corte,
        usuario_seudonimo,
        zona AS zona_origen_mas_frecuente

    FROM conteo_zonas

    ORDER BY
        corte,
        usuario_seudonimo,
        cantidad DESC,
        zona

)

-- =====================================================
-- 8. RESULTADO FINAL CON FILTRO CDC
-- =====================================================

SELECT
    a.corte,
    a.fecha_corte,
    a.usuario_seudonimo,

    a.eventos_ultimos_7_dias,
    a.eventos_ultimos_28_dias,

    m.modo_mas_usado,

    a.cantidad_modos_distintos,
    a.dias_desde_ultimo_evento,
    a.proporcion_eventos_hora_pico,

    z.zona_origen_mas_frecuente,

    a.gasto_acumulado_gtq,
    a.gasto_promedio_evento_gtq,
    a.ultimo_evento_previo

FROM agregados a

-- Excluir personas sin identificadores disponibles
INNER JOIN estado_personas p
  ON p.corte = a.corte
 AND p.usuario_seudonimo = a.usuario_seudonimo
 AND p.tiene_identificador_disponible = TRUE

LEFT JOIN modo_principal m
  ON a.corte = m.corte
 AND a.usuario_seudonimo = m.usuario_seudonimo

LEFT JOIN zona_principal z
  ON a.corte = z.corte
 AND a.usuario_seudonimo = z.usuario_seudonimo
