with transmetro as (

    select
        sistema_origen,
        identificador_registro,
        motivo_rechazo,
        raw_value,
        ingestion_timestamp,
        ingestion_date
    from {{ ref('cuarentena_transmetro') }}

),

transurbano as (

    select
        sistema_origen,
        identificador_registro,
        motivo_rechazo,
        raw_value,
        ingestion_timestamp,
        ingestion_date
    from {{ ref('cuarentena_transurbano') }}

),

metroriel as (

    select
        sistema_origen,
        identificador_registro,
        motivo_rechazo,
        raw_value,
        ingestion_timestamp,
        ingestion_date
    from {{ ref('cuarentena_metroriel') }}

)

select * from transmetro

union all

select * from transurbano

union all

select * from metroriel