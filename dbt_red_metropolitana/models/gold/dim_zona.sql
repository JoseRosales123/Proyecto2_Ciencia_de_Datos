with zonas_servidas as (

    select distinct
        zona_conformada as zona_nombre

    from {{ ref('silver_zonas_conformadas') }}

    where zona_conformada is not null

),

zonas_residencia as (

    select distinct
        trim(zona_residencia) as zona_nombre

    from {{ ref('silver_padron_usuarios_scd2') }}

    where zona_residencia is not null
      and trim(zona_residencia) <> ''

),

universo_zonas as (

    select zona_nombre
    from zonas_servidas

    union

    select zona_nombre
    from zonas_residencia

),

dimension as (

    select

        row_number() over (
            order by u.zona_nombre
        )::integer as zona_key,

        u.zona_nombre,

        case
            when u.zona_nombre ~ '^Zona [0-9]+$'
                then 'ZONA_URBANA'
            else 'MUNICIPIO_SECTOR'
        end as tipo_zona,

        case
            when s.zona_nombre is not null
                then true
            else false
        end as tiene_servicio

    from universo_zonas u

    left join zonas_servidas s
        on u.zona_nombre = s.zona_nombre

)

select *
from dimension