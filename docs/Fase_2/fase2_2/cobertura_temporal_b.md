# Certificación de cobertura temporal de fuentes para B

## Estado y alcance

Se prepara `scripts/modelado/auditar_cobertura_fuentes_b.py`, separado de los
exportadores y del evaluador. **No se ejecutó la auditoría ni se consultó PostgreSQL.**
No se leyó ningún dataset, etiqueta, autorización o bitácora B; tampoco se inspeccionaron
filas de fuentes. Se revisaron código/esquemas y el formato de manifiestos definido
por las ingestas. No se afirma que existan manifiestos válidos en una ejecución real.

Esta preparación continúa [auditoria_pre_test_b.md](auditoria_pre_test_b.md) y
[plan_cierre_pre_test_b.md](plan_cierre_pre_test_b.md). El usuario confirma 10/10
pruebas sintéticas CDC aprobadas y corrección publicada en aede6ba; ese resultado
no certifica cobertura temporal. No se modifica modelo L1 C=1, umbral 1/3,
política e9e0ed5, su SHA256, evaluador, exportador ni Fase 1.

**Completitud: PENDIENTE.** Este bloque no autoriza lecturas reales. La existencia
de un auditor no acredita el contenido, integridad o cobertura de las fuentes.

## Fuentes y límites exactos

El abandono se determina por ausencia de eventos válidos en **[2026-07-31 00:00:00,
2026-08-30 00:00:00)**, aplicando las expresiones temporales actuales de SQL_EVENTOS.
La elegibilidad/features requieren además **[2026-07-03, 2026-07-31)** y el historial
CDC anterior al corte. Los catálogos e identidad son dependencias, no eventos de abandono.

| Fuente y vía | Staging → Silver | Reloj usado para la ventana | Cobertura necesaria |
|---|---|---|---|
| Transmetro / Streaming | `staging.transmetro_validaciones` → `silver.silver_transmetro_validaciones` | `fecha_hora_local AT TIME ZONE 'UTC'`; parseo Staging con sesión UTC como A | Ventanas previa y posterior completas; deduplicación por validation_id. |
| Transurbano / Batch | `staging.transurbano_transacciones` → `silver.silver_transurbano_transacciones` | `fecha_hora_local`, timestamp de fecha/hora origen | Mismos límites en ese reloj; explicar parada nula y fecha posterior a ingestion_date. |
| MetroRiel / Batch | `staging.metroriel_viajes` → `silver.silver_metroriel_viajes` | `entry_ts` | Mismos límites de entrada; disponibilidad de salida/duración para decidir validez, incluso en viajes cercanos al final. |
| Aerómetro / Streaming | `staging.aerometro_boardings` → `silver.silver_aerometro_boardings` | `fecha_hora_local` calculada desde timestamp_utc en America/Guatemala | Posterior UTC equivalente: **[2026-07-31 06:00Z, 2026-08-30 06:00Z)**; previa: [2026-07-03 06:00Z, 2026-07-31 06:00Z). |
| Padrón / CDC | `staging.cdc_padron_usuarios` | `commit_ts < 2026-07-31`, desempate por seq | Historia/estado inicial suficiente hasta el corte, no solo CDC de la ventana posterior. |

**No sustituir estos relojes por un único recorte UTC global.** En particular,
`int_aerometro_normalizado.sql` convierte explícitamente a hora Guatemala. La sesión
UTC no deshace esa conversión. Si el origen solo acredita hasta 2026-08-30 00:00Z,
no acredita por sí mismo las últimas seis horas de la ventana local de Aerómetro.
No se inspeccionaron fechas reales y no se afirma que exista esa carencia: debe probarse.
Tampoco se cambia ahora la convención histórica de A.

Referencias: `scripts/etiquetado/calcular_etiquetas.py` (SQL_EVENTOS y preparar_fechas);
`dbt_red_metropolitana/models/silver/int_aerometro_normalizado.sql`;
`silver_transmetro_validaciones.sql`, `silver_transurbano_transacciones.sql`,
`silver_metroriel_viajes.sql`, `silver_aerometro_boardings.sql` e intermedios de calidad.

## Criterios de aceptación verificables

