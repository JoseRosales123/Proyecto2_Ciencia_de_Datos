with clasificados as (

    select *
    from {{ ref('int_transmetro_calidad') }}

)

select

    'Transmetro' as sistema_origen,

    validacion_id::text as identificador_registro,

    'DUPLICADO_TORNIQUETE' as motivo_rechazo,

    raw_value,

    ingestion_timestamp,
    ingestion_date,

    kafka_partition,
    kafka_offset

from clasificados

where numero_repeticion > 1