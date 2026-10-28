select *

from {{ ref('feat_usuario_movilidad') }}

where proporcion_eventos_hora_pico < 0
   or proporcion_eventos_hora_pico > 1