# Plan de cierre de controles previos al test B

## Alcance y estados

Este plan continúa [auditoria_pre_test_b.md](auditoria_pre_test_b.md), sin repetirla
ni sustituir sus evidencias. Solo se revisaron las definiciones adicionales de ingesta
y los fragmentos necesarios de exportación, CDC y evaluación. No se ejecutó ninguno
de los comandos propuestos abajo, ninguna consulta, exportación, entrenamiento o
evaluación. No se abrió ningún archivo de datos, autorización o bitácora B.
Ese fue el alcance del bloque de planificación original. En la actualización CDC
posterior se autorizó e implementó la variante local B y se prepararon pruebas
sintéticas; su ejecución se informa por separado, sin acceder a datos reales.

**APROBADO** identifica controles de diseño ya acreditados en la auditoría;
**PENDIENTE** indica una comprobación/evidencia todavía no realizada;
**BLOQUEANTE** es una condición para no habilitar la siguiente etapa.
Un pendiente obligatorio mantiene bloqueada esa etapa hasta su cierre documentado.

| Control | Estado actual | Evidencia/criterio de cierre | Momento límite |
|---|---|---|---|
| Contrato de 13 columnas, nueve features, L1 C=1 y umbral 1/3 | APROBADO | Auditoría existente; no cambiar definición ni recalibrar con B. | Mantener durante todo el proceso. |
| Ajuste solo en A y reserva antes de leer CSV B | APROBADO | Evaluador: `pipe.fit(X_a, y_a)` y evento persistido anterior a `INPUT_B.read_bytes()`. | Mantener sin cambios. |
| Huellas y autoría e9e0ed5/03455c5 | APROBADO | Auditoría: bytes coincidentes y autoría Paula Navarro. Revalidar únicamente código/configuración en equipo de ejecución. | Antes de cada autorización operativa. |
| Certificación real de cobertura | PENDIENTE | Certificado upstream de intervalo completo, manifiestos/reconciliación y trazabilidad descritos abajo. Los metadatos definidos no bastan por sí solos. | Antes de primera consulta/exportación de B. |
| Autorización para consultar/exportar B | BLOQUEANTE | Instrucción posterior explícita del usuario tras revisar cobertura, CDC y seguridad operativa. Este plan no la concede. | Antes de cualquier acceso a fuentes B. |
| Normalización CDC de B alineada con dbt | PENDIENTE | Variante local B implementada: UPPER(c.op), sin cambios en A/dbt. Cerrar con revisión del diff y resultados de pruebas sintéticas; no se presume éxito de ejecución. | Antes de primera consulta/exportación. |
| Git, equipo único, Python/versiones y hard links | PENDIENTE | Registrar resultados de verificaciones seguras; no basta asumir que otro clon hereda exclusiones. | Antes de exportación. |
| Manifiesto y FINALIZADO de exportación | APROBADO | Su escritura existe en el código, con SHA256; esto no afirma que existan artefactos reales. | Verificar éxito después de exportación autorizada. |
| Aceptación de exportación completa por evaluador | PENDIENTE | El enlace no está automatizado. Definir y aplicar la aceptación humana restringida descrita abajo. | Antes de autorizar el test y de abrir su CSV. |
| Autorización única de evaluación | BLOQUEANTE | Otra instrucción posterior y archivo vinculado al HEAD aprobado, política y hash certificado de exportación. | Antes de entrenar modelo final o ejecutar evaluador. |

## 1. Cobertura: qué habría que certificar

Ventana posterior exacta: **[2026-07-31 00:00:00, 2026-08-30 00:00:00)** con la
convención UTC de A. Certificar además la previa [2026-07-03, 2026-07-31), los
catálogos/identidades y el historial CDC anterior a 2026-07-31. No usar etiquetas
ni prevalencia de abandono para acreditar cobertura.

