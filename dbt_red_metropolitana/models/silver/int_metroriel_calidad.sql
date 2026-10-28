{{ config(materialized='ephemeral') }}

with base as (

    select

        cast(trip_id as bigint) as trip_id,

        card,

        cast(entry_station as integer) as entry_station,

        cast(
            entry_ts as timestamp
        ) as entry_ts,

        cast(
            exit_station as integer
        ) as exit_station,

        cast(
            exit_ts as timestamp
        ) as exit_ts,

        cast(
            fare_gtq as numeric(10,2)
        ) as fare_gtq,

        cast(
            duration_s as integer
        ) as duration_s,

        raw_value,
        ingestion_timestamp,
        ingestion_date,
        source_row_number,

        (
            exit_station is null
            or exit_ts is null
            or duration_s is null
        ) as regla_viaje_sin_salida

    from {{ source('staging', 'metroriel_viajes') }}

),

enriquecido as (

    select

        b.*,

        eo.nombre_estacion as estacion_origen_nombre,
        eo.zona_nombre as zona_origen_original,

        ed.nombre_estacion as estacion_destino_nombre,
        ed.zona_nombre as zona_destino_original,

        zo.zona_conformada as zona_origen_conformada,
        zd.zona_conformada as zona_destino_conformada

    from base b

    left join {{ source('staging', 'mr_estaciones') }} eo
        on b.entry_station = cast(eo.id_estacion as integer)

    left join {{ source('staging', 'mr_estaciones') }} ed
        on b.exit_station = cast(ed.id_estacion as integer)

    left join {{ ref('silver_zonas_conformadas') }} zo
        on zo.sistema = 'metroriel'
       and zo.zona_original = eo.zona_nombre

    left join {{ ref('silver_zonas_conformadas') }} zd
        on zd.sistema = 'metroriel'
       and zd.zona_original = ed.zona_nombre

)

select *
from enriquecido