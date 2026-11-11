> **Estado final actualizado:** B fue evaluado una sola vez el 2026-11-11,
> FINALIZADO a las 20:32:33.890840 UTC, commit de ejecución
> `931146e26c0dec88ec374bd2b8015c185fdaf90f`. Intento consumido: no repetir ni reajustar.
> Véase [el cierre académico y técnico](cierre_fase2_2.md). El texto siguiente conserva
> el contexto histórico de validación A y preparación anterior a B; sus menciones de
> B pendiente/no autorizado y sus comandos futuros no describen el estado actual ni
> habilitan otra ejecución. Política y artefactos congelados permanecen intactos.

# 2.2 — Umbral económico: validación en A

Solo A, 60664 personas y 8110 positivos. B permanece cerrado como test único.
Se reutiliza make_model('l1', 1.0), con las nueve variables y el preprocesamiento de 1.4.
Cinco folds estratificados, shuffle=True y random_state=42, sin alterar el orden del CSV.
Cada pipeline nuevo se ajusta solo con train. Cada persona recibe una sola predicción OOF.
No se guardan predicciones individuales, identificadores ni modelos finales.

## Escenario económico y política definitiva

Contacto Q5, retención condicional al abandono 25%, valor retenido Q60.
Ganancia esperada individual: 0.25 × 60 × p − 5 = 15p − 5.
Umbral teórico: 5/15 = 0.333333333333; contactar si p ≥ umbral.
En el empate se contacta, con ganancia esperada cero. No contactar tiene ganancia cero.
Ganancia esperada del grupo: suma de (15p − 5) entre los contactados.
Ganancia observada simulada: 15TP − 5(TP+FP), usando las etiquetas de A.
Esta última usa retención esperada del 25%: no mide retenciones reales ni beneficio causal realizado.
Se supone costo constante, valor constante, capacidad sin límite y beneficio nulo en no abandonantes.

Se congela la regresión logística L1 con λ=1 (C=1), sin recalibración adicional,
y el umbral **exacto 1/3**, representado como numerador 1 y denominador 3.
Se contacta si la probabilidad estimada es mayor o igual que 1/3; 33.33% es solo
una presentación redondeada y no el valor usado para decidir.
Se adopta 1/3 por la condición de rentabilidad económica, sin optimizar sobre las etiquetas.
La curva empírica es descriptiva; elegir su máximo y reportar ese mismo resultado produciría optimismo.
No se seleccionan candidatos empíricos ni se usan resultados B.
La revisión OOF en A respalda adoptar esta política bajo los supuestos económicos,
con las limitaciones de calibración descritas a continuación. La política queda
congelada antes de abrir B; no se ajustará con el resultado del test único.
Una futura recalibración sería otra política y requeriría un protocolo independiente;
no está permitida dentro de esta evaluación de B.

## Resultados agregados OOF

AP OOF: 0.482160; Brier: 0.089065;
log-loss: 0.296666; ECE en diez intervalos: 0.012559.
Probabilidad media: 0.133722; prevalencia: 0.133687.
Se compara Brier/log-loss contra la tasa del train correspondiente en metricas_oof.csv.
Menor Brier/log-loss es mejor, pero también dependen de discriminación y no demuestran calibración.
La curva de fiabilidad presenta tasas y probabilidades por intervalo, con sus tamaños;
ECE depende de los intervalos y no tiene aquí una regla automática de aprobación.

La curva está razonablemente cerca de la diagonal, con desviaciones locales:
en [0.3, 0.4), intervalo que contiene el umbral, la probabilidad media es 0.345005
y la tasa observada 0.361186 entre 2,597 personas. En [0.7, 0.8) se sobreestima
el riesgo (0.745063 frente a 0.683502; 891 personas). El último intervalo tiene
solo una persona y no admite una interpretación estable. La calibración no es perfecta.
Brier mejora frente al baseline de tasa del train (0.115815), al igual que log-loss
(baseline 0.393336), aunque estas métricas también dependen de discriminación.
La media global predicha próxima a la prevalencia no prueba calibración local.

Con el umbral congelado hay 7,019 contactos: TP=3,598, FP=3,421, FN=4,512,
TN=49,133; precisión=0.512609 y recall=0.443650. La ganancia esperada es
Q21,013.94 y la observada simulada Q18,875.00. La diferencia no es una medida
de retención realizada: la primera utiliza probabilidades y la segunda etiquetas,
pero ambas suponen el beneficio esperado de Q15 por verdadero positivo.

Políticas comparadas (totales OOF sobre A):

```text
        politica   umbral  personas  contactados   tp    fp   fn    tn  precision   recall  ganancia_esperada_q  ganancia_observada_simulada_q
    no_contactar 1.000000     60664            0    0     0 8110 52554   0.000000 0.000000             0.000000                            0.0
 contactar_todos 0.000000     60664        60664 8110 52554    0     0   0.133687 1.000000       -181638.374963                      -181670.0
       umbral_05 0.500000     60664         3732 2283  1449 5827 51105   0.611736 0.281504         17243.885463                        15585.0
umbral_economico 0.333333     60664         7019 3598  3421 4512 49133   0.512609 0.443650         21013.941997                        18875.0
```