| Operador | Tabla Staging y procedencia | Tabla Silver / fecha usada para etiquetar | Comprobación futura |
|---|---|---|---|
| Transmetro | `staging.transmetro_validaciones`; partición/offset Kafka | `silver.silver_transmetro_validaciones`; `fecha_hora_local AT TIME ZONE 'UTC'` | Continuidad/completitud de mensajes frente al origen, deduplicación por reglas dbt y cobertura diaria de eventos válidos. |
| Transurbano | `staging.transurbano_transacciones`; `source_row_number` | `silver.silver_transurbano_transacciones`; `fecha_hora_local` | Archivo completo y secuencia de filas, explicación de rechazos por parada nula/fecha futura. |
| MetroRiel | `staging.metroriel_viajes`; `source_row_number` | `silver.silver_metroriel_viajes`; `entry_ts` | Archivo completo y secuencia de filas; reconciliar exclusión de viajes sin salida. |
| Aerómetro | `staging.aerometro_boardings`; partición/offset Kafka | `silver.silver_aerometro_boardings`; `fecha_hora_local` | Completitud de mensajes frente al origen y normalización temporal. |
| CDC | `staging.cdc_padron_usuarios`; seq, commit_ts, source_file/source_row_number | No sustituir por estado actual; la disponibilidad usa historial anterior al corte | Snapshot inicial/historial suficiente, origen y secuencias reconciliados, último estado por commit_ts/seq y contrato de op. |

Ubicaciones: `scripts/staging/cargar_operaciones_staging.py`, definiciones de tablas
(líneas 55–118); `scripts/staging/cargar_cdc_staging.py` (38–53); modelos
`dbt_red_metropolitana/models/silver/silver_*` de esos operadores;
`scripts/etiquetado/calcular_etiquetas.py`, SQL_EVENTOS y SQL_ULTIMAS_OPERACIONES.

Metadatos que habría que vincular, sin examinarlos en este bloque:

- **Batch y CDC:** manifiestos definidos bajo `bronze/_manifests/`, con `source_file`,
  `source_file_sha256`, `records`, `expected_records`, `count_matches`, `parquet_files`
  e ingestion_timestamp/date. Su escritura está en
  `scripts/batch/cargar_batch_bronze.py:451` y `scripts/cdc/cargar_cdc_bronze.py:239`.
  Conteos esperados y hashes deben proceder de una versión de origen identificada;
  un esperado constante en código no certifica que el archivo origen sea completo.
- **Streaming:** registros Bronze con source_file, topic, partition, offset e ingestión
  (`scripts/streaming/consumidor_bronze.py:372`). Contrastar particiones y rangos de
  offsets con la publicación completa del origen, duplicados y mensajes faltantes.
  Un watermark Kafka solo describe lo publicado en ese topic, no todo el origen.
- **Reconciliación existente:** el código de `scripts/validaciones/inventario_bronze.py`
  define `docs/reportes_fase1/reconciliacion_bronze.json` y `.csv`, con esperados,
  cargados, diferencia y validez. Identificar la ejecución/snapshot a la que corresponden;
  no volver a ejecutar ingestas ni validadores históricos para este cierre.
- **Staging/Silver:** ingestion_timestamp/date, raw_value y números de fila/offset permiten
  rastrear pérdidas y transformaciones, pero fecha de ingestión no equivale a fecha del
  evento. Reconciliar origen → Bronze → Staging → Silver y explicar cada exclusión.
- **Certificado de origen:** responsable, fuente/versión o snapshot, inicio y fin exclusivos
  de cobertura de eventos, cierre del periodo sin retrasos pendientes y evidencia de
  extracción completa por cada operador. Registrar también dependencias de identidad,
  catálogos y CDC. No inferirlo del último evento ni de ausencia de actividad.

Conteos a comprobar posteriormente: filas por fuente/versión y partición o rango de
filas; duplicados/faltantes; eventos por día en las dos ventanas; descartes de calidad
por causa; sumas reconciliadas entre capas. Cero eventos en un día debe poder
distinguirse de ingesta incompleta con evidencia del origen. No se exige artificialmente
que cada día tenga viajes ni se publican conteos de abandonos.

**Resultado de planificación: PENDIENTE.** Las definiciones de manifiestos revisadas
certifican, como máximo, coincidencia de archivos/conteos de una ingesta; no incluyen
por sí solas una certificación independiente de cobertura temporal integral de los
cuatro orígenes. Sin esa evidencia adicional, no cerrar completitud ni habilitar B.
`--cobertura-confirmada-hasta 2026-08-30` solo registra una declaración del operador.

