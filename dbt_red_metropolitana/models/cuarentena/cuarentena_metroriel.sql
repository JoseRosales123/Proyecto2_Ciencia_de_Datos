with clasificados as (

    select *
    from {{ ref('int_metroriel_calidad') }}

)

select

    'MetroRiel' as sistema_origen,

    trip_id::text as identificador_registro,

    'VIAJE_SIN_SALIDA' as motivo_rechazo,

    raw_value,

    ingestion_timestamp,
    ingestion_date,
    source_row_number

from clasificados

where regla_viaje_sin_salida