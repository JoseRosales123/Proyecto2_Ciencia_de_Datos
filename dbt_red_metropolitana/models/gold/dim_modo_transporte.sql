with modos as (

    select *
    from (
        values
            (1, 'Transmetro',   'BUS'),
            (2, 'Transurbano',  'BUS'),
            (3, 'MetroRiel',    'FERROCARRIL'),
            (4, 'Aerometro',    'AEREO')
    ) as t (
        modo_key,
        modo_transporte,
        tipo_sistema
    )

)

select *
from modos