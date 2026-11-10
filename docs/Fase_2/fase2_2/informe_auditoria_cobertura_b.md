# Informe de auditoría agregada de cobertura de fuentes — B

## Dictamen y alcance

La ejecución analizada terminó sin bloqueos técnicos automáticos y con consistencia
interna en los controles agregados realizados. **La completitud del origen sigue sin
certificarse** y no existe evidencia suficiente de cierre de llegadas tardías.

Se conserva exactamente el estado del resultado:

```json
{
  "estado": "PENDIENTE_CERTIFICACION_ORIGEN",
  "certificado": false
}
```

Este informe no concede autorización para exportar o evaluar B. Se redactó leyendo
exclusivamente los ocho reportes agregados de la carpeta indicada y
[cobertura_temporal_b.md](cobertura_temporal_b.md). No se consultó PostgreSQL,
no se ejecutó otra auditoría y no se abrieron datasets, etiquetas o predicciones
individuales. No se modificó `resultado.json` ni otro reporte. Según el estado
comunicado por el usuario, el dataset B no se ha exportado ni evaluado; los agregados
de fuentes no permiten comprobar por sí solos el historial de ejecución del test.

## Procedencia de la ejecución

Carpeta: `docs/reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/`.

| Metadato registrado | Valor |
|---|---|
| Commit informado | `aede6baebe3d2b766e90d73bd243dfabd4867650` |
| Snapshot de base de datos, UTC | `2026-11-10T04:06:49.332515+00:00` |
| SHA256 del auditor ejecutado | `af5c8e2f580764b93d35d9033a7305dd01100283b9aa6d52817070d3a57b74b0` |
| Evento anterior a lectura de fuentes, UTC | `2026-11-10T04:06:49.244606+00:00` |
| Evento FINALIZADO, UTC | `2026-11-10T04:06:56.151923+00:00` |
| Bloqueos técnicos automáticos | 0 |
| Estado final / certificado | `PENDIENTE_CERTIFICACION_ORIGEN` / `false` |

Fuentes: [resultado.json](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/resultado.json)
y [bitacora.jsonl](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/bitacora.jsonl).
El commit y la huella son valores registrados, no una verificación adicional de
autoría, árbol limpio o pertenencia del script a ese commit. La huella permite
identificar sus bytes; el vínculo completo entre código aprobado y ejecución debe
formar parte de la aceptación documental pendiente.

## Ventanas y significado de la cobertura temporal

| Ventana | Inicio incluido | Fin excluido | Días por operador |
|---|---|---|---:|
| Previa: features y elegibilidad | 2026-07-03 00:00:00 | 2026-07-31 00:00:00 | 28 |
| Posterior: actividad para abandono | 2026-07-31 00:00:00 | 2026-08-30 00:00:00 | 30 |

Se revisaron 58 fechas distintas por operador: 232 combinaciones operador/día,
sin fechas ausentes en el calendario agregado ni días con cero eventos Silver.
Las fechas diarias de la ventana previa van del 3 al 30 de julio; las posteriores,
del 31 de julio al 29 de agosto, ambos extremos diarios incluidos.

Los límites deben interpretarse según el reloj empleado por cada fuente, descrito
en la documentación de cobertura. En particular, Aerómetro usa hora
`America/Guatemala`; su ventana posterior equivale a
**[2026-07-31 06:00 UTC, 2026-08-30 06:00 UTC)**. La previa equivale a
[2026-07-03 06:00 UTC, 2026-07-31 06:00 UTC). Tener eventos el 29 de agosto
no acredita las últimas horas del día ni el cierre del origen.

Transmetro se audita con la conversión UTC definida; Transurbano con su fecha/hora
normalizada y MetroRiel con `entry_ts`. No se redefine aquí ninguna convención
histórica. CDC necesita historia/estado inicial suficiente **anterior a 2026-07-31**,
no simplemente cobertura de los 30 días posteriores.

## Resultados diarios reconciliados

Totales obtenidos sumando únicamente las filas de cada operador/ventana del
[CSV de cobertura diaria](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/cobertura_diaria.csv).
En las ocho combinaciones, cada diferencia diaria `Staging − rechazados − Silver`
es cero; no se trata solo de una compensación entre diferencias positivas y negativas.

| Operador | Ventana | Días | Staging | Rechazados por regla | Silver | Días con diferencia | Días sin eventos Silver |
|---|---|---:|---:|---:|---:|---:|---:|
| Transmetro | Previa | 28 | 219,138 | 621 | 218,517 | 0 | 0 |
| Transmetro | Posterior | 30 | 244,502 | 742 | 243,760 | 0 | 0 |
| Transurbano | Previa | 28 | 503,561 | 2,393 | 501,168 | 0 | 0 |
| Transurbano | Posterior | 30 | 550,985 | 2,728 | 548,257 | 0 | 0 |
| MetroRiel | Previa | 28 | 182,467 | 2,201 | 180,266 | 0 | 0 |
| MetroRiel | Posterior | 30 | 200,710 | 2,416 | 198,294 | 0 | 0 |
| Aerómetro | Previa | 28 | 119,708 | 0 | 119,708 | 0 | 0 |
| Aerómetro | Posterior | 30 | 130,782 | 0 | 130,782 | 0 | 0 |

