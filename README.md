
# Proyecto 2 — Ciencia de Datos
## Red Metropolitana de Transporte

Este proyecto desarrolla un pipeline de ingeniería y ciencia de datos para integrar información de Transmetro, Transurbano, MetroRiel y Aerómetro.

La arquitectura utiliza ingestas Batch, Streaming y CDC, almacenamiento Bronze en Parquet, PostgreSQL, Prefect y dbt para la preparación de datos y su posterior análisis.

---

# Fase 1 — Preparación y análisis de datos

## 1.1. Datos nuevos desde cero

### Objetivo

Reconstruir el pipeline de la Red Metropolitana de Transporte a partir de nueve fuentes de datos, utilizando ingestas Batch, Streaming con Apache Kafka y CDC, almacenamiento Bronze en Parquet, PostgreSQL para Staging, Prefect para orquestación y dbt para las transformaciones Silver y Gold.

### Requisitos previos

- Python con las dependencias del proyecto instaladas y el entorno virtual activado.
- Docker Desktop y Docker Compose.
- Los nueve archivos originales en `datos_red/`.
- El archivo `.env` configurado para los servicios exclusivos del Proyecto 2.
- El perfil dbt disponible en `dbt_red_metropolitana/config/profiles.yml`.

### Ejecución completa desde cero

Desde la raíz del repositorio:

```powershell
python .\scripts\orquestacion\ejecutar_desde_cero.py --desde-cero --confirmar-borrado-p2
```

El programa valida la configuración Docker Compose y los recursos asociados al Proyecto 2 antes de reinicializarlos. Solicita escribir `REINICIAR PROYECTO 2` como confirmación adicional.

**Advertencia:** esta operación elimina los datos generados en Bronze y los volúmenes Kafka/PostgreSQL del Proyecto 2. No elimina los nueve archivos originales ni debe utilizarse con recursos compartidos de otros proyectos.

Para ejecutar el pipeline reutilizando las cargas existentes:

```powershell
python .\scripts\orquestacion\ejecutar_desde_cero.py
```

### Reconciliación de datos

| Fuente | Registros esperados | Registros cargados | Diferencia |
|---|---:|---:|---:|
| TM estaciones | 104 | 104 | 0 |
| TU paradas | 328 | 328 | 0 |
| MR estaciones | 22 | 22 | 0 |
| AM estaciones | 14 | 14 | 0 |
| Transmetro | 713,786 | 713,786 | 0 |
| Transurbano | 1,635,788 | 1,635,788 | 0 |
| MetroRiel | 590,844 | 590,844 | 0 |
| Aerómetro | 387,053 | 387,053 | 0 |
| CDC padrón | 77,636 | 77,636 | 0 |
| **Total** | **3,405,575** | **3,405,575** | **0** |

### Tiempos de ejecución

En la reconstrucción desde estado limpio, se observaron los siguientes tiempos:

| Etapa | Segundos |
|---|---:|
| Ingesta Batch | 4.03 |
| Ingesta CDC Bronze | 0.37 |
| Publicación Transmetro | 1.50 |
| Consumo Transmetro | 7.52 |
| Publicación Aerómetro | 0.96 |
| Consumo Aerómetro | 3.98 |
| Prefect: Staging, CDC y modelos dbt | 240.27 |

Los tiempos completos del coordinador se encuentran en `docs/reportes_fase1/tiempos_etapas.csv`.

Las duraciones internas de Prefect se registran por separado y no deben sumarse nuevamente a su duración total.

### Validación final

- Nueve fuentes reconciliadas sin diferencias.
- 3,405,575 registros preservados en Bronze.
- Integridad del contenido Streaming verificada.
- 25 modelos dbt ejecutados satisfactoriamente.
- 89 pruebas dbt aprobadas.
- Aplicación del CDC y generación de las capas Staging, Silver y Gold completadas.

### Evidencias

- `docs/reportes_fase1/reconciliacion_bronze.csv`
- `docs/reportes_fase1/reconciliacion_bronze.json`
- `docs/reportes_fase1/tiempos_etapas.csv`
- `docs/metricas_prefect/`
- `docs/evidencias/Fase_1/fase1_1/`

**Resultado:** ejecución integral satisfactoria desde el estado limpio de los datos generados del Proyecto 2, con las dependencias y fuentes originales previamente preparadas.

---

## 1.2. Etiqueta, población y unidad

### Objetivo

Construir una etiqueta de abandono para los usuarios de la Red Metropolitana, definiendo una población elegible, ventanas temporales de observación y una unidad de análisis consistente.

Se utilizaron las tablas Silver de los cuatro operadores y el historial CDC del padrón de usuarios.

### Definición de los cortes

Se establecieron dos fechas de corte:

| Corte | Fecha de corte | Ventana previa (28 días) | Ventana posterior (30 días) |
|---|---|---|---|
| A | 2026-07-01 | 03/06 al 30/06 | 01/07 al 30/07 |
| B | 2026-07-31 | 03/07 al 30/07 | 31/07 al 29/08 |

Las ventanas utilizan intervalos semiabiertos: el inicio está incluido y el final excluido.

### Población elegible

Se considera elegible una unidad cuando:

1. Registra al menos dos abordajes válidos durante los 28 días anteriores al corte.
2. Cumple la política de elegibilidad establecida para las eliminaciones del padrón CDC.

