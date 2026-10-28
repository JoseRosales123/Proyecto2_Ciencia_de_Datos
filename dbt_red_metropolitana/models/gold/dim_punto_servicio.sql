with puntos as (

    -- Transmetro
    select
        'Transmetro' as modo_transporte,
        estacion_id as punto_id,
        nombre as punto_nombre,
        linea as linea_ruta_eje,
        zona as zona_original

    from {{ source('staging', 'tm_estaciones') }}


    union all


    -- Transurbano
    select
        'Transurbano',
        cod_parada,
        descripcion,
        ruta,
        sector

    from {{ source('staging', 'tu_paradas') }}


    union all


    -- MetroRiel
    select
        'MetroRiel',
        id_estacion,
        nombre_estacion,
        null::text,
        zona_nombre

    from {{ source('staging', 'mr_estaciones') }}


    union all


    -- Aerometro
    select
        'Aerometro',
        station_code,
        station_name,
        axis,
        district

    from {{ source('staging', 'am_estaciones') }}

),

enriquecido as (

    select

        p.*,

        m.modo_key,

        z.zona_key,

        z.zona_nombre

    from puntos p

    left join {{ ref('dim_modo_transporte') }} m
        on m.modo_transporte = p.modo_transporte

    left join {{ ref('silver_zonas_conformadas') }} sz
        on sz.sistema = lower(p.modo_transporte)
       and sz.zona_original = p.zona_original

    left join {{ ref('dim_zona') }} z
        on z.zona_nombre = sz.zona_conformada

),

dimension as (

    select

        row_number() over (
            order by modo_key, punto_id
        )::integer as punto_servicio_key,

        modo_key,

        modo_transporte,

        punto_id,

        punto_nombre,

        linea_ruta_eje,

        zona_key,

        zona_nombre,

        zona_original

    from enriquecido

)

select *
from dimension