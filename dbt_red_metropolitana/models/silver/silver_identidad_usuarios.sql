with identidades as (

    select distinct

        'Transmetro' as sistema,
        usuario_fuente as llave_original,

        'N:' ||
        cast(
            cast(
                regexp_replace(
                    usuario_fuente,
                    '[^0-9]',
                    '',
                    'g'
                ) as bigint
            ) as text
        ) as usuario_integrado_aprox

    from {{ ref('silver_transmetro_validaciones') }}


    union


    select distinct

        'Transurbano' as sistema,
        usuario_fuente as llave_original,

        'N:' ||
        cast(
            cast(
                usuario_fuente as bigint
            ) as text
        ) as usuario_integrado_aprox

    from {{ ref('silver_transurbano_transacciones') }}


    union


    select distinct

        'MetroRiel' as sistema,
        usuario_fuente as llave_original,

        'N:' ||
        cast(
            cast(
                regexp_replace(
                    usuario_fuente,
                    '[^0-9]',
                    '',
                    'g'
                ) as bigint
            ) as text
        ) as usuario_integrado_aprox

    from {{ ref('silver_metroriel_viajes') }}


    union


    select distinct

        'Aerometro' as sistema,
        usuario_fuente as llave_original,

        'AM:' || usuario_fuente
            as usuario_integrado_aprox

    from {{ ref('silver_aerometro_boardings') }}

)

select

    sistema,
    llave_original,
    usuario_integrado_aprox

from identidades