Se consideran los eventos válidos de Transmetro, Transurbano, MetroRiel y Aerómetro.

### Definición de la etiqueta

La variable objetivo se denomina `abandono`.

- **Etiqueta 1:** la unidad no registra abordajes válidos en los 30 días posteriores al corte.
- **Etiqueta 0:** la unidad registra al menos un abordaje válido durante ese período.

La etiqueta representa ausencia de actividad observada durante 30 días, no abandono permanente del sistema.

### Unidad de análisis seleccionada

Se compararon dos alternativas:

**PERSONA aproximada seudonimizada**

Se agrupan identificadores mediante `usuario_seudonimo`, obtenido de la integración aproximada de identidades disponible en Silver.

Se seleccionó como unidad principal porque el objetivo consiste en medir el abandono de la red de transporte en conjunto y no únicamente el abandono de un operador.

**TARJETA por operador**

Se utiliza la combinación de `sistema` e `identificador` para distinguir las tarjetas o identificadores de cada fuente.

Esta alternativa se conserva como análisis de sensibilidad para medir el efecto de la integración.

### Comparación global de identidades

| Indicador | Resultado |
|---|---:|
| Identificadores originales | 130,322 |
| Identidades aproximadas | 87,102 |
| Identidades multisistema | 35,691 |
| Reducción de unidades | 43,220 |
| Reducción porcentual | 33.16% |

La integración reduce el número de unidades analíticas, aunque las coincidencias numéricas no garantizan que todos los identificadores asociados pertenezcan a una misma persona.

### Tratamiento de eliminaciones CDC

El historial CDC permite identificar tarjetas de Transmetro cuya última operación antes de cada corte fue `DELETE`.

Se implementaron las siguientes reglas:

- Una tarjeta Transmetro eliminada no se considera elegible individualmente.
- Una persona aproximada puede permanecer habilitada cuando conserva al menos otro identificador no eliminado.
- Una tarjeta sin historial CDC no se clasifica automáticamente como eliminada. Su estado en CDC se considera desconocido.

La cobertura encontrada fue:

| Indicador | Cantidad |
|---|---:|
| Identificadores Transmetro | 41,344 |
| Con historial CDC | 25,424 |
| Sin historial CDC | 15,920 |
| Cobertura CDC | 61.49% |

### Resultados de las etiquetas

Se procesaron 3,223,167 eventos válidos de Silver, sin eventos pendientes de identificación seudonimizada.

| Corte | Unidad | Población elegible | Positivos | Negativos | Tasa positiva |
|---|---|---:|---:|---:|---:|
| A | PERSONA_APROX | 60,664 | 8,110 | 52,554 | 13.3687% |
| A | TARJETA_OPERADOR | 77,411 | 11,211 | 66,200 | 14.4824% |
| B | PERSONA_APROX | 59,126 | 7,261 | 51,865 | 12.2806% |
| B | TARJETA_OPERADOR | 76,378 | 10,312 | 66,066 | 13.5013% |

La población elegible y la tasa de abandono cambian según la unidad de análisis.

Por ese motivo, se utilizará PERSONA aproximada como unidad principal y TARJETA por operador como comparación metodológica.

### Validación temporal

Las fuentes Silver contienen registros desde el 1 de junio hasta el 29 de agosto de 2026.

Las ventanas posteriores de ambos cortes están comprendidas dentro de ese período.

Se compararon las fechas originales de Transmetro con sus valores almacenados en PostgreSQL. Los valores horarios coinciden al representarlos en UTC.

No obstante, el CSV original no declara explícitamente una zona horaria, por lo que la interpretación UTC se adopta como convención de procesamiento y no como una propiedad confirmada del origen.

### Ejecución del apartado 1.2

Desde la raíz del repositorio:

```powershell
python .\scripts\etiquetado\calcular_etiquetas.py
```

El script consulta Silver y el historial CDC de Staging, utiliza tablas temporales y genera reportes comparativos sin modificar las tablas permanentes del pipeline.

### Archivos generados

- `docs/reportes_fase1_2/resumen_etiquetas_cortes.csv`
- `docs/reportes_fase1_2/comparacion_identidades.csv`
- `docs/reportes_fase1_2/comparacion_unidades_cortes.csv`

El archivo `resumen_etiquetas_cortes.csv` corresponde al cálculo preliminar de PERSONA aproximada. Para la comparación final de unidades deben utilizarse los resultados de `comparacion_unidades_cortes.csv`.

### Documentación y evidencias

- `docs/Fase_1/fase1_2/documentacion_tecnica.md`
- `docs/evidencias/Fase_1/fase1_2/`
- `docs/reportes_fase1_2/`

### Limitaciones metodológicas

- La identidad PERSONA es aproximada y no representa una identificación personal confirmada.
- La cobertura del historial CDC es parcial.
- Una eliminación de tarjeta no implica necesariamente el abandono de toda la red.
- La ausencia de abordajes durante 30 días no demuestra abandono permanente.
- Las fechas de origen no contienen una zona horaria explícita.
- Los resultados dependen de las reglas de identidad, elegibilidad y observación implementadas.

**Resultado:** se construyeron etiquetas de abandono para dos cortes temporales, se cuantificó el efecto de utilizar PERSONA frente a TARJETA y se estableció una unidad principal para los análisis posteriores.
