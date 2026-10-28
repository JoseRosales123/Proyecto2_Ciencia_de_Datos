{{ config(materialized='table') }}

with eventos as (

    -- =====================================================
    -- TRANSMETRO
    -- =====================================================

    select

        i.usuario_seudonimo,
        'Transmetro' as modo_transporte,

        t.fecha_hora_local
            as fecha_hora,

        t.zona_conformada
            as zona_origen,

        t.tarifa_gtq::numeric
            as gasto_gtq

    from {{ ref('silver_transmetro_validaciones') }} t

    inner join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = 'Transmetro'
       and i.llave_original = t.usuario_fuente


    union all


    -- =====================================================
    -- TRANSURBANO
    -- =====================================================

    select

        i.usuario_seudonimo,
        'Transurbano' as modo_transporte,

        t.fecha_hora_local
            as fecha_hora,

        t.zona_conformada
            as zona_origen,

        t.monto_gtq::numeric
            as gasto_gtq

    from {{ ref('silver_transurbano_transacciones') }} t

    inner join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = 'Transurbano'
       and i.llave_original = t.usuario_fuente


    union all


    -- =====================================================
    -- METRORIEL
    -- =====================================================

    select

        i.usuario_seudonimo,
        'MetroRiel' as modo_transporte,

        t.entry_ts
            as fecha_hora,

        t.zona_origen_conformada
            as zona_origen,

        t.fare_gtq::numeric
            as gasto_gtq

    from {{ ref('silver_metroriel_viajes') }} t

    inner join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = 'MetroRiel'
       and i.llave_original = t.usuario_fuente


    union all


    -- =====================================================
    -- AEROMETRO
    -- =====================================================

    select

        i.usuario_seudonimo,
        'Aerometro' as modo_transporte,

        t.fecha_hora_local
            as fecha_hora,

        t.zona_conformada
            as zona_origen,

        t.tarifa_gtq::numeric
            as gasto_gtq

    from {{ ref('silver_aerometro_boardings') }} t

    inner join {{ ref('silver_identidad_usuarios_seudonimizada') }} i
        on i.sistema = 'Aerometro'
       and i.llave_original = t.usuario_fuente

),

fecha_corte as (

    select
        max(fecha_hora)::date as fecha_corte
    from eventos

),

eventos_90d as (

    select
        e.*,
        f.fecha_corte

    from eventos e

    cross join fecha_corte f

    where e.fecha_hora::date
          between f.fecha_corte - interval '89 days'
              and f.fecha_corte

),

agregados as (

    select

        usuario_seudonimo,

        max(fecha_corte)
            as fecha_corte,

        count(*) filter (
            where fecha_hora::date
                  >= fecha_corte - interval '6 days'
        )::integer
            as eventos_ultimos_7_dias,

        count(*) filter (
            where fecha_hora::date
                  >= fecha_corte - interval '29 days'
        )::integer
            as eventos_ultimos_30_dias,

        count(*)::integer
            as eventos_ultimos_90_dias,

        count(distinct modo_transporte)::integer
            as cantidad_modos_distintos,

        (
            max(fecha_corte)
            - max(fecha_hora)::date
        )::integer
            as dias_desde_ultimo_evento,

        avg(
            case
                when extract(hour from fecha_hora) between 5 and 8
                  or extract(hour from fecha_hora) between 16 and 19
                    then 1.0
                else 0.0
            end
        )::numeric(10,4)
            as proporcion_eventos_hora_pico,

        sum(coalesce(gasto_gtq, 0))::numeric(14,2)
            as gasto_acumulado_gtq,

        avg(coalesce(gasto_gtq, 0))::numeric(14,2)
            as gasto_promedio_evento_gtq

    from eventos_90d

    group by usuario_seudonimo

),

modos as (

    select

        usuario_seudonimo,
        modo_transporte,

        count(*) as cantidad,

        row_number() over (
            partition by usuario_seudonimo
            order by
                count(*) desc,
                modo_transporte
        ) as posicion

    from eventos_90d

    group by
        usuario_seudonimo,
        modo_transporte

),

modo_principal as (

    select
        usuario_seudonimo,
        modo_transporte as modo_mas_usado

    from modos

    where posicion = 1

),

zonas as (

    select

        usuario_seudonimo,
        zona_origen,

        count(*) as cantidad,

        row_number() over (
            partition by usuario_seudonimo
            order by
                count(*) desc,
                zona_origen
        ) as posicion

    from eventos_90d

    where zona_origen is not null

    group by
        usuario_seudonimo,
        zona_origen

),

zona_principal as (

    select
        usuario_seudonimo,
        zona_origen as zona_origen_mas_frecuente

    from zonas

    where posicion = 1

)

select

    a.usuario_seudonimo,
    a.fecha_corte,

    a.eventos_ultimos_7_dias,
    a.eventos_ultimos_30_dias,
    a.eventos_ultimos_90_dias,

    m.modo_mas_usado,

    a.cantidad_modos_distintos,
    a.dias_desde_ultimo_evento,

    a.proporcion_eventos_hora_pico,

    z.zona_origen_mas_frecuente,

    a.gasto_acumulado_gtq,
    a.gasto_promedio_evento_gtq

from agregados a

left join modo_principal m
    on a.usuario_seudonimo = m.usuario_seudonimo

left join zona_principal z
    on a.usuario_seudonimo = z.usuario_seudonimo