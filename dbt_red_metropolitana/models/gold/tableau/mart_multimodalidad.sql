{{ config(materialized='table') }}

select

    es_multimodal_aprox,

    cantidad_sistemas,

    sistemas_asociados,

    count(*)::bigint as cantidad_usuarios

from {{ ref('dim_usuario') }}

group by
    es_multimodal_aprox,
    cantidad_sistemas,
    sistemas_asociados