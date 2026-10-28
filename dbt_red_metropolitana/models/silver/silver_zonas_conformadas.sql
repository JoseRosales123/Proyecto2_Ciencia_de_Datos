with zonas_crudas as (

    -- Transmetro
    select
        'transmetro' as sistema,
        zona as zona_original
    from {{ source('staging', 'tm_estaciones') }}

    union all

    -- Transurbano
    select
        'transurbano' as sistema,
        sector as zona_original
    from {{ source('staging', 'tu_paradas') }}

    union all

    -- MetroRiel
    select
        'metroriel' as sistema,
        zona_nombre as zona_original
    from {{ source('staging', 'mr_estaciones') }}

    union all

    -- Aerometro
    select
        'aerometro' as sistema,
        district as zona_original
    from {{ source('staging', 'am_estaciones') }}

),

normalizadas as (

    select
        sistema,
        zona_original,

        case

            -- Formato de Transurbano: Z10, Z1, etc.
            when upper(zona_original) ~ '^Z[0-9]+$'
                then 'Zona ' ||
                     substring(
                         upper(zona_original)
                         from 2
                     )

            -- Zonas que ya llegan como "Zona N"
            when upper(zona_original) ~ '^ZONA [0-9]+$'
                then 'Zona ' ||
                     substring(
                         zona_original
                         from '[0-9]+'
                     )

            -- Municipios / sectores
            when upper(zona_original) = 'MIXCO'
                then 'Mixco'

            when upper(zona_original) = 'VILLA NUEVA'
                then 'Villa Nueva'

            when upper(zona_original) = 'SAN MIGUEL PETAPA'
                then 'San Miguel Petapa'

            when upper(zona_original) = 'SANTA CATARINA PINULA'
                then 'Santa Catarina Pinula'

            else trim(zona_original)

        end as zona_conformada

    from zonas_crudas

)

select distinct

    sistema,
    zona_original,
    zona_conformada

from normalizadas