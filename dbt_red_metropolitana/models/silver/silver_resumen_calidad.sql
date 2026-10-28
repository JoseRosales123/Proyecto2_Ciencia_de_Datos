with metricas as (

    select
        'Transmetro' as sistema,
        'DUPLICADO_TORNIQUETE' as regla,
        count(*) as registros_regla,
        (
            select count(*)
            from {{ source('staging', 'transmetro_validaciones') }}
        ) as total_fuente

    from {{ ref('cuarentena_transmetro') }}

    union all

    select
        'Transurbano',
        'COD_PARADA_NULO',
        count(*) filter (
            where regla_cod_parada_nulo
        ),
        (
            select count(*)
            from {{ source('staging', 'transurbano_transacciones') }}
        )

    from {{ ref('cuarentena_transurbano') }}

    union all

    select
        'Transurbano',
        'FECHA_FUTURA',
        count(*) filter (
            where regla_fecha_futura
        ),
        (
            select count(*)
            from {{ source('staging', 'transurbano_transacciones') }}
        )

    from {{ ref('cuarentena_transurbano') }}

    union all

    select
        'MetroRiel',
        'VIAJE_SIN_SALIDA',
        count(*),
        (
            select count(*)
            from {{ source('staging', 'metroriel_viajes') }}
        )

    from {{ ref('cuarentena_metroriel') }}

)

select

    sistema,
    regla,
    registros_regla,
    total_fuente,

    round(
        registros_regla::numeric
        / nullif(total_fuente, 0)
        * 100,
        4
    ) as porcentaje_fuente

from metricas