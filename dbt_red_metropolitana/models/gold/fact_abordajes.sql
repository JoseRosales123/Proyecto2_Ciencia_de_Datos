with abordajes as (

    -- =====================================================
    -- TRANSMETRO
    -- =====================================================

    select

        'Transmetro' as modo_transporte,

        validacion_id::text as identificador_fuente,

        usuario_fuente,

        estacion_id as punto_id,

        fecha_hora_local,

        tarifa_gtq,

        linea as linea_ruta_eje,

        zona_conformada

    from {{ ref('silver_transmetro_validaciones') }}


    union all


    -- =====================================================
    -- TRANSURBANO
    -- =====================================================

    select

        'Transurbano' as modo_transporte,

        source_row_number::text as identificador_fuente,

        usuario_fuente,

        cod_parada as punto_id,

        fecha_hora_local,

        monto_gtq as tarifa_gtq,

        ruta as linea_ruta_eje,

        zona_conformada

    from {{ ref('silver_transurbano_transacciones') }}


    union all


    -- =====================================================
    -- AEROMETRO
    -- =====================================================

    select

        'Aerometro' as modo_transporte,

        boarding_id::text as identificador_fuente,

        usuario_fuente,

        station_code as punto_id,

        fecha_hora_local,

        tarifa_gtq,

        axis as linea_ruta_eje,

        zona_conformada

    from {{ ref('silver_aerometro_boardings') }}

),

con_identidad as (

    select

        a.*,

        i.usuario_seudonimo

    from abordajes a

    left join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = a.modo_transporte
       and i.llave_original = a.usuario_fuente

),

dimensionado as (

    select

        a.*,

        u.usuario_key,

        t.tiempo_key,

        m.modo_key,

        p.punto_servicio_key,

        z.zona_key

    from con_identidad a

    left join {{ ref('dim_usuario') }} u
        on u.usuario_seudonimo = a.usuario_seudonimo

    left join {{ ref('dim_tiempo') }} t
        on t.fecha = a.fecha_hora_local::date
       and t.hora = extract(hour from a.fecha_hora_local)::integer

    left join {{ ref('dim_modo_transporte') }} m
        on m.modo_transporte = a.modo_transporte

    left join {{ ref('dim_punto_servicio') }} p
        on p.modo_transporte = a.modo_transporte
       and p.punto_id = a.punto_id

    left join {{ ref('dim_zona') }} z
        on z.zona_nombre = a.zona_conformada

)

select

    row_number() over (
        order by
            modo_transporte,
            identificador_fuente
    )::bigint as abordaje_key,

    modo_key,
    usuario_key,
    tiempo_key,
    zona_key,
    punto_servicio_key,

    identificador_fuente,

    fecha_hora_local,

    linea_ruta_eje,

    tarifa_gtq,

    1::integer as cantidad_abordajes

from dimensionado