with validacion as (

    select
        (
            select count(*)
            from {{ ref('fact_abordajes') }}
        ) as abordajes_gold,

        (
            select count(*)
            from {{ ref('silver_transmetro_validaciones') }}
        )
        +
        (
            select count(*)
            from {{ ref('silver_transurbano_transacciones') }}
        )
        +
        (
            select count(*)
            from {{ ref('silver_aerometro_boardings') }}
        ) as abordajes_silver,

        (
            select count(*)
            from {{ ref('fact_viajes_metroriel') }}
        ) as viajes_gold,

        (
            select count(*)
            from {{ ref('silver_metroriel_viajes') }}
        ) as viajes_silver

)

select *

from validacion

where abordajes_gold <> abordajes_silver
   or viajes_gold <> viajes_silver