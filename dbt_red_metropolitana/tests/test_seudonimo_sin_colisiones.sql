select
    usuario_seudonimo

from {{ ref('silver_identidad_usuarios_seudonimizada') }}

group by usuario_seudonimo

having count(distinct usuario_integrado_aprox) <> 1