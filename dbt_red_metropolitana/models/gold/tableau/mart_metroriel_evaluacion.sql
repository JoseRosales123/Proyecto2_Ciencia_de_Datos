{{ config(materialized='table') }}

with demanda_otros_modos as (

    select

        z.zona_nombre,

        sum(f.cantidad_abordajes)::bigint
            as demanda_otros_modos

    from {{ ref('fact_abordajes') }} f

    inner join {{ ref('dim_zona') }} z
        on f.zona_key = z.zona_key

    group by z.zona_nombre

),

demanda_metroriel as (

    select

        z.zona_nombre,

        sum(f.cantidad_viajes)::bigint
            as viajes_metroriel

    from {{ ref('fact_viajes_metroriel') }} f

    inner join {{ ref('dim_zona') }} z
        on f.zona_origen_key = z.zona_key

    group by z.zona_nombre

),

resultado as (

    select

        z.zona_nombre,

        case
            when z.zona_nombre in (
                'Zona 12',
                'Zona 8',
                'Zona 1',
                'Zona 6',
                'Zona 17'
            )
            then true
            else false
        end as esta_en_trazado_metroriel,

        coalesce(o.demanda_otros_modos, 0)
            as demanda_otros_modos,

        coalesce(m.viajes_metroriel, 0)
            as viajes_metroriel,

        coalesce(o.demanda_otros_modos, 0)
        + coalesce(m.viajes_metroriel, 0)
            as demanda_observada_total

    from {{ ref('dim_zona') }} z

    left join demanda_otros_modos o
        on z.zona_nombre = o.zona_nombre

    left join demanda_metroriel m
        on z.zona_nombre = m.zona_nombre

)

select *
from resultado