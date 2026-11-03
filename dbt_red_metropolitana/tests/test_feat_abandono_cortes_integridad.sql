
-- La prueba falla si devuelve una o mas filas.

WITH duplicados AS (

    SELECT
        corte,
        usuario_seudonimo

    FROM {{ ref('feat_abandono_cortes') }}

    GROUP BY
        corte,
        usuario_seudonimo

    HAVING COUNT(*) > 1

),

registros_invalidos AS (

    SELECT
        corte,
        usuario_seudonimo

    FROM {{ ref('feat_abandono_cortes') }}

    WHERE ultimo_evento_previo >= fecha_corte

       OR ultimo_evento_previo <
          fecha_corte - INTERVAL '28 days'

       OR eventos_ultimos_28_dias < 2

       OR eventos_ultimos_7_dias >
          eventos_ultimos_28_dias

       OR eventos_ultimos_7_dias < 0

       OR dias_desde_ultimo_evento < 1

       OR dias_desde_ultimo_evento > 28

)

SELECT
    'DUPLICADO' AS problema,
    corte,
    usuario_seudonimo
FROM duplicados

UNION ALL

SELECT
    'VALOR_INVALIDO' AS problema,
    corte,
    usuario_seudonimo
FROM registros_invalidos
