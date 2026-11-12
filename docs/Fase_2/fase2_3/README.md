# Fase 2.3 — Segmentación KMeans y PCA (José)

**Diagnóstico y segmentación A completados; documentación para revisión.**
Se eligió k=6 antes de examinar abandono. No repetir análisis para este cierre.
La Fase 2.2 y su test único consumido permanecen intactos; 2.4 es responsabilidad
separada de Paolo.

- [Informe de cierre](cierre_fase2_3.md): metodología, codo/silueta, elección de k,
  PCA, nombres aprobados, perfiles, acciones y limitaciones.
- [Diagnóstico agregado](../../reportes_fase2_3/diagnostico_k/resumen.json) y
  [tabla k](../../reportes_fase2_3/diagnostico_k/diagnostico_k.csv).
- [Resumen final k=6](../../reportes_fase2_3/segmentacion_k6/resumen.json) y
  [perfiles originales](../../reportes_fase2_3/segmentacion_k6/perfiles.csv).
- [Codo](../../evidencias/Fase_2/fase2_3/01_codo.png),
  [silueta](../../evidencias/Fase_2/fase2_3/02_silueta.png),
  [PCA con leyenda](../../evidencias/Fase_2/fase2_3/03_pca_2d.con_leyenda.png),
  [PCA original exacto](../../evidencias/Fase_2/fase2_3/03_pca_2d.original.png) y
  [perfiles/acciones](../../evidencias/Fase_2/fase2_3/04_perfiles_y_acciones.png).

A: 60,664 observaciones. Siete numéricas, mediana y StandardScaler; categorías,
identificadores y etiqueta fuera de las distancias. KMeans++, semilla 42, n_init=10,
Lloyd. Silueta k=6: 0.319089 en muestra fija de 3,000; k=6 es compromiso operativo,
no máximo de silueta. PCA explica 57.6841% entre dos componentes.

Los reportes conservan nombres provisionales por trazabilidad; las equivalencias
aprobadas por José están en el informe. Abandono se usa únicamente después de fijar
k para descripción no causal. Las acciones son propuestas de eficacia no medida.
El segmento no se añade al clasificador de 2.2.

Implementación: `scripts/modelado/segmentar_corte_a.py`; pruebas sintéticas:
`tests/modelado/test_segmentar_corte_a.py` (14 aprobadas previamente). Interfaces
históricas: `--analizar-k --muestra-silueta 3000` y `--k 6 --justificacion ...`.
No se ejecutan nuevamente en este cierre. Importar o pedir ayuda no carga datasets.
Las salidas existentes son exclusivas y no se sobrescriben.

Solo se proponen para versionado agregados y PNG sin identificadores. No publicar
datasets ni asignaciones. No se modifica el trabajo de Paolo, la política o el test B.
