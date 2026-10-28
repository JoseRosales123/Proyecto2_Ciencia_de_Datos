with clasificados as (

    select *
    from {{ ref('int_transmetro_calidad') }}

)

select

    validacion_id,

    'Transmetro' as modo_transporte,

    tarjeta as usuario_fuente,

    estacion_id,
    linea,

    fecha_hora_local,

    tarifa_gtq,

    tipo,

    zona_original,
    zona_conformada,

    raw_value,
    ingestion_timestamp,
    ingestion_date,

    kafka_partition,
    kafka_offset

from clasificados

where numero_repeticion = 1