select *

from {{ ref('feat_usuario_movilidad') }}

where eventos_ultimos_7_dias
      > eventos_ultimos_30_dias

   or eventos_ultimos_30_dias
      > eventos_ultimos_90_dias