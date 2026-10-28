{{ config(materialized='ephemeral') }}

with base as (

    select

        cast(boarding_id as bigint) as boarding_id,

        user_hash,
        station_code,
        axis,

        cast(
            timestamp_utc as timestamptz
        ) as timestamp_utc,

        (
            cast(timestamp_utc as timestamptz)
            at time zone 'America/Guatemala'
        ) as fecha_hora_local,

        cast(cabin_number as integer) as cabin_number,

        cast(fare as numeric(10,2)) as tarifa_gtq,

        raw_value,
        ingestion_timestamp,
        ingestion_date,

        kafka_partition,
        kafka_offset

    from {{ source('staging', 'aerometro_boardings') }}

),

enriquecido as (

    select

        b.*,

        e.station_name,
        e.district as zona_original,

        z.zona_conformada

    from base b

    left join {{ source('staging', 'am_estaciones') }} e
        on b.station_code = e.station_code

    left join {{ ref('silver_zonas_conformadas') }} z
        on z.sistema = 'aerometro'
       and z.zona_original = e.district

)

select *
from enriquecido