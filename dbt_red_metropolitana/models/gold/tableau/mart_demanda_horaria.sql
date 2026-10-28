{{ config(materialized='table') }}

with abordajes as (

    select

        t.fecha,
        t.hora,
        t.dia_semana_nombre,
        t.es_dia_habil,
        t.es_hora_pico,

        m.modo_transporte,

        z.zona_nombre,
        z.tipo_zona,

        'ABORDAJE' as tipo_evento,

        sum(f.cantidad_abordajes)::bigint
            as cantidad_eventos

    from {{ ref('fact_abordajes') }} f

    inner join {{ ref('dim_tiempo') }} t
        on f.tiempo_key = t.tiempo_key

    inner join {{ ref('dim_modo_transporte') }} m
        on f.modo_key = m.modo_key

    inner join {{ ref('dim_zona') }} z
        on f.zona_key = z.zona_key

    group by
        t.fecha,
        t.hora,
        t.dia_semana_nombre,
        t.es_dia_habil,
        t.es_hora_pico,
        m.modo_transporte,
        z.zona_nombre,
        z.tipo_zona

),

metroriel as (

    select

        t.fecha,
        t.hora,
        t.dia_semana_nombre,
        t.es_dia_habil,
        t.es_hora_pico,

        'MetroRiel' as modo_transporte,

        z.zona_nombre,
        z.tipo_zona,

        'VIAJE_INICIADO' as tipo_evento,

        sum(f.cantidad_viajes)::bigint
            as cantidad_eventos

    from {{ ref('fact_viajes_metroriel') }} f

    inner join {{ ref('dim_tiempo') }} t
        on f.tiempo_key = t.tiempo_key

    inner join {{ ref('dim_zona') }} z
        on f.zona_origen_key = z.zona_key

    group by
        t.fecha,
        t.hora,
        t.dia_semana_nombre,
        t.es_dia_habil,
        t.es_hora_pico,
        z.zona_nombre,
        z.tipo_zona

)

select *
from abordajes

union all

select *
from metroriel