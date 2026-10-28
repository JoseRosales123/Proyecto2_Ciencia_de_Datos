with clasificados as (

    select *
    from {{ ref('int_transurbano_calidad') }}

)

select

    'Transurbano' as sistema_origen,

    source_row_number::text as identificador_registro,

    motivo_rechazo,

    regla_cod_parada_nulo,
    regla_fecha_futura,

    raw_value,

    ingestion_timestamp,
    ingestion_date

from clasificados

where regla_cod_parada_nulo
   or regla_fecha_futura