## 2. CDC: cierre sin modificar Fase 1

Comparación estática ya identificada:

| Lugar | Tratamiento |
|---|---|
| `calcular_etiquetas.py:85` | `WHEN c.op = 'DELETE' THEN FALSE`: sensible a mayúsculas. |
| `exportar_dataset_corte_b.py`, SQL_DISPONIBILIDAD_B | Variante local implementada: `WHEN UPPER(c.op) = 'DELETE' THEN FALSE`; deja de importar SQL_DISPONIBILIDAD del etiquetador. |
| `feat_abandono_cortes.sql:45` y 72 | `UPPER(p.op)` y comparación con DELETE: tolera diferencias de mayúsculas. |
| `cargar_cdc_staging.py:41` y 132–164 | VARCHAR NOT NULL, sin CHECK de dominio ni conversión a mayúsculas. |

No hay garantía upstream ni prueba de que existan operaciones en minúsculas.
Tras autorización explícita se implementó el cambio mínimo solo en el exportador B:
una consulta local idéntica a SQL_DISPONIBILIDAD salvo UPPER(c.op). No se modifica
Fase 1, su historial, sus etiquetas ni dbt. No se añade TRIM. El último estado sigue
seleccionándose por commit_ts < corte, commit_ts DESC y seq DESC; disponibilidad
personal sigue usando BOOL_OR y la elegibilidad exige dos abordajes previos.

