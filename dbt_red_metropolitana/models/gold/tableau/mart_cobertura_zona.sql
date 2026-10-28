{{ config(materialized='table') }}

with cobertura as (

    select

        z.zona_key,
        z.zona_nombre,
        z.tipo_zona,
        z.tiene_servicio,

        count(distinct p.modo_key)
            as cantidad_modos,

        count(distinct p.punto_servicio_key)
            as cantidad_puntos_servicio,

        count(distinct case
            when m.modo_transporte = 'Transmetro'
            then p.punto_servicio_key
        end) as puntos_transmetro,

        count(distinct case
            when m.modo_transporte = 'Transurbano'
            then p.punto_servicio_key
        end) as puntos_transurbano,

        count(distinct case
            when m.modo_transporte = 'MetroRiel'
            then p.punto_servicio_key
        end) as puntos_metroriel,

        count(distinct case
            when m.modo_transporte = 'Aerometro'
            then p.punto_servicio_key
        end) as puntos_aerometro

    from {{ ref('dim_zona') }} z

    left join {{ ref('dim_punto_servicio') }} p
        on z.zona_key = p.zona_key

    left join {{ ref('dim_modo_transporte') }} m
        on p.modo_key = m.modo_key

    group by
        z.zona_key,
        z.zona_nombre,
        z.tipo_zona,
        z.tiene_servicio

)

select *
from cobertura