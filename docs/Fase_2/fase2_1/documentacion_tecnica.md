# 2.1 — Ensemble y sesgo-varianza

## Objetivo y fuentes

Comparar Random Forest con regresión logística L1 (λ=1) y los dos baselines de 1.4 mediante Average Precision (AP), examinando el desempeño en entrenamiento y validación y su brecha. Esta documentación utiliza los resultados existentes; no se realizó un nuevo entrenamiento para redactarla.

Fuentes: [métricas resumidas](../../reportes_fase2_1/metricas_resumen.csv), [métricas por fold](../../reportes_fase2_1/metricas_por_fold.csv), [configuración](../../reportes_fase2_1/configuracion.json), [comparación con 1.4](../../reportes_fase2_1/comparacion_fase1_4.csv) y [top 10 de importancias](../../reportes_fase2_1/top10_importancias.csv).

## Datos y protocolo

- Dataset local: `datos_modelado_local/fase1_4/dataset_corte_A.csv`; 60,664 personas, 8,110 positivos y 52,554 negativos. Solo corte A, del 2026-07-01; no se utilizaron etiquetas B ni C.
- Nueve variables originales: siete numéricas y dos categóricas. El identificador seudonimizado no es predictor.
- Validación exacta: `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`, conservando el orden del CSV utilizado en 1.4, sin ordenar ni filtrar filas. Los cuatro modelos comparten las mismas particiones.
- Los folds 1–4 contienen 48,531 personas en train y 12,133 en validación; el quinto contiene 48,532 y 12,132. Cada fold tiene 6,488 positivos en train y 1,622 en validación. Las huellas de los índices están en [folds_resumen.csv](../../reportes_fase2_1/folds_resumen.csv).
- Cada pipeline se ajusta solo con train: imputación numérica por mediana y estandarización; imputación categórica constante `DESCONOCIDO` y OneHotEncoder con `handle_unknown='ignore', drop='first'`. La sustitución constante de categorías ausentes no estima estadísticas globales.
- AP se calcula con probabilidades o puntuaciones continuas, sin umbral. La brecha es AP train menos AP validación en cada fold. Las tablas muestran media y desviación estándar muestral entre cinco folds (`ddof=1`).

La comparación histórica contiene 15 coincidencias modelo/fold: dos baselines y logística en cinco folds. Todas presentan diferencia de AP de validación igual a cero frente a 1.4.

## Modelos y configuración ejecutada

El baseline de tasa positiva asigna a todas las personas la prevalencia del train de su fold. El baseline de recencia utiliza `dias_desde_ultimo_evento`, con nulos sustituidos por 28, recorte a [0, 28] y división entre 28; no ajusta parámetros.

La logística reutiliza `make_model('l1', 1.0)` de 1.4: `C=1`, `l1_ratio=1`, solver `liblinear`, `max_iter=1500` y semilla 42. Random Forest utilizó **150 árboles**, `max_depth=None`, `min_samples_leaf=1`, `min_samples_split=2`, `max_features='sqrt'`, bootstrap habilitado, sin ponderación de clases y semilla 42. No se realizó búsqueda de hiperparámetros.

Según la configuración guardada: Python 3.12.10, scikit-learn 1.9.1, NumPy 2.5.4 y pandas 3.1.0. `avisos.csv` y la configuración no registran avisos de ajuste. El comando correspondiente a los resultados existentes es el siguiente, incluido solo para reproducibilidad:

```powershell
python scripts/modelado/comparar_ensembles.py --arboles 150 --repeticiones 3 --jobs -1
```

## Tabla de modelos

Valores redondeados a seis decimales desde `metricas_resumen.csv`; ± corresponde a la DE entre folds.

| Modelo | AP train, media ± DE | AP validación, media ± DE | Brecha train−validación, media ± DE |
|---|---:|---:|---:|
| Baseline tasa positiva | 0.133687 ± 0.000001 | 0.133687 ± 0.000005 | ≈ 0 ± 0.000006 |
| Baseline recencia | 0.456507 ± 0.003003 | 0.456792 ± 0.011985 | −0.000285 ± 0.014988 |
| Logística L1, λ=1 | 0.483969 ± 0.002988 | **0.482854 ± 0.012173** | 0.001115 ± 0.015125 |
| Random Forest | 0.976434 ± 0.000359 | 0.407661 ± 0.011362 | 0.568774 ± 0.011533 |

La brecha exacta media del baseline de tasa es −1.362329860032929e−10, prácticamente cero. La diferencia media de AP validación logística−RF es 0.075193; logística supera RF en los cinco folds. RF también queda por debajo del baseline de recencia en los cinco folds.

## Análisis de sesgo-varianza

**Random Forest:** AP train de 0.976434 frente a AP validación de 0.407661 y brecha media de 0.568774. En todos los folds la brecha es grande (entre 0.553501 y 0.580358). Es evidencia de sobreajuste marcado, compatible con alta varianza de generalización en esta configuración de árboles sin límite de profundidad. La AP de entrenamiento elevada no se traduce en una mejora fuera del train: incluso el baseline de recencia obtiene mejor AP de validación.

**Logística L1:** mantiene AP train y validación próximas, con brecha media de 0.001115, y alcanza la mayor AP media de validación entre los cuatro modelos. Su generalización observada es mejor que la del bosque evaluado. En dos folds la brecha es negativa y en tres positiva; la media pequeña no debe interpretarse como igualdad exacta entre train y validación ni como ausencia demostrada de sesgo.