| Control | Evidencia exigida para cerrar | Estado de esta preparación |
|---|---|---|
| Cierre completo de cada origen | Certificado responsable/versionado con límites de eventos en su reloj, extracción completa y ausencia de llegadas tardías pendientes. Incluir hashes de la versión original y límites anteriores. | PENDIENTE; bloquea certificación. |
| Batch y CDC | Manifiestos `bronze/_manifests/<fuente>-*.json`: source/source_file, source_file_sha256, records, expected_records, count_matches, lista de Parquet y fecha de ingesta. Hash y conteos vinculados al origen acreditado. | PENDIENTE; el script comprobará formato, consistencia y conteo de metadatos Parquet. |
| Streaming | Certificación de publicación íntegra del origen, hashes/versión, particiones y rangos esperados. Reconciliar publicación → Bronze → Staging, sin duplicados ni pérdidas sin explicación. | PENDIENTE; offsets Staging solo son diagnóstico. |
| Reconciliación entre capas | Totales origen/manifestados/Parquet/Staging y conteos diarios Staging−rechazados=Silver; explicar cada pérdida, duplicado, rechazo y eventual multiplicación por joins de catálogos. | PENDIENTE; parte automatizada por el auditor. |
| Días sin eventos | Calendario completo de 28+30 días por operador y prueba del origen que justifique cada cero real; distinguirlo de extracción o ingesta faltante. | PENDIENTE; cero no se aprueba ni se rechaza automáticamente. |
| Rechazos | Causas, volumen, procedencia y efecto temporal revisados, sin leer ni publicar etiquetas. Rechazos de Transurbano se cuentan por unión de reglas para evitar doble conteo. | PENDIENTE; sin umbral arbitrario de tolerancia. |
| CDC y dependencias | Dominio de op normalizado para B, secuencias y fechas consistentes, snapshot inicial suficiente; catálogos e identidad coherentes y misma clave/procedencia. | PENDIENTE; checks agregados no acreditan historia inicial. |
| Procedencia y snapshot | Commit, huellas de código/manifiestos, instante de snapshot DB, versión de ingesta y vínculo con archivos inmutables; aprobación de responsable identificado. | PENDIENTE; DB y filesystem no comparten transacción. |

`MAX(fecha)`, `MIN(fecha)`, número total esperado, watermark Kafka, presencia de
todos los días o `count_matches=true` no prueban por separado completitud del origen.
Los conteos esperados escritos en scripts de Fase 1 no son una certificación temporal.
No fijar conteos de positivos/negativos B ni utilizar prevalencia para reconciliar fuentes.

Los formatos de manifiestos proceden de `scripts/batch/cargar_batch_bronze.py` y
`scripts/cdc/cargar_cdc_bronze.py`; Streaming conserva topic/partition/offset en
`scripts/streaming/consumidor_bronze.py`. Las columnas de trazabilidad Staging se
definen en `scripts/staging/cargar_operaciones_staging.py` y `cargar_cdc_staging.py`.
No se ejecutan estos cargadores ni validadores históricos: pueden reconstruir capas.

## Auditor preparado: acceso y salidas

Importar el nuevo módulo o pedir `--help` solo usa librerías estándar y argparse:
no importa psycopg/pyarrow, carga .env, lee manifiestos ni conecta. La ejecución real
exige **ambos** `--auditar-fuentes` y la frase `AUTORIZO_AUDITORIA_FUENTES_B`, además
de una instrucción posterior expresa del usuario. Los flags previenen accidentes;
no autentican consentimiento humano ni sustituyen esa instrucción.

Después de autorización, antes de acceder a fuentes crea una carpeta nueva por
fecha/UUID y una bitácora sincronizada en
`docs/reportes_fase2_2/cobertura_fuentes/<ejecucion>/`. No sobrescribe ejecuciones.
Usa PostgreSQL con snapshot `REPEATABLE READ READ ONLY`, sesión UTC y timeout por
consulta; no crea tablas ni modifica datos. Todas las consultas devuelven agregados.

No accede a `abandono`, etiquetas, datasets de A/B, probabilidades, features por
persona, identificadores de usuarios ni funciones de entrenamiento/exportación.
El servidor agrega sobre fuentes operativas, pero Python no recibe filas individuales.
Los metadatos Parquet se leen sin cargar columnas, raw_value ni filas; no se recalculan
hashes leyendo CSV/Parquet de individuos. Los SHA de origen son **declarados**, no
verificados contra bytes de datos por este auditor. Esto mantiene pendiente su
autenticidad y correspondencia con el origen certificado.

