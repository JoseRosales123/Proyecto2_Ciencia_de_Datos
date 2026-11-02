
# Apartado 1.2 — Etiqueta, población y unidad

## 1. Objetivo

Definir la población elegible y la etiqueta de abandono de usuarios de la Red Metropolitana de Transporte, utilizando datos validados de la capa Silver.

Se evalúan dos cortes temporales para comparar el abandono de usuarios y el efecto de seleccionar diferentes unidades de análisis.

## 2. Fechas de corte

| Corte | Fecha | Ventana previa | Ventana posterior |
|---|---|---|---|
| A | 2026-07-01 | 2026-06-03 al 2026-06-30 | 2026-07-01 al 2026-07-30 |
| B | 2026-07-31 | 2026-07-03 al 2026-07-30 | 2026-07-31 al 2026-08-29 |

Las ventanas se implementan mediante intervalos semiabiertos: el inicio está incluido y el final excluido.

## 3. Definición de población elegible

Una unidad es elegible cuando:

1. Registra al menos dos abordajes válidos durante los 28 días anteriores a la fecha de corte.
2. Cumple la política de elegibilidad establecida para las bajas del padrón CDC.

Se utilizan los eventos válidos de Transmetro, Transurbano, MetroRiel y Aerómetro.

## 4. Definición de etiqueta

La variable objetivo es `abandono`.

- `abandono = 1`: no registra abordajes válidos en los 30 días posteriores al corte.
- `abandono = 0`: registra al menos un abordaje válido durante ese período.

Esta etiqueta representa ausencia de uso observada durante la ventana definida, no una cancelación permanente del servicio.

## 5. Unidad de análisis

Se compararon dos alternativas:

### PERSONA aproximada

Agrupa los identificadores utilizando `usuario_seudonimo`, obtenido de la integración de identidades de Silver.

Esta es la unidad principal seleccionada para el proyecto porque permite estudiar el abandono de la red completa, en lugar del abandono de un operador individual.

La integración es aproximada y no constituye una identificación personal verificada.

### TARJETA por operador

Utiliza la combinación de `sistema` e `identificador` para distinguir tarjetas e identificadores originales entre operadores.

Esta alternativa se conserva como análisis de sensibilidad.

## 6. Costo de integración

| Indicador | Resultado |
|---|---:|
| Identificadores originales | 130,322 |
| Identidades aproximadas | 87,102 |
| Identidades multisistema | 35,691 |
| Reducción de unidades | 43,220 |
| Reducción porcentual | 33.16% |

La integración reduce el número de unidades, aunque puede introducir errores de asociación entre identificadores que no necesariamente pertenecen a una misma persona.

## 7. Tratamiento del CDC

El historial CDC se utiliza para identificar tarjetas de Transmetro cuya última operación anterior al corte fue `DELETE`.

La comparación aplica las siguientes reglas:

- Una tarjeta Transmetro eliminada antes del corte no es elegible individualmente.
- Una persona aproximada permanece habilitada si conserva al menos un identificador asociado que no esté eliminado.
- Una tarjeta sin historial CDC no se considera automáticamente eliminada; su estado CDC es desconocido.

Se identificaron 41,344 tarjetas de Transmetro, de las cuales 25,424 tienen historial CDC y 15,920 no lo tienen.

Esta política constituye una decisión analítica y debe interpretarse considerando las limitaciones de la integración aproximada.

## 8. Resultados de los cortes

| Corte | Unidad | Población elegible | Positivos | Negativos | Tasa positiva |
|---|---|---:|---:|---:|---:|
| A | PERSONA_APROX | 60,664 | 8,110 | 52,554 | 13.3687% |
| A | TARJETA_OPERADOR | 77,411 | 11,211 | 66,200 | 14.4824% |
| B | PERSONA_APROX | 59,126 | 7,261 | 51,865 | 12.2806% |
| B | TARJETA_OPERADOR | 76,378 | 10,312 | 66,066 | 13.5013% |

Los resultados muestran que la elección de la unidad modifica tanto la población elegible como la tasa de abandono.

## 9. Validación temporal

Los datos válidos de Silver cubren del 1 de junio al 29 de agosto de 2026.

Las ventanas posteriores de ambos cortes se encuentran dentro de ese período de observación.

En Transmetro, los valores horarios almacenados en PostgreSQL y representados en UTC coinciden con los valores del CSV original.

Sin embargo, como el archivo original no declara explícitamente una zona horaria, no es posible asegurar que los valores originales correspondan realmente a UTC. Para mantener consistencia con el origen se utiliza la misma representación horaria en el etiquetado.

## 10. Implementación

Script principal:

`scripts/etiquetado/calcular_etiquetas.py`

Ejecución:

```powershell
python .\scripts\etiquetado\calcular_etiquetas.py
```

Reportes generados:

- `docs/reportes_fase1_2/comparacion_identidades.csv`
- `docs/reportes_fase1_2/comparacion_unidades_cortes.csv`

La implementación utiliza consultas sobre Silver y Staging, así como tablas temporales de PostgreSQL. No modifica las tablas permanentes del pipeline.

## 11. Limitaciones

- La identidad PERSONA es aproximada y puede producir asociaciones incorrectas.
- La cobertura del CDC en Transmetro es parcial.
- La ausencia de actividad representa abandono operativo dentro de 30 días, no abandono definitivo.
- Las fechas de origen no declaran explícitamente una zona horaria.
- La regla de elegibilidad por CDC representa una política analítica y debe mantenerse consistente durante el modelado y la evaluación.

## 12. Conclusión

Se selecciona PERSONA aproximada seudonimizada como unidad principal para analizar el abandono de usuarios de toda la red metropolitana.

La comparación con TARJETA por operador permite cuantificar la sensibilidad de los resultados a la integración de identidades.

El apartado proporciona dos cortes temporales, una definición reproducible de población y etiqueta, y resultados respaldados por consultas sobre datos Silver validados.