Pruebas reproducibles: `tests/modelado/test_cdc_disponibilidad_b.py`, diez métodos
unittest con subcasos para DELETE/delete/Delete, INSERT/UPDATE, historial ausente,
otros operadores, varias tarjetas Transmetro, frontera temporal y desempates.
Usan SQLite exclusivamente en memoria, constantes obtenidas por AST y ninguna
importación de exportadores o psycopg. Ejecutan la consulta real de disponibilidad;
DISTINCT ON se traduce a ROW_NUMBER solo en el arnés, no en producción. Una aserción
exige que la única diferencia SQL frente a A sea UPPER. Es una validación sintética,
no integración PostgreSQL ni certificado de datos reales.

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts/modelado/exportar_dataset_corte_b.py tests/modelado/test_cdc_disponibilidad_b.py
.\.venv\Scripts\python.exe tests/modelado/test_cdc_disponibilidad_b.py -v
```

Estado de esta actualización: se intentaron compilación y pruebas con `.venv`, pero
Python no pudo iniciar su intérprete base de WindowsApps (salida 1 en ambos casos).
El control CDC permanece **PENDIENTE** hasta ejecutar y revisar los resultados en
PowerShell operativo. No se ejecutó exportación ni se consultaron datos reales.

Comparabilidad: si el historial ya utiliza mayúsculas no hay diferencia de elegibilidad.
Si usa variantes DELETE, la población B puede cambiar cuando no exista otro
identificador disponible. A conserva su tratamiento original y no se recalcula;
documentar esa diferencia metodológica sin cuantificar efectos no observados.

El exportador B no está en `sha256_codigo` de la política actual: un cambio aprobado
en él exigiría nuevo commit/revisión y manifiesto con nuevas huellas de procedencia,
pero **no justifica alterar las huellas congeladas del clasificador**. La corrección
está aplicada al código local y sigue pendiente de revisión/versionado antes de
cualquier exportación. e9e0ed5 y 03455c5 se conservan como antecedentes; el manifiesto
futuro registrará la nueva huella del exportador y el commit aprobado.

## 3. Exportación completa y aceptación antes del test

Diseño comprobado en `exportar_dataset_corte_b.py:240–270`:

1. CSV parcial exclusivo, flush/fsync y validación privada.
2. SHA256 del parcial y publicación del CSV mediante enlace exclusivo.
3. Manifiesto exclusivo, flush/fsync: estado `EXPORTADO_VALIDADO`, hash del CSV,
   hash de política, ventanas, columnas, commit y hashes de seis archivos fuente.
4. Evento persistido `FINALIZADO`, estado `EXPORTADO_VALIDADO`, con el mismo hash.

Existe manifiesto, huella e indicador de finalización. **No constituyen una operación
atómica conjunta:** un fallo después de publicar el CSV puede dejarlo sin manifiesto
completo o FINALIZADO. No aceptar solo existencia del CSV; no borrar/reintentar.

El evaluador, antes de abrir el CSV B, comprueba política/sidecar, hashes de código,
archivos congelados versionados y sin cambios, autorización y commit HEAD, fecha de
autorización, formato del hash B y ausencia del directorio de resultados. Reserva su
bitácora exclusiva, verifica versiones y A, ajusta solo A y registra ANTES_DE_LECTURA_B.
Solo entonces lee bytes de B, verifica hash y valida esquema/contenido.

**No automatizado:** el evaluador no lee el manifiesto ni la bitácora de exportación,
no acredita cobertura y no sabe que FINALIZADO se alcanzó. Tampoco valida la exclusión
Git de todos los artefactos locales. La revisión humana debe preceder a su autorización.

Criterio de aceptación futura, sin abrir el CSV ni etiquetas:

- Manifiesto válido con estado EXPORTADO_VALIDADO y evaluación NO_EJECUTADO, ventanas
  exactas y trece columnas del contrato; cobertura vinculada al certificado aprobado.
- Bitácora de exportación con reserva, ANTES_DE_CONSULTAR_B y cierre FINALIZADO; ningún
  fallo o intento adicional pendiente de auditoría. Hash de cierre igual al del manifiesto.
- Hash de política igual al archivo congelado; commit y hashes de procedencia del
  exportador/dependencias iguales a los efectivamente aprobados para exportar.
- Ningún parcial residual, reserva previa de test ni resultado previo; revisión de
  un operador identificado en la máquina designada. No leer distribución ni filas.
- Acta privada de aceptación con referencia al certificado de cobertura y artefactos,
  sin datos individuales; después, autorización separada de evaluación con el hash
  certificado y el HEAD de ejecución aprobado.

**No usar `Get-FileHash dataset_corte_B.csv` como preflight independiente:** también
lee todo el test. Copiar el hash ya registrado en manifiesto/bitácora a la autorización
futura. El cotejo con los bytes reales corresponde al evaluador, después de su reserva.
Si la procedencia no es confiable o los certificados discrepan, detenerse.

No se propone cambiar el evaluador para imponer automáticamente esta aceptación.
Si se quisiera hacerlo, revisar primero: cualquier cambio de sus bytes rompe su
autohuella en `politica_congelada.json`; actualizar esta rompe el sidecar y cualquier
autorización vinculada a su SHA256. Requeriría una revisión/versionado formal de la
congelación y nuevos hashes/autorización antes de B, no una edición silenciosa.
**No implementar esa modificación sin revisión explícita.**

## 4. Comandos seguros propuestos para PowerShell — no acceden a B

Desde la raíz, con operador presente. Son un procedimiento pendiente, no comandos
ejecutados en este bloque. No usar ingestas, `psql`, dbt, exportación ni evaluación.

### Repositorio y equipo

```powershell
Get-Location
$env:COMPUTERNAME
[System.Environment]::UserName
git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short
git diff --check
git diff --exit-code -- scripts/modelado/evaluar_test_unico_b.py docs/Fase_2/fase2_2/politica_congelada.json docs/Fase_2/fase2_2/politica_congelada.sha256
```

Resultado esperado: repositorio/rama y equipo acordados; ningún cambio de código
congelado. Los documentos de auditoría/plan y los dos documentos antiguos de Fase 1
sin seguimiento se identifican aparte; no borrarlos, agregarlos ni tratarlos como datos
de B. `git diff` solo contrasta índice/HEAD: cotejar además las huellas congeladas
de código/configuración según el procedimiento ya aprobado. No recalcular hash de A/B
en este bloque. Registrar nombre de equipo/operador solo en control privado; el nombre
del equipo es una identificación operativa, no una autenticación criptográfica.

### Exclusión y ausencia de artefactos previos: solo metadatos de rutas

```powershell
$rutasControlB = @(
  'datos_modelado_local/fase2_2/dataset_corte_B.csv',
  'datos_modelado_local/fase2_2/dataset_corte_B.csv.partial',
  'datos_modelado_local/fase2_2/exportacion_b_manifiesto.json',
  'datos_modelado_local/fase2_2/exportacion_b_bitacora.jsonl',
  'datos_modelado_local/fase2_2/autorizacion_test_b.json',
  'datos_modelado_local/fase2_2/test_b_bitacora.jsonl'
)
foreach ($rutaControlB in $rutasControlB) {
  git check-ignore -v -- $rutaControlB
  if ($LASTEXITCODE -ne 0) { throw 'Ruta no ignorada: detener revision' }
  $versionadosControlB = @(git ls-files -- $rutaControlB)
  if ($LASTEXITCODE -ne 0 -or $versionadosControlB.Count -gt 0) {
    throw 'Ruta versionada o comprobacion fallida: detener revision'
  }
  if (Test-Path -LiteralPath $rutaControlB -ErrorAction Stop) {
    throw 'Existe un artefacto previo: detenerse sin abrirlo ni borrarlo'
  }
}
if (Test-Path -LiteralPath 'docs/reportes_fase2_2/test_unico_B' -ErrorAction Stop) {
  throw 'Existe directorio de resultados: detenerse sin abrirlo'
}
```

Este bloque es **solo para antes de la primera exportación**: después se esperarán
artefactos de exportación y hará falta el protocolo de aceptación, no este chequeo
de ausencia total. `Test-Path` no lee contenidos. No usar Get-Content/Get-FileHash
en rutas B ni enumerar sus filas. La regla local `.git/info/exclude` no se hereda
al clonar; si falta, detener y revisar configuración antes de crear datos, sin forzar add.
Comprobar manualmente que el directorio designado no redirige a otra copia/equipo.

### Sintaxis sin ejecutar módulos y ayuda del exportador

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import ast; from pathlib import Path; archivos=['scripts/modelado/exportar_dataset_corte_b.py','scripts/modelado/evaluar_test_unico_b.py']; [ast.parse(Path(p).read_text(encoding='utf-8-sig')) for p in archivos]; print('Sintaxis correcta; modulos no ejecutados')"
.\.venv\Scripts\python.exe scripts/modelado/exportar_dataset_corte_b.py --help
```