Entregables futuros, exclusivamente de integridad/cobertura:

- `cobertura_diaria.csv`: calendario explícito por operador y ventana, conteos Staging,
  rechazados y Silver, diferencia y marca de día sin eventos. No son conteos de abandono.
- `fechas_nulas.csv`, `filas_staging.csv`: problemas temporales y totales operativos.
- `offsets_streaming.csv`: rangos/duplicados/huecos por partición, sin usuarios.
- `filas_batch.csv`: integridad de numeración de filas, sin contenidos.
- `manifiestos.csv`: huellas JSON/declaradas y coincidencia de filas Parquet por manifiesto.
- `resultado.json`: estado, bloqueos, pendientes, commit, SHA del auditor e integridad
  CDC agregada anterior al corte (no se extraen tarjetas).
- `bitacora.jsonl`: antes de acceso, finalización o tipo de fallo; no errores SQL con datos.

Varias versiones de manifiesto se marcan pendientes de selección de snapshot y no
se suman indiscriminadamente. Rutas Parquet deben quedar dentro de la carpeta Bronze
de la fuente. La validación de metadatos no demuestra que dos archivos con igual
conteo tengan el mismo contenido.

## Límites y decisión de certificación

El resultado automático será **BLOQUEANTE** ante discrepancias técnicas detectadas
o **PENDIENTE_CERTIFICACION_ORIGEN** en caso contrario. Siempre guarda
`certificado=false`: nunca cierra automáticamente el requisito ni habilita exportación
o evaluación. Un auditor que aún carece de evidencia upstream no puede emitir una
certificación positiva solo porque sus agregados cuadren.

La reconciliación diaria reproduce las reglas operativas relevantes sin ejecutar dbt.
No recompila todos sus casts/joins: errores de parseo, fuentes modificadas o catálogos
duplicados pueden impedirla o generar diferencias que deben investigarse. Los modelos
intermedios dbt son ephemeral y no se consultan como tablas físicas. Las reglas de
duplicados se calculan antes de filtrar la ventana, como en dbt.

Los checks de numeración/offsets se aplican al snapshot completo Staging y pueden
señalar huecos que tengan una explicación legítima; no se descartan sin reconciliarlos
con origen/retención/publicación. CDC previo al corte no tiene por qué comenzar en
una fecha universal: debe acreditarse un estado inicial más todo el historial necesario.

La carpeta de reportes es agregada; custodiar el certificado upstream y cualquier
metadato operativo sensible en un registro privado. No publicar archivos fuente,
usuarios, claves, contraseñas o datos individuales. El responsable deberá documentar
aceptación de cada criterio, snapshot y evidencias; si falta cualquier prueba de
completitud, mantener PENDIENTE y detener el flujo antes de exportar B.

## Verificaciones seguras y comando futuro

Desde la raíz, solo sintaxis y ayuda; no consultan datos:

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts/modelado/auditar_cobertura_fuentes_b.py
.\.venv\Scripts\python.exe scripts/modelado/auditar_cobertura_fuentes_b.py --help
```

Se intentaron ambos comandos desde Codex en esta preparación: el Python base de
WindowsApps de `.venv` no pudo iniciarse (salida 1). Sintaxis y ayuda quedan
**PENDIENTES** de comprobar en PowerShell operativo; no se afirma que hayan pasado.
Ninguno llegó a ejecutar el script ni consultas. La inspección estática de la ruta
`--help` sí confirma que termina antes de acceder a fuentes.

Dependencias operativas posteriores: psycopg, python-dotenv, pyarrow, `.env` ya
configurado, acceso a tablas Staging/Silver y metadatos Bronze. No mostrar credenciales.

**Comando futuro, NO autorizado ni ejecutado en este bloque:**

```powershell
.\.venv\Scripts\python.exe scripts/modelado/auditar_cobertura_fuentes_b.py --auditar-fuentes --confirmacion AUTORIZO_AUDITORIA_FUENTES_B
```

Ese comando sí consulta fuentes y lee manifiestos/metadatos. No debe confundirse
con `--help`, una exportación, una autorización del test único o una certificación final.
Primero revisar código/criterios; luego solicitar la instrucción explícita para ejecutar
solo esta auditoría de fuentes. Exportación y test conservarán sus autorizaciones separadas.
