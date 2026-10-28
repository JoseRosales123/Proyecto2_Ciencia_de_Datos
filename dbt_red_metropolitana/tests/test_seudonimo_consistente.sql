select
    usuario_integrado_aprox

from {{ ref('silver_identidad_usuarios_seudonimizada') }}

group by usuario_integrado_aprox

having count(distinct usuario_seudonimo) <> 1