Reglas registradas: duplicados de `validation_id` en Transmetro; unión de parada
nula o fecha futura en Transurbano; viaje sin salida en MetroRiel; ninguna exclusión
en el modelo Silver de Aerómetro. Los rechazos de Transurbano no se suman por
separado entre causas que podrían superponerse.

La coincidencia comprueba la reconciliación bajo esas reglas; no prueba que los
rechazos sean irrelevantes para medir abandono ni que el origen no haya omitido eventos.
Su justificación e impacto de cobertura siguen requiriendo revisión documental.

## Integridad Staging, Batch y Streaming

Los totales Staging siguientes corresponden al snapshot completo de las fuentes;
no deben confundirse con los totales de las ventanas de la tabla anterior.

| Operador | Filas Staging completas | Fechas nulas |
|---|---:|---:|
| Transmetro | 713,786 | 0 |
| Transurbano | 1,635,788 | 0 |
| MetroRiel | 590,844 | 0 |
| Aerómetro | 387,053 | 0 |

Fuentes: [filas_staging.csv](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/filas_staging.csv)
y [fechas_nulas.csv](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/fechas_nulas.csv).

| Batch | Filas | Números de fila distintos | Rango |
|---|---:|---:|---|
| Transurbano | 1,635,788 | 1,635,788 | 1..1,635,788 |
| MetroRiel | 590,844 | 590,844 | 1..590,844 |

La numeración observada es continua y sin duplicados en ambos casos, según
[filas_batch.csv](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/filas_batch.csv).
Esto comprueba integridad del rango cargado; no acredita que el archivo recibido
contenga todo lo que produjo su sistema de origen.

| Streaming | Partición | Filas / offsets distintos | Rango observado | Offsets nulos | Huecos |
|---|---:|---:|---|---:|---:|
| Transmetro | 0 | 713,786 / 713,786 | 0..713,785 | 0 | 0 |
| Aerómetro | 0 | 387,053 / 387,053 | 0..387,052 | 0 | 0 |

Fuente: [offsets_streaming.csv](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/offsets_streaming.csv).
No hay duplicados ni huecos internos en los rangos observados. Falta demostrar que
esos rangos representan la publicación completa del origen, sin omisiones antes
del productor, otras particiones pendientes o llegadas posteriores al snapshot.

## Manifiestos y CDC

| Manifiesto de fuente | Filas declaradas | Filas de metadatos Parquet | Estado del control técnico |
|---|---:|---:|---|
| Transurbano | 1,635,788 | 1,635,788 | APROBADO |
| MetroRiel | 590,844 | 590,844 | APROBADO |
| CDC padrón | 77,636 | 77,636 | APROBADO |

[manifiestos.csv](../../reportes_fase2_2/cobertura_fuentes/20261110T040649Z_eec3c7f64818/manifiestos.csv)
registra para cada uno SHA256 del manifiesto y SHA256 **declarado** del origen.
APROBADO se limita al control técnico definido; no es una certificación independiente
del contenido original. No se recalcularon hashes leyendo archivos individuales en
esta auditoría documental. Los totales completos Staging de Transurbano y MetroRiel
coinciden también con esos conteos, pero la identidad de contenido/snapshot y su
trazabilidad entre capas no quedan demostradas solo por igualdad numérica.

| CDC anterior al corte | Resultado |
|---|---:|
| Operaciones | 52,320 |
| Secuencias distintas | 52,320 |
| Rango de secuencias | 1..52,320 |
| Primer commit observado | 2026-06-01 00:02:00 |
| Último commit observado | 2026-07-30 23:58:00 |
| Operaciones fuera de dominio | 0 |

Estos datos proceden de `cdc_agregado` en `resultado.json`. Las 52,320 operaciones
son el subconjunto **anterior al corte**; las 77,636 filas del manifiesto son el total
de la ingesta CDC. No corresponde exigir igualdad entre ambos alcances ni interpretar
su diferencia como pérdida. La unicidad, continuidad observada y dominio válido no
certifican que exista un estado inicial suficiente para todas las identidades ni
que el origen haya entregado todos sus cambios anteriores al corte.

## Integridad verificada frente a completitud no certificada

