{{ config(materialized='ephemeral') }}

with base as (

    select
        cast(validation_id as bigint) as validacion_id,
        tarjeta,
        estacion_id,
        linea,

        to_timestamp(
            fecha_hora,
            'YYYY-MM-DD HH24:MI:SS'
        ) as fecha_hora_local,

        cast(tarifa as numeric(10,2)) as tarifa_gtq,

        tipo,

        raw_value,
        ingestion_timestamp,
        ingestion_date,
        kafka_partition,
        kafka_offset,

        row_number() over (
            partition by validation_id
            order by kafka_partition, kafka_offset
        ) as numero_repeticion

    from {{ source('staging', 'transmetro_validaciones') }}

),

enriquecido as (

    select
        b.*,

        e.zona as zona_original,

        z.zona_conformada

    from base b

    left join {{ source('staging', 'tm_estaciones') }} e
        on b.estacion_id = e.estacion_id

    left join {{ ref('silver_zonas_conformadas') }} z
        on z.sistema = 'transmetro'
       and z.zona_original = e.zona

)

select *
from enriquecido