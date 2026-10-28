with base as (

    select

        usuario_seudonimo,

        count(distinct sistema) as cantidad_sistemas,

        string_agg(
            distinct sistema,
            ', '
            order by sistema
        ) as sistemas_asociados,

        max(estrategia_identidad) as estrategia_identidad

    from {{ ref('silver_identidad_usuarios_seudonimizada') }}

    group by usuario_seudonimo

),

dimension as (

    select

        row_number() over (
            order by usuario_seudonimo
        )::bigint as usuario_key,

        usuario_seudonimo,

        cantidad_sistemas,

        sistemas_asociados,

        (
            cantidad_sistemas > 1
        ) as es_multimodal_aprox,

        estrategia_identidad

    from base

)

select *
from dimension