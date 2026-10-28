with viajes as (

    select

        trip_id,

        usuario_fuente,

        entry_station::text as punto_origen_id,
        exit_station::text as punto_destino_id,

        entry_ts,
        exit_ts,

        fare_gtq as tarifa_gtq,
        duration_s as duracion_segundos,

        zona_origen_conformada,
        zona_destino_conformada

    from {{ ref('silver_metroriel_viajes') }}

),

con_identidad as (

    select

        v.*,

        i.usuario_seudonimo

    from viajes v

    left join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = 'MetroRiel'
       and i.llave_original = v.usuario_fuente

),

dimensionado as (

    select

        v.*,

        u.usuario_key,

        t.tiempo_key,

        m.modo_key,

        po.punto_servicio_key
            as punto_origen_key,

        pd.punto_servicio_key
            as punto_destino_key,

        po.zona_key
            as zona_origen_key,

        pd.zona_key
            as zona_destino_key

    from con_identidad v

    left join {{ ref('dim_usuario') }} u
        on u.usuario_seudonimo = v.usuario_seudonimo

    left join {{ ref('dim_tiempo') }} t
        on t.fecha = v.entry_ts::date
       and t.hora = extract(hour from v.entry_ts)::integer

    left join {{ ref('dim_modo_transporte') }} m
        on m.modo_transporte = 'MetroRiel'

    left join {{ ref('dim_punto_servicio') }} po
        on po.modo_transporte = 'MetroRiel'
       and po.punto_id = v.punto_origen_id

    left join {{ ref('dim_punto_servicio') }} pd
        on pd.modo_transporte = 'MetroRiel'
       and pd.punto_id = v.punto_destino_id

)

select

    row_number() over (
        order by trip_id
    )::bigint as viaje_key,

    modo_key,
    usuario_key,
    tiempo_key,

    punto_origen_key,
    punto_destino_key,

    zona_origen_key,
    zona_destino_key,

    trip_id as identificador_fuente,

    entry_ts as fecha_hora_entrada,
    exit_ts as fecha_hora_salida,

    tarifa_gtq,

    duracion_segundos,

    1::integer as cantidad_viajes

from dimensionado