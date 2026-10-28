with clasificados as (

    select *
    from {{ ref('int_metroriel_calidad') }}

)

select

    trip_id,

    'MetroRiel' as modo_transporte,

    card as usuario_fuente,

    entry_station,
    estacion_origen_nombre,
    zona_origen_original,
    zona_origen_conformada,

    exit_station,
    estacion_destino_nombre,
    zona_destino_original,
    zona_destino_conformada,

    entry_ts,
    exit_ts,

    fare_gtq,
    duration_s,

    raw_value,
    ingestion_timestamp,
    ingestion_date,
    source_row_number

from clasificados

where not regla_viaje_sin_salida