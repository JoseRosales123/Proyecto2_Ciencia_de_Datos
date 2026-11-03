
# Fase 1.4 — Baselines y regresión logística regularizada

## 1. Objetivo

Evaluar modelos predictivos de abandono de usuarios de la Red Metropolitana mediante dos baselines y regresión logística regularizada.

Se utilizan exclusivamente las características y etiquetas correspondientes al corte A, con fecha 2026-07-01. No se utilizan las etiquetas del corte B para entrenar ni seleccionar modelos.

## 2. Dataset de entrenamiento

El dataset se generó mediante:

`scripts/modelado/exportar_dataset_corte_a.py`

Se reutilizaron las reglas de etiquetado del apartado 1.2 y las características construidas en 1.3.

| Indicador | Resultado |
|---|---:|
| Personas elegibles | 60,664 |
| Abandono = 1 | 8,110 |
| Abandono = 0 | 52,554 |
| Tasa positiva | 13.3687% |
| Etiquetas sin características | 0 |
| Características sin etiqueta | 0 |

El dataset individual se conserva en `datos_modelado_local/fase1_4/dataset_corte_A.csv` y no debe publicarse en GitHub porque contiene identificadores seudonimizados.

## 3. Métrica seleccionada

La métrica principal es Average Precision (AP), que resume el desempeño sobre la curva precisión-recall.

Se eligió porque el abandono representa aproximadamente el 13.37% de la población, por lo que existe desbalance entre las clases. AP permite comparar la capacidad de los modelos para priorizar usuarios positivos y considera el comportamiento de precisión y recuperación a distintos umbrales.

Como métricas complementarias se calcularon ROC-AUC y F1 con umbral 0.5.

## 4. Modelos comparados

### Baseline 1 — Tasa positiva

Asigna a todos los usuarios la tasa de abandono observada en la partición de entrenamiento de cada fold.

No utiliza características individuales y funciona como referencia mínima.

### Baseline 2 — Recencia

Utiliza exclusivamente los días desde el último abordaje como puntuación, divididos entre 28 y limitados al intervalo de 0 a 1.

No se entrena un modelo ni se ajustan parámetros mediante las etiquetas.

### Regresión logística L1 y L2

Se evaluaron las regularizaciones L1 y L2 mediante scikit-learn.

Los valores de λ utilizados fueron:

0.01, 0.1, 1, 10 y 100.

Se utilizó la relación λ = 1/C, según la parametrización del clasificador, donde C representa el inverso de la intensidad de regularización.

El preprocesamiento incluye imputación de valores faltantes, estandarización de variables numéricas y codificación One-Hot de variables categóricas.

Estas transformaciones se ajustan dentro de cada fold para evitar fuga de información entre entrenamiento y validación.

## 5. Validación cruzada

Se utilizó StratifiedKFold con:

- Cinco folds.
- Mezcla aleatoria activada.
- Semilla 42.
- Las mismas particiones para todos los modelos.

La estratificación mantiene aproximadamente la proporción de abandonos en las particiones.

Los resultados se presentan mediante la media y la desviación estándar de las métricas obtenidas en los cinco folds.

## 6. Resultados

| Modelo | AP media | Desviación estándar |
|---|---:|---:|
| Baseline 1 — Tasa positiva | 0.133687 | 0.000005 |
| Baseline 2 — Recencia | 0.456792 | 0.011985 |
| Logística L1 — λ = 1 | 0.482854 | 0.012173 |
| Logística L2 — λ = 0.01 | 0.482802 | 0.012146 |

Ambas regresiones logísticas superaron a los baselines según la AP media.

Se seleccionó L1 con λ = 1 por obtener la AP media más alta entre las configuraciones evaluadas.

La diferencia entre L1 y L2 es muy pequeña y no demuestra una superioridad estadística significativa.

## 7. Análisis de regularización

La gráfica `ap_vs_lambda.png` presenta la AP media y la desviación estándar de los cinco folds frente a λ.

Se observa un desempeño relativamente estable para valores de λ entre 0.01 y 10.

Con λ = 100 aparece una reducción de AP, especialmente en L1, lo que sugiere que una regularización excesivamente fuerte perjudica el desempeño predictivo.

## 8. Interpretación de coeficientes

El modelo L1 seleccionado se ajustó nuevamente utilizando todo el dataset del corte A, después de elegir λ.

| Característica | Coeficiente | Odds ratio |
|---|---:|---:|
| Días desde último evento | +0.851947 | 2.344207 |
| Eventos últimos 7 días | -0.733219 | 0.480360 |
| Zona 13 | +0.523849 | 1.688514 |
| Zona 10 | +0.507652 | 1.661386 |
| Gasto acumulado GTQ | -0.246619 | 0.781438 |

### Interpretaciones

1. Días desde último evento: una mayor inactividad se asocia con mayores odds de abandono, manteniendo las demás características constantes.
2. Eventos últimos 7 días: una mayor actividad reciente se asocia con menores odds de abandono.
3. Zona 13: presenta mayores odds estimadas que la zona de referencia omitida en la codificación.
4. Zona 10: también presenta una asociación positiva respecto de la categoría de referencia.
5. Gasto acumulado: valores más altos se asocian con menores odds estimadas de abandono.

Los coeficientes numéricos corresponden a variables estandarizadas. Los coeficientes categóricos son comparaciones respecto de la categoría omitida.

La interpretación es asociativa y no demuestra causalidad.

## 9. Archivos del proyecto

Scripts:

- `scripts/modelado/exportar_dataset_corte_a.py`
- `scripts/modelado/entrenar_baselines_logistica.py`

Reportes:

- `docs/reportes_fase1_4/tabla_modelos.csv`
- `docs/reportes_fase1_4/metricas_por_fold.csv`
- `docs/reportes_fase1_4/metricas_resumen_todos.csv`
- `docs/reportes_fase1_4/ap_vs_lambda.png`
- `docs/reportes_fase1_4/coeficientes_modelo_elegido.csv`
- `docs/reportes_fase1_4/configuracion_resultados.json`

Evidencias:

- `docs/evidencias/Fase_1/fase1_4/`

## 10. Reproducción

Desde la raíz del repositorio:

Primero, generar el dataset local:

`python .\scripts\modelado\exportar_dataset_corte_a.py`

Después, entrenar y comparar modelos:

`python .\scripts\modelado\entrenar_baselines_logistica.py`

Se requieren pandas, numpy, scikit-learn y matplotlib, además de las dependencias para conectarse a PostgreSQL.

## 11. Limitaciones

- La selección de λ y la estimación de desempeño utilizan los mismos cinco folds; por tanto, no se trata de una evaluación externa independiente.
- El rendimiento reportado corresponde únicamente al corte A.
- El corte B no se utilizó como conjunto de prueba.
- Los resultados están condicionados a las reglas de etiquetado e integración aproximada de identidades.
- Los coeficientes describen asociaciones, no efectos causales.
- La AP no representa directamente el porcentaje de predicciones correctas.

## 12. Conclusión

Se construyeron dos baselines y se evaluaron regresiones logísticas regularizadas mediante cinco folds estratificados.

El modelo L1 con λ = 1 obtuvo la mayor AP media (0.482854), superando al baseline de recencia (0.456792) y al baseline constante (0.133687).

Se generaron los reportes, la gráfica de regularización y los coeficientes necesarios para interpretar el comportamiento del modelo seleccionado.
