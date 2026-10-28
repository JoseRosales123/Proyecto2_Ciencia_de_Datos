select

    boarding_id,

    'Aerometro' as modo_transporte,

    user_hash as usuario_fuente,

    station_code,
    station_name,
    axis,

    timestamp_utc,
    fecha_hora_local,

    cabin_number,
    tarifa_gtq,

    zona_original,
    zona_conformada,

    raw_value,
    ingestion_timestamp,
    ingestion_date,

    kafka_partition,
    kafka_offset

from {{ ref('int_aerometro_normalizado') }}