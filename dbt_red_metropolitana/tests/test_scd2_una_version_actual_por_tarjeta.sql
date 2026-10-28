select
    tarjeta

from {{ ref('silver_padron_usuarios_scd2') }}

group by tarjeta

having count(*) filter (
    where es_version_actual = true
) <> 1