{{ config(materialized='ephemeral') }}

with base as (

    select

        source_row_number,

        fecha,
        hora,
        num_tarjeta,
        nullif(trim(cod_parada), '') as cod_parada,
        ruta,

        (
            cast(monto_centavos as numeric)
            / 100
        )::numeric(10,2) as monto_gtq,

        cast(cod_estado as integer) as cod_estado,

        to_timestamp(
            fecha || ' ' || hora,
            'DD/MM/YYYY HH24:MI:SS'
        )::timestamp as fecha_hora_local,

        to_date(
            fecha,
            'DD/MM/YYYY'
        ) as fecha_operacion,

        raw_value,
        ingestion_timestamp,
        ingestion_date,

        (
            nullif(trim(cod_parada), '') is null
        ) as regla_cod_parada_nulo,

        (
            to_date(fecha, 'DD/MM/YYYY')
            > ingestion_date
        ) as regla_fecha_futura

    from {{ source('staging', 'transurbano_transacciones') }}

),

enriquecido as (

    select

        b.*,

        p.sector as zona_original,

        z.zona_conformada,

        nullif(
            concat_ws(
                ' | ',

                case
                    when b.regla_cod_parada_nulo
                    then 'COD_PARADA_NULO'
                end,

                case
                    when b.regla_fecha_futura
                    then 'FECHA_FUTURA'
                end
            ),
            ''
        ) as motivo_rechazo

    from base b

    left join {{ source('staging', 'tu_paradas') }} p
        on b.cod_parada = p.cod_parada

    left join {{ ref('silver_zonas_conformadas') }} z
        on z.sistema = 'transurbano'
       and z.zona_original = p.sector

)

select *
from enriquecido