El comando AST solo analiza texto de código; no ejecuta ni importa el evaluador
congelado. `--help` del exportador termina antes de dependencias/consultas. Si Python
no inicia, queda PENDIENTE; no cambiar política/entorno para ocultar diferencias de
versión. Confirmar posteriormente versiones instaladas sin entrenar. No se propone
ejecutar el evaluador en este bloque, ni siquiera para ayuda.

La prueba de hard links y apertura exclusiva deberá ser independiente, con archivos
sintéticos nuevos de nombres distintos de B en el mismo volumen, sin leer archivos
preexistentes. Registrar resultado antes de exportar; no crear reservas ni datasets
B para probar el bloqueo. Usar una sola máquina/operador: OneDrive no garantiza
exclusión distribuida. Esta prueba tampoco se ejecuta en el bloque actual.

## 5. Operaciones que requieren autorización posterior — NO ejecutar ahora

Se deberán autorizar expresamente: inspección de manifiestos/datos reales de ingesta,
consultas de cobertura a PostgreSQL, exportación, lectura de sus manifiestos/bitácoras
y, separadamente, ajuste final/evaluación. No ejecutar scripts históricos para obtener
evidencias: algunos reconstruyen/truncan capas y publican conteos no necesarios.

Ejemplo de consulta agregada futura, limitada a cobertura operativa y sin etiquetas
ni identificadores; **no es prueba suficiente de completitud** ni está autorizada:

```sql
WITH eventos AS (
  SELECT 'Transmetro' AS sistema,
         fecha_hora_local AT TIME ZONE 'UTC' AS fecha
  FROM silver.silver_transmetro_validaciones
  UNION ALL
  SELECT 'Transurbano', fecha_hora_local
  FROM silver.silver_transurbano_transacciones
  UNION ALL
  SELECT 'MetroRiel', entry_ts
  FROM silver.silver_metroriel_viajes
  UNION ALL
  SELECT 'Aerometro', fecha_hora_local
  FROM silver.silver_aerometro_boardings
)
SELECT sistema, fecha::date AS dia, COUNT(*) AS eventos_validos
FROM eventos
WHERE fecha >= TIMESTAMP '2026-07-31'
  AND fecha < TIMESTAMP '2026-08-30'
GROUP BY sistema, fecha::date
ORDER BY sistema, dia;
```