**Baselines:** la tasa positiva tiene capacidad de discriminación nula porque entrega una puntuación constante, aunque su brecha sea prácticamente cero; este patrón ilustra que una brecha pequeña no garantiza buen desempeño. Recencia captura señal predictiva y queda entre logística y RF en AP de validación. Su pequeña brecha negativa media es compatible con variación entre las particiones y no demuestra una ventaja intrínseca de validación sobre entrenamiento.

Las métricas no estiman una descomposición formal de sesgo y varianza. En particular, la DE de AP de validación de RF (0.011362) es ligeramente menor que la de logística (0.012173): la interpretación de alta varianza se apoya en el sobreajuste train−validación, no en afirmar una mayor dispersión entre folds. Los folds comparten datos de entrenamiento, por lo que esas DE no son intervalos de confianza ni pruebas de significancia. λ=1 se seleccionó previamente con este mismo CV en 1.4; no hay evaluación externa independiente. Las conclusiones se limitan al corte A y a las configuraciones evaluadas.

## Diez importancias por permutación en validación

Se utilizó `permutation_importance` sobre **Random Forest**, con `scoring='average_precision'`, exclusivamente en la matriz de validación transformada por el preprocesador ya ajustado con train y con las etiquetas de validación. No se ajustó ningún modelo durante las permutaciones ni se calcularon importancias sobre train. Se realizaron **tres repeticiones por característica y fold**; la semilla es `42 + fold`.

Como hay nueve variables originales, el top 10 corresponde a **columnas codificadas**, incluidas variables dummy, comunes a los cinco folds. La importancia es la caída de AP de validación al permutar cada columna. Primero se promedian las tres repeticiones dentro de cada fold; después se obtiene la media y DE entre los cinco folds. Las repeticiones y su dispersión interna se conservan en [permutaciones_validacion.csv](../../reportes_fase2_1/permutaciones_validacion.csv) e [importancias_por_fold.csv](../../reportes_fase2_1/importancias_por_fold.csv).

| Posición | Característica codificada | Caída AP media | DE entre folds |
|---|---|---:|---:|
| 1 | `num__dias_desde_ultimo_evento` | 0.184233 | 0.009196 |
| 2 | `num__eventos_ultimos_7_dias` | 0.052866 | 0.006398 |
| 3 | `cat__zona_origen_mas_frecuente_Zona 13` | 0.005084 | 0.005038 |
| 4 | `cat__zona_origen_mas_frecuente_Zona 10` | 0.004664 | 0.003143 |
| 5 | `cat__zona_origen_mas_frecuente_Zona 11` | 0.000335 | 0.001572 |
| 6 | `cat__zona_origen_mas_frecuente_Zona 7` | −0.000108 | 0.002179 |
| 7 | `cat__zona_origen_mas_frecuente_Zona 9` | −0.000109 | 0.002255 |
| 8 | `cat__zona_origen_mas_frecuente_Zona 12` | −0.000221 | 0.001898 |
| 9 | `cat__zona_origen_mas_frecuente_Zona 8` | −0.000403 | 0.001823 |
| 10 | `cat__zona_origen_mas_frecuente_Zona 4` | −0.000443 | 0.001597 |

La recencia y los eventos de los últimos siete días producen las mayores caídas de AP. Las importancias negativas se conservan: indican que, en promedio, permutar esas columnas mejoró ligeramente AP; no prueban un efecto protector ni una relación causal. Varias medias son pequeñas respecto a su dispersión. Las variables correlacionadas pueden compartir u ocultar importancia; permutar una dummy aisladamente puede crear combinaciones categóricas no observadas. Este ranking describe el bosque evaluado y no sustituye una interpretación de la logística elegida.

## Decisión (cuatro líneas)

Se mantiene la regresión logística L1 con λ=1 por alcanzar la mayor AP media de validación: 0.482854.  
Su brecha media de 0.001115 muestra un comportamiento train−validación más equilibrado que el RF evaluado.  
Random Forest queda por debajo en los cinco folds, con AP validación de 0.407661 y brecha de 0.568774.  
La decisión se limita al corte A y a estas configuraciones; no demuestra superioridad sobre todos los bosques ni validación externa.

## Reportes y evidencias

Gráficas del entrenamiento: [AP train/validación](../../reportes_fase2_1/ap_train_validacion.png) y [top 10 por permutación](../../reportes_fase2_1/top10_permutation_validacion.png). Los CSV agregados y la configuración se conservan en `docs/reportes_fase2_1/`; no se publican datasets individuales.

Se verificó la existencia de las tres evidencias solicitadas, todas con tamaño mayor que cero:

- [01_comparacion_modelos.png](../../evidencias/Fase_2/fase2_1/01_comparacion_modelos.png)
- [02_sesgo_varianza.png](../../evidencias/Fase_2/fase2_1/02_sesgo_varianza.png)
- [03_importancia_permutacion.png](../../evidencias/Fase_2/fase2_1/03_importancia_permutacion.png)

No faltan archivos de evidencia. Esta revisión verificó su presencia; no creó ni reemplazó capturas. No se modificaron la Fase 1, PostgreSQL ni Docker, y no se usaron cortes B/C ni se reentrenaron modelos durante el cierre documental.
