with configuracion as (

    select
        current_setting(
            'app.pseudonymization_key'
        ) as pseudonymization_key

),

identidades as (

    select

        i.sistema,
        i.llave_original,
        i.usuario_integrado_aprox,

        'USR:' ||
        encode(
            hmac(
                i.usuario_integrado_aprox,
                c.pseudonymization_key,
                'sha256'
            ),
            'hex'
        ) as usuario_seudonimo,

        case
            when i.usuario_integrado_aprox like 'AM:%'
                then 'IDENTIDAD_SEPARADA_AEROMETRO'

            else 'IDENTIDAD_NUMERICA_APROX'
        end as estrategia_identidad

    from {{ ref('silver_identidad_usuarios') }} i

    cross join configuracion c

)

select

    sistema,
    llave_original,
    usuario_integrado_aprox,
    usuario_seudonimo,
    estrategia_identidad

from identidades