| Dimensión | Conclusión permitida | Conclusión que no se puede afirmar |
|---|---|---|
| Calendario y reconciliación | 58 días por operador, actividad Silver todos los días y diferencias diarias cero bajo las reglas auditadas. | Que se recibió cada evento originado, incluidas las últimas horas de cada ventana. |
| Secuencias, offsets y filas | Rangos observados continuos y sin duplicados en los controles presentados. | Que esos rangos sean los rangos finales y completos de los productores. |
| Manifiestos y Parquet | Conteos declarados y de metadatos coincidentes; huellas registradas. | Autenticidad del origen o igualdad del contenido entre capas solo por sus conteos. |
| CDC | Integridad agregada del subconjunto previo observado y cero operaciones fuera de dominio. | Completitud del historial, disponibilidad del estado inicial o ausencia de cambios tardíos. |
| Bloqueos automáticos | Ninguno detectado por esta ejecución. | Aprobación del origen, certificación final o permiso para exportar/evaluar B. |

El snapshot de noviembre es posterior a la ventana de eventos, pero ese hecho no
demuestra por sí solo que ya no puedan llegar correcciones, eventos demorados o
reprocesamientos. Presencia de actividad diaria y fecha máxima no bastan.

## Evidencias independientes aún necesarias

No se presupone que los siguientes documentos existan. Son requisitos concretos
de cierre, no certificados emitidos por este informe.

| Área | Evidencia solicitada | Criterio de aceptación y responsable propuesto |
|---|---|---|
| Batch: Transurbano y MetroRiel | Acta/manifiesto del responsable de origen con versión o snapshot de extracción, límites temporales en su reloj, número total de registros, SHA256 del archivo entregado y constancia de extracción completa. | Responsable del origen y custodio de ingesta concilian esa versión con los hashes declarados, inventario Parquet y numeración Staging; documentan diferencias sin exponer individuos. |
| Streaming: ambos operadores | Registro de publicación del productor con versión/hash del origen, identificador de ejecución/topic, inventario completo de particiones, rangos finales exclusivos, mensajes enviados y errores/reintentos. | Responsable del productor acredita que todos los eventos del origen cerrado se publicaron; ingesta vincula los rangos finales con Bronze/Staging, no solo con el mínimo/máximo observado. |
| CDC | Snapshot inicial o evidencia de reconstrucción suficiente, posición inicial/final certificada del log, secuencias/transacciones esperadas y política de interpretación temporal; versión y hash de extracción. | Responsable CDC acredita ausencia de cambios omitidos previos al corte y relación de ese subconjunto con la ingesta completa de 77,636 filas. Justifica identidad no resuelta, si corresponde, sin publicar tarjetas. |
| Llegadas tardías y correcciones | Política de tardanza respaldada por cada origen; registro de cierre del periodo, colas pendientes, errores/reintentos y reprocesamientos/correcciones resueltos; watermark de evento acompañado por garantía del origen. | Cada responsable certifica el cierre hasta el límite requerido, incluido 2026-08-30 06:00 UTC para Aerómetro. No basta esperar tiempo ni observar que una cola está vacía si el origen no ha cerrado. |
| Rechazos y calidad | Informe de calidad por regla y ventana, con causa, procedencia y aceptación de exclusiones; para MetroRiel, suficiencia de información de salida de viajes cercanos al límite. | Responsable de calidad documenta por qué las exclusiones son coherentes con la definición de evento válido y si existen incidentes pendientes capaces de ocultar actividad. Reconciliación cero no sustituye esta aceptación. |
| Catálogos e identidad | Versiones/snapshots aprobados de catálogos e identidad, constancia privada de misma clave/procedencia de seudonimización y limitación de identidad aproximada. | Custodio técnico acredita consistencia con las capas auditadas, sin divulgar claves ni identificadores. |
| Trazabilidad de aceptación | Acta que vincule certificado upstream, manifiestos exactos, snapshot DB, código/huella ejecutados y revisión por responsable identificado; inventario inmutable de evidencias. | Revisor confirma correspondencia entre DB y filesystem y deja aceptación fechada. Las huellas declaradas requieren una cadena de custodia confiable, no su mera presencia. |

Si es necesaria una nueva comprobación sobre fuentes o metadatos reales para obtener
estas evidencias, deberá autorizarse y delimitarse en otro bloque. Este informe no
ejecuta ni propone como ya realizadas esas comprobaciones. No se requieren etiquetas
de abandono para ninguno de estos cierres.

## Conclusión y próximos controles

**Integridad técnica comprobada dentro del alcance de la auditoría agregada:** cero
bloqueos automáticos, fechas nulas o diferencias diarias; numeraciones y offsets
observados consistentes; manifiestos y conteos Parquet reconciliados.

**Completitud del origen y cierre de tardíos: PENDIENTES.** También permanece pendiente
la aceptación documental de rechazos, estado inicial/historial CDC, catálogos/identidad
y vínculo entre snapshots de origen, archivos y base. No hay días sin actividad que
justificar en esta ejecución, pero eso no elimina los otros requisitos del resultado.

Se mantiene `certificado=false`. No corresponde aprobar cobertura definitiva,
exportar B ni habilitar el test único basándose exclusivamente en estos reportes.
El modelo L1 C=1, umbral exacto 1/3, política, SHA256, exportador, evaluador y Fase 1
permanecen sin modificaciones durante esta redacción. No se hizo add, commit ni push.