Debe usarse sesión UTC de solo lectura, límites revisados y reconciliaciones upstream;
la consulta no emite días sin eventos, que deben confrontarse con un calendario de
los 30 días y certificación de cada origen. Repetir el diseño para la ventana previa
solo bajo la autorización correspondiente. No incorporar abandono, probabilidades
ni selección de personas a estas consultas.

Comando futuro de exportación, únicamente tras cerrar los requisitos preexportación:

```powershell
python scripts/modelado/exportar_dataset_corte_b.py --exportar-b --confirmacion AUTORIZO_EXPORTACION_B --cobertura-confirmada-hasta 2026-08-30
```

Después de una exportación autorizada y con permiso para revisar sus certificados,
estos comandos futuros leen solo artefactos de control, no el CSV; **no están incluidos
en la batería segura actual**:

```powershell
$manifiestoB = Get-Content -LiteralPath 'datos_modelado_local/fase2_2/exportacion_b_manifiesto.json' -Raw -Encoding utf8 | ConvertFrom-Json
$eventosExportacionB = @(Get-Content -LiteralPath 'datos_modelado_local/fase2_2/exportacion_b_bitacora.jsonl' -Encoding utf8 | ForEach-Object { $_ | ConvertFrom-Json })
if ($manifiestoB.estado -ne 'EXPORTADO_VALIDADO' -or $eventosExportacionB.Count -eq 0) {
  throw 'Exportacion no certificada'
}
$cierreExportacionB = $eventosExportacionB[-1]
if ($cierreExportacionB.evento -ne 'FINALIZADO' -or
    $cierreExportacionB.estado -ne 'EXPORTADO_VALIDADO' -or
    $cierreExportacionB.dataset_b_sha256 -ne $manifiestoB.dataset_b_sha256 -or
    @($eventosExportacionB | Where-Object { $_.evento -eq 'FALLO_REQUIERE_REVISION' }).Count -gt 0) {
  throw 'Cierre de exportacion inconsistente: detenerse'
}
```

Estas comprobaciones mínimas no sustituyen revisar ventanas, columnas, procedencia,
política y certificado de cobertura descritos en la sección 3. No imprimir los objetos
completos, abrir el CSV ni generar autorización automáticamente. No se incluye aquí
un comando operativo del evaluador: su ejecución es una etapa separada todavía bloqueada.

## 6. Secuencia de cierre y evidencia exigida

1. **Revisión del cambio CDC:** aceptar la variante local ya implementada y sus pruebas
   sintéticas, manteniendo la salvedad de comparabilidad A/B. No se asume permiso para leer B.
2. **Pruebas sin B:** resultados de comandos seguros, máquina/operador, versiones,
   exclusión Git y prueba sintética de filesystem/CDC. Conservar el registro técnico
   sin datos individuales. Las pruebas se ejecutarán en otro bloque autorizado.
3. **Cobertura:** reunir evidencia upstream suficiente. Si solo hay conteos globales,
   fechas máximas o una declaración sin soporte, mantener PENDIENTE y bloquear acceso.
   Cualquier revisión de datos reales requiere instrucción posterior que defina su alcance.
4. **Exportación:** solo con autorización expresa y controles previos cerrados. Conservar
   bitácora y manifiesto; ante fallo no borrar ni reintentar automáticamente.
5. **Aceptación de exportación:** revisión privada documentada de certificados, sin
   abrir filas/etiquetas; no autorizar test con un CSV final huérfano.
6. **Test único:** nueva instrucción expresa, autorización vinculada a política, hash
   certificado y HEAD aprobado de ese momento. Versionar documentos puede cambiar HEAD;
   no reutilizar e9e0ed5 ni 03455c5 automáticamente como commit de ejecución. No cambiar
   modelo/umbral tras conocer B ni repetir ante fallos sin auditoría del intento consumido.

No se modificaron ni ejecutaron política, sidecar o evaluador. Solo se implementó
la variante CDC local B y su validación sintética separada. Cualquier modificación futura del evaluador o definición congelada
requiere revisión formal antes de implementarse. Este plan no habilita ninguna lectura B.
