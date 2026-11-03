
# Fase 1.3 — Features y auditoría de fuga temporal

## 1. Objetivo

Construir características de movilidad para analizar el abandono de usuarios del sistema Red Metropolitana, utilizando información disponible antes de cada fecha de corte.

Se reutilizó la lógica del modelo `feat_usuario_movilidad.sql` del Proyecto 1, adaptándola a ventanas históricas de 7 y 28 días y a las reglas de elegibilidad definidas en el apartado 1.2.

## 2. Modelo implementado

Archivo principal:

`dbt_red_metropolitana/models/features/feat_abandono_cortes.sql`

El modelo integra información de cuatro sistemas:

- Transmetro.
- Transurbano.
- MetroRiel.
- Aerómetro.

Los eventos se obtienen de modelos Silver y se relacionan con identidades seudonimizadas.

## 3. Fechas de corte

| Corte | Fecha | Uso |
|---|---|---|
| A | 2026-07-01 | Features y comparación con etiquetado |
| B | 2026-07-31 | Features y comparación con etiquetado |
| C | 2026-08-29 | Features; sin etiqueta posterior validada |

El corte C se utiliza como fecha adicional para generar características. No se considera etiquetado para abandono, debido a que no contamos con los 30 días posteriores completos.

## 4. Unidad de análisis

La unidad seleccionada es la persona aproximada, representada mediante `usuario_seudonimo`.

La clave lógica de cada registro es:

`(corte, usuario_seudonimo)`

Se exige un mínimo de dos eventos válidos en los 28 días anteriores al corte.

Se incorporó la última operación CDC anterior a cada fecha de corte para determinar la disponibilidad de los identificadores de Transmetro.

Una persona se conserva cuando tiene al menos un identificador disponible, incluyendo identificadores de otros operadores.

## 5. Características generadas

- Eventos de los últimos 7 días.
- Eventos de los últimos 28 días.
- Modo de transporte más utilizado.
- Cantidad de modos distintos.
- Días desde el último evento.
- Proporción de eventos durante horas pico.
- Zona de origen más frecuente.
- Gasto acumulado.
- Gasto promedio por evento.
- Fecha y hora del último evento previo.

Todas las ventanas excluyen el día de corte y los eventos posteriores.

## 6. Resultados

| Corte | Personas | Fecha máxima del evento |
|---|---:|---|
| A | 60,664 | 2026-06-30 22:59:58 |
| B | 59,126 | 2026-07-30 22:59:49 |
| C | 58,726 | 2026-08-28 22:59:53 |
| Total | 178,516 | |

En los tres cortes, el número de filas coincidió con el número de usuarios únicos.

Los conteos de A y B también coinciden con los obtenidos en el apartado 1.2.

## 7. Corrección de elegibilidad CDC

Inicialmente, el corte A generó 60,892 personas.

Al investigar la población se identificaron:

- 482 personas asociadas a alguna tarjeta con baja CDC.
- 254 personas que conservaban otro identificador disponible.
- 228 personas sin identificadores disponibles.

La incorporación de las reglas CDC redujo la población de A de 60,892 a 60,664 personas, coincidiendo con el conteo del etiquetado.

La coincidencia numérica no sustituye una comparación individual de las identidades.

## 8. Auditoría de fuga temporal

Se compararon dos versiones de las características del corte A:

1. Características calculadas utilizando las fuentes completas, con el filtro temporal del modelo.
2. Características calculadas utilizando un límite adicional de lectura hasta el 1 de julio de 2026.

Resultados:

| Indicador | Resultado |
|---|---:|
| Filas originales | 60,664 |
| Filas con recorte temporal | 60,664 |
| Registros exclusivos de alguna versión | 0 |
| Características diferentes | 0 |

La comparación se realizó por `usuario_seudonimo` y por el contenido de las filas.

Resultado: **cero diferencias**.

Alcance: esta auditoría demuestra la invariancia bajo el límite temporal adicional aplicado a los eventos. No representa una eliminación física de datos posteriores ni una auditoría completa de la temporalidad de las tablas de identidad.

## 9. Pruebas automáticas

Archivos:

`dbt_red_metropolitana/models/features/feat_abandono_cortes.yml`

`dbt_red_metropolitana/tests/test_feat_abandono_cortes_integridad.sql`

Comando utilizado:

`dbt test --select feat_abandono_cortes --profiles-dir .\config`

Resultados:

- 8 pruebas ejecutadas.
- 8 pruebas aprobadas.
- 0 errores.
- 0 advertencias.
- Duración: 0.97 segundos.

Las pruebas verifican valores obligatorios, cortes permitidos, duplicados y consistencia temporal de las características.

## 10. Reproducción

Desde `dbt_red_metropolitana`:

`dbt run --select feat_abandono_cortes --profiles-dir .\config`

Para ejecutar únicamente las pruebas:

`dbt test --select feat_abandono_cortes --profiles-dir .\config`

Los cortes pueden parametrizarse mediante `feature_cortes`. El límite temporal adicional de auditoría se controla con `feature_max_timestamp`.

## 11. Evidencias

Las capturas se encuentran en:

`docs/evidencias/Fase_1/fase1_3/`

Las evidencias incluyen las ejecuciones de features, validaciones de población, unicidad, integración CDC, auditoría temporal y pruebas dbt.

## 12. Limitaciones y trabajo pendiente

- La identidad representa una aproximación entre operadores y no garantiza equivalencia con una persona física.
- La comparación exacta de identidades entre features y etiquetas debe realizarse antes de construir el conjunto final de entrenamiento.
- El corte C no dispone de una etiqueta de abandono validada.
- La auditoría temporal debe ampliarse si se requiere demostrar aislamiento de fuentes de identidad o CDC frente a modificaciones futuras.
- El modelo original `feat_usuario_movilidad.sql` se conserva sin modificaciones.