La media y DE muestral de AP por fold están separadas de AP OOF agrupada;
AP no es aditiva y ambos cálculos pueden diferir. Precisión se define como cero
si no hay contactos, por convención; no significa precisión medida en un grupo vacío.
La ganancia media por fold no es la ganancia total: los totales están en comparacion_politicas.csv.
Los folds comparten train; las DE no son intervalos de confianza.
λ=1 ya fue seleccionado en 1.4 con este CV: no es evaluación externa independiente.
La ganancia esperada depende de probabilidades interpretables; AP mide ranking, no calibración.

## Reproducción y archivos

`python scripts/modelado/seleccionar_umbral.py --ejecutar-a`

Este comando documenta la ejecución histórica de A; no se volvió a ejecutar al
congelar la política. Volver a ejecutarlo sobrescribe sus reportes y la documentación
generada, por lo que no debe usarse para inspeccionar resultados ni cerrar el test B.

CSV y gráficas agregados: docs/reportes_fase2_2/. Configuración incluye versiones,
huella del dataset y parámetros. No se consultó PostgreSQL, Docker ni dbt.
Este script no incluye lectura, preparación, entrenamiento ni evaluación de B/C.
El test único B requerirá autorización explícita posterior y una política previamente fijada.

## Política congelada y test único B

La definición definitiva está en [politica_congelada.json](politica_congelada.json).
Incluye todos los hiperparámetros registrados, las nueve variables, el preprocesamiento,
las versiones, las huellas del código y dataset A, el CV, el umbral como fracción y
los supuestos económicos. `estado_b=NO_EJECUTADO` describe el momento de congelación;
la política es inmutable. El estado operativo posterior lo registra la bitácora, no
una modificación de este archivo. La huella SHA256 de la política se guarda en
`politica_congelada.sha256` y debe vincularse a la autorización posterior.

El evaluador separado `scripts/modelado/evaluar_test_unico_b.py` está preparado,
pero **no fue ejecutado**. Exige flag, frase explícita y un archivo local de autorización
creado solo después de recibir una instrucción posterior del usuario. Verifica política,
commit, huellas del código, dataset A, versiones e hiperparámetros. Ajustará un pipeline
nuevo solo con todo A, sin modificar artefactos de 1.4/2.1. Con B solo hará predicción
y cálculo de métricas agregadas en el umbral fijo; no buscará umbrales, calibración
ni hiperparámetros. La fecha UTC, commit, huellas, matriz de confusión, AP, ROC-AUC,
Brier, log-loss, precisión, recall y ambas ganancias quedarán registrados.

Antes de cualquier lectura de B, incluida su huella, crea exclusivamente y sincroniza
en disco `datos_modelado_local/fase2_2/test_b_bitacora.jsonl` con modo `x`.
Un segundo proceso en el mismo sistema de archivos no puede reservar el mismo intento.
Cada fallo posterior consume el intento, incluso si B aún no se abrió; no existe opción
de reintento, borrado o sobrescritura. Antes de abrir B registra y sincroniza el evento
`ANTES_DE_LECTURA_B`. Los resultados usan un directorio nuevo y apertura exclusiva.

**Límite de garantía:** esta exclusión es local. No impide que una persona borre o altere
la bitácora, copie el repositorio, cambie el programa o ejecute en otra máquina; tampoco
garantiza exclusión distribuida mediante OneDrive. Para el test se debe designar una sola
máquina y operador, conservar y respaldar la bitácora y no ejecutar copias sincronizadas.
Si hay fallo o duda sobre una lectura previa, detener el proceso para auditoría; no
eliminar la reserva ni repetir el test. La autorización local no autentica por sí sola
la voluntad del usuario: debe conservar una referencia a su instrucción explícita.

## Dependencia pendiente: exportación de B

La revisión se limitó al código existente, sin abrir archivos B ni consultar PostgreSQL.
`scripts/etiquetado/calcular_etiquetas.py` contempla A/B y conteos agregados.
En el Bloque 4 se preparó `scripts/modelado/exportar_dataset_corte_b.py`, sin ejecutarlo;
el procedimiento, controles y dependencias están en [exportacion_b.md](exportacion_b.md).
`exportar_dataset_corte_a.py` está fijado a A y no se modificó. Sigue pendiente
autorizar por separado la exportación de B y verificar cobertura antes de habilitar
la evaluación. No se ejecutó etiquetado ni se generó un dataset B.

El contrato futuro es un CSV local `datos_modelado_local/fase2_2/dataset_corte_B.csv`
con las nueve características de 1.4, `abandono`, `usuario_seudonimo`, `corte='B'`
y `fecha_corte='2026-07-31'`, una fila por persona, sin nulos/duplicados en identificadores
y etiquetas binarias. El exportador autorizado deberá certificar población elegible,
ventanas temporales completas, correspondencia entre features y etiquetas y SHA256,
sin revelar etiquetas ni métricas al seleccionar la política. El evaluador no construye
etiquetas ni se conecta a PostgreSQL. No se publican ese CSV, identificadores ni probabilidades.

## Evidencias

- [01_calculo_umbral.png](../../evidencias/Fase_2/fase2_2/01_calculo_umbral.png): diagrama matemático del escenario, no una captura de ejecución.
- [02_calibracion_oof.png](../../evidencias/Fase_2/fase2_2/02_calibracion_oof.png): evidencia existente de calibración A.
- [03_curva_ganancia.png](../../evidencias/Fase_2/fase2_2/03_curva_ganancia.png): evidencia existente de ganancia A.

No se volvió a ejecutar CV, no se entrenó el modelo final y no se leyó B durante este cierre.
