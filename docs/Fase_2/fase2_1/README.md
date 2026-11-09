# Fase 2.1 — Ensemble y sesgo-varianza

Solo corte A: 60664 personas y 8110 positivos. Sin etiquetas B/C.
Mismos cinco folds y orden de filas que 1.4. Preprocesamiento dentro de pipelines,
ajustado exclusivamente con train. L1 λ=1 conserva la configuración de 1.4.
Bosque con parámetros prefijados, sin búsqueda de hiperparámetros.

## Resultados observados

- Baseline_recencia: AP train 0.456507 ± 0.003003; AP validación 0.456792 ± 0.011985; brecha train−validación -0.000285 ± 0.014988.
- Baseline_tasa_positiva: AP train 0.133687 ± 0.000001; AP validación 0.133687 ± 0.000005; brecha train−validación -0.000000 ± 0.000006.
- Logistica_l1_lambda_1: AP train 0.483969 ± 0.002988; AP validación 0.482854 ± 0.012173; brecha train−validación 0.001115 ± 0.015125.
- RandomForest: AP train 0.976434 ± 0.000359; AP validación 0.407661 ± 0.011362; brecha train−validación 0.568774 ± 0.011533.

Diferencia RF−L1 de AP en validación: -0.075193 ± 0.010867; RF supera L1 en 0/5 folds.

## Interpretación y límites

Una AP train mayor que validación es compatible con sobreajuste. La magnitud de
la brecha y la dispersión deben leerse junto con AP de validación y los baselines.
Una brecha pequeña no demuestra bajo sesgo: ambos desempeños pueden ser bajos.
Estas mediciones no constituyen una descomposición formal de sesgo y varianza.
Los folds comparten entrenamiento; la DE no es un intervalo de confianza.
L1 λ=1 ya fue seleccionado usando este CV en 1.4; no hay evaluación externa independiente.
Máxima diferencia absoluta frente a AP histórica: 0. Revisar avisos y versiones si difiere.

## Importancia por permutación

RF: caída de AP al permutar exclusivamente validación, sin reentrenar.
Top 10 de columnas codificadas comunes a los cinco folds, no diez variables originales:
solo existen nueve variables originales. Se conservan valores negativos.
La DE entre folds usa las medias de las repeticiones por fold; las repeticiones
y su dispersión interna se guardan por separado. No representan personas.
Permutar una dummy puede producir combinaciones categóricas no observadas.
Correlación entre variables puede repartir u ocultar importancia; no indica causalidad.

## Reproducción

`python scripts/modelado/comparar_ensembles.py --arboles 150 --repeticiones 3 --jobs -1`

Los CSV y gráficos están en `docs/reportes_fase2_1/`. La configuración incluye
versiones, parámetros, avisos y huellas agregadas de dataset/folds.
No se exportan identificadores, predicciones ni filas individuales.
