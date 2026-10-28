with eventos as (

    select

        seq,
        commit_ts,
        op,
        tarjeta,

        nullif(perfil, '') as perfil,
        nullif(zona_residencia, '') as zona_residencia,
        nullif(estado, '') as estado,

        max(
            case
                when nullif(perfil, '') is not null
                then seq
            end
        ) over (
            partition by tarjeta
            order by seq
            rows between unbounded preceding and current row
        ) as seq_ultimo_perfil,

        max(
            case
                when nullif(zona_residencia, '') is not null
                then seq
            end
        ) over (
            partition by tarjeta
            order by seq
            rows between unbounded preceding and current row
        ) as seq_ultima_zona

    from {{ source('staging', 'cdc_padron_usuarios') }}

    where tarjeta <> 'SIN-TARJETA'

),

atributos_reconstruidos as (

    select

        e.seq,
        e.commit_ts,
        e.op,
        e.tarjeta,

        p.perfil as perfil_efectivo,

        z.zona_residencia as zona_residencia_efectiva,

        case
            when e.op = 'DELETE'
                then 'INACTIVA'

            else coalesce(
                e.estado,
                'ACTIVA'
            )
        end as estado_version,

        case
            when e.op = 'DELETE'
                then false
            else true
        end as activo

    from eventos e

    left join {{ source('staging', 'cdc_padron_usuarios') }} p
        on p.seq = e.seq_ultimo_perfil

    left join {{ source('staging', 'cdc_padron_usuarios') }} z
        on z.seq = e.seq_ultima_zona

),

versiones as (

    select

        md5(
            tarjeta
            || ':'
            || seq::text
        ) as version_id,

        tarjeta,

        perfil_efectivo as perfil,
        zona_residencia_efectiva as zona_residencia,

        estado_version as estado,
        activo,

        op as operacion_origen,

        seq as vigente_desde_seq,

        lead(seq) over (
            partition by tarjeta
            order by seq
        ) as vigente_hasta_seq_exclusiva,

        commit_ts as commit_ts_evento,

        lead(commit_ts) over (
            partition by tarjeta
            order by seq
        ) as siguiente_commit_ts_evento,

        (
            lead(seq) over (
                partition by tarjeta
                order by seq
            ) is null
        ) as es_version_actual,

        (
            op = 'DELETE'
            and perfil_efectivo is null
            and zona_residencia_efectiva is null
        ) as tombstone_sin_cuerpo

    from atributos_reconstruidos

)

select
    version_id,
    tarjeta,

    perfil,
    zona_residencia,

    estado,
    activo,

    operacion_origen,

    vigente_desde_seq,
    vigente_hasta_seq_exclusiva,

    commit_ts_evento,
    siguiente_commit_ts_evento,

    es_version_actual,
    tombstone_sin_cuerpo

from versiones