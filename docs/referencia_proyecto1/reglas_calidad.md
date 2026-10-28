# Reglas de calidad de datos - Capa Silver

Las reglas se definieron antes de implementar los modelos de calidad en dbt.

Los registros que incumplan una regla no serán eliminados.
Se enviarán a una tabla de cuarentena conservando el dato original
y el motivo del rechazo.

## 1. Transmetro - Duplicados de torniquete

### Regla
`validacion_id` debe identificar una validación única.

Si existen varias filas con el mismo `validacion_id`, se conservará
una sola como registro válido y las repeticiones adicionales serán
enviadas a cuarentena.

### Motivo de rechazo
`DUPLICADO_TORNIQUETE`

---

## 2. Transurbano - Código de parada nulo

### Regla
Una transacción debe contener un `cod_parada` válido.

Si `cod_parada` viene vacío o nulo, el registro no puede relacionarse
con una parada ni con una zona conformada.

### Motivo de rechazo
`COD_PARADA_NULO`

---

## 3. Transurbano - Fecha futura

### Regla
La fecha de una transacción no puede ser posterior a la fecha en que
el registro fue ingerido.

La comparación se realizará contra `ingestion_date`, para que la regla
sea reproducible y no dependa de la fecha en que se vuelva a ejecutar
el proyecto.

### Motivo de rechazo
`FECHA_FUTURA`

---

## 4. MetroRiel - Viaje sin salida

### Regla
MetroRiel representa un viaje completo, por lo que debe existir
información de salida.

Se considerará inválido un registro cuando `exit_station`,
`exit_ts` o `duration_s` sea nulo.

### Motivo de rechazo
`VIAJE_SIN_SALIDA`

---

## 5. Aerómetro

El enunciado no especifica una anomalía intencional de calidad para
Aerómetro.

Sus registros serán normalizados en Silver, especialmente la
conversión del timestamp UTC a hora local de Guatemala, pero no se
inventarán reglas de rechazo adicionales.

---

# Tratamiento de registros con más de un problema

Un registro puede incumplir más de una regla.

La tabla de cuarentena conservará una sola copia del registro y
registrará todos los motivos encontrados.

Para las métricas de calidad, cada regla se contará de forma
independiente.

Por ejemplo, una transacción de Transurbano que tenga simultáneamente
un código de parada nulo y una fecha futura contará:

- una vez para `COD_PARADA_NULO`;
- una vez para `FECHA_FUTURA`;
- pero seguirá representando un solo registro en cuarentena.

# Principio general

Silver contendrá únicamente registros válidos para análisis.

Cuarentena conservará los registros rechazados junto con:

- sistema de origen;
- identificador del registro;
- dato crudo;
- motivo de rechazo;
- fecha de ingesta.

Los registros rechazados nunca serán descartados en silencio.