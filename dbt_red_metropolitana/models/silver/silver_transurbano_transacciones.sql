with clasificados as (

    select *
    from {{ ref('int_transurbano_calidad') }}

)

select

    source_row_number,

    'Transurbano' as modo_transporte,

    num_tarjeta as usuario_fuente,

    cod_parada,
    ruta,

    fecha_hora_local,

    monto_gtq,
    cod_estado,

    zona_original,
    zona_conformada,

    raw_value,
    ingestion_timestamp,
    ingestion_date

from clasificados

where not regla_cod_parada_nulo
  and not regla_fecha_futura