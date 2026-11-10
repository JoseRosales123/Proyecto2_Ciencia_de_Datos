# Modos de exportación B — implementación preparada, sin autorización operativa

La propuesta de enmienda **no está aprobada**. Implementar validaciones y fixtures
no aprueba esa propuesta ni autoriza exportar. No se creó acta, autorización,
dataset ni reserva operativa. Política, sidecar, evaluador y resultado de auditoría
permanecen intactos; `certificado=false` sigue siendo el resultado histórico oficial.

## Contrato explícito

El exportador exige `--exportar-b` y exactamente uno de estos flags:

| Flag | Modo registrado | Condiciones |
|---|---|---|
| `--certificacion-de-origen` | `CERTIFICACION_DE_ORIGEN` | Confirmación histórica `AUTORIZO_EXPORTACION_B` y `--cobertura-confirmada-hasta` igual o posterior a 2026-08-30. No admite campos del modo limitado. Conserva el significado de declaración de cobertura completa respaldada por el operador; el código no autentica por sí solo un certificado de origen. |
| `--aceptacion-limitada-del-snapshot` | `ACEPTACION_LIMITADA_DEL_SNAPSHOT` | Confirmación específica `AUTORIZO_EXPORTACION_B_SNAPSHOT_LIMITADO`, `--acta-sha256` y `--snapshot-id`, acta aprobada y validada. Rechaza cualquier fecha de cobertura certificada. |

Sin flag de modo no hay exportación. Seleccionar ambos produce error de argparse.
Sin `--exportar-b`, o con `--help`, solo se muestra ayuda. La validación se repite
dentro de `exportar()`, por lo que una llamada directa tampoco elude la autorización.
Los comandos históricos sin modo explícito ahora fallan de forma segura.

## Acta privada futura: no creada

Ruta fija: `datos_modelado_local/fase2_2/acta_aceptacion_snapshot_b.json`, ignorada
por Git y no versionada. Se comprueba la exclusión antes de leerla, y se rechaza
una redirección de ruta. Su SHA256 debe coincidir con la huella externa aprobada
aportada en CLI. El archivo no se genera ni completa automáticamente.

Campos exigidos:

- `version`: entero 1; `id` no vacío; `estado`: APROBADA;
  `tipo_respaldo`: ACEPTACION_LIMITADA_DEL_SNAPSHOT.
- `certificado_origen`: false; `evaluacion_b`: NO_EJECUTADO;
  `acepta_limitaciones`: true.
- `aprobado_por`, `referencia_aprobacion_enmienda` y
  `referencia_autorizacion_exportacion`: textos no vacíos que deben corresponder
  a instrucciones reales y separadas, revisadas por el custodio.
- `validacion_academica`: objeto con estado APROBADA o NO_REQUERIDA_JUSTIFICADA y
  referencia no vacía. No admite PENDIENTE; el custodio debe comprobar la justificación.
- `fecha_utc`: fecha con zona, posterior o igual a congelación y no futura.
- `propuesta_sha256`, `politica_sha256`, `exportador_sha256` y `commit`:
  coincidencia exacta con los archivos actuales y HEAD aprobado. Propuesta, política,
  sidecar y exportador deben estar versionados y sin modificaciones locales.
- `snapshot`: objeto con `id`, `descripcion`, `fecha_snapshot_utc` con zona y no
  posterior a aprobación, y lista no vacía `evidencias` con pares `ruta`/`sha256`.
  El identificador debe coincidir exactamente con `--snapshot-id`.
- `snapshot_sha256`: SHA256 de `json.dumps(snapshot, sort_keys=True,
  separators=(',', ':'), ensure_ascii=False).encode('utf-8')`.

Solo se admite leer evidencias agregadas JSON/JSONL/CSV dentro de
`docs/reportes_fase2_2/cobertura_fuentes/` y manifiestos JSON bajo
`bronze/_manifests/`. Las rutas resueltas deben permanecer dentro de esas áreas,
sin duplicados; se compara cada huella. Nunca se admite referenciar el CSV B como
evidencia para esta validación. La huella del descriptor vincula la aprobación a
ese descriptor/evidencias; **no es una huella criptográfica del contenido de la DB**.
La identidad física e inmutabilidad del snapshot y su vínculo con la exportación
siguen requiriendo aceptación/custodia documentada. No se certificarán por inferencia.

Todos esos controles ocurren antes de crear la reserva, importar psycopg/cargar
.env o conectar. Una aprobación escrita en JSON no prueba por sí sola identidad
del firmante ni consentimiento: verificar la instrucción humana referenciada sigue
siendo obligatorio. No falsificar campos para satisfacer el programa.

## Reserva, salidas y trazabilidad

Se mantienen rutas de CSV/parcial/manifiesto/bitácora, creación exclusiva, rechazo de
artefactos previos, reserva persistida antes del acceso, validaciones y no reintento.
No se cambia SQL de eventos/etiquetas/features, corrección CDC, ventanas ni columnas.

La reserva, evento previo al acceso, manifiesto y cierre registrarán modo/tipo de
respaldo. En limitado, registrarán `certificado_origen=false`, huella/id del acta,
huellas de propuesta/descriptor, id de snapshot y commit aprobado. No existirá campo
de fecha ficticia de cobertura certificada. El manifiesto separa
`integridad_exportacion=VALIDADA` del respaldo de origen. En certificación se conserva
la fecha de cobertura declarada; su valor de certificado refleja esa declaración
del operador, no una autenticación independiente realizada por el script.

Este cambio modifica la huella del exportador y exige revisión/versionado posterior.
El exportador no pertenece a `sha256_codigo` de la política congelada, que no se
actualiza. La autorización futura del evaluador seguirá ligada al HEAD aprobado de
su ejecución y al cierre técnico de exportación. El evaluador congelado no valida
automáticamente el acta: se mantiene el control humano de aceptación previa.

## Pruebas reproducibles sin B

`tests/modelado/test_modos_exportacion_b.py` contiene quince métodos unittest con
subcasos. Crea exclusivamente fixtures desechables en un directorio temporal del
sistema, con nombres `fixture_*`, y sustituye todas las rutas operativas del módulo.
Los JSON de prueba llevan referencias FIXTURE y no son actas reales. Simula Git y
la comprobación de exclusión; esta última debe verificarse realmente en el equipo
operativo antes de ejecutar, no se da por probada con un mock.

Una conexión PostgreSQL simulada lanza una excepción si se intenta utilizar. Se
prueba: ausencia de modo/confirmación, exclusión mutua, semántica de certificación,
fecha prohibida en limitado, acta ausente/no aprobada/incompleta, hashes y commit
incorrectos, snapshot/evidencias alterados o fuera de ruta, cambios locales y una
reserva sintética previa. Los rechazos comprueban que no hubo conexión ni nueva
reserva/salida. El caso positivo valida **solo preflight**, nunca exportación.

```powershell
.\.venv\Scripts\python.exe -m py_compile scripts/modelado/exportar_dataset_corte_b.py tests/modelado/test_modos_exportacion_b.py
.\.venv\Scripts\python.exe tests/modelado/test_modos_exportacion_b.py -v
.\.venv\Scripts\python.exe tests/modelado/test_cdc_disponibilidad_b.py -v
```

En Codex se intentaron compilación y la nueva batería, pero el intérprete base de
WindowsApps no pudo iniciarse (salida 1). Ambas verificaciones quedan PENDIENTES
de ejecución en PowerShell operativo; no se afirma que las quince pruebas pasaran.
Las diez pruebas CDC habían sido aprobadas anteriormente según el estado confirmado;
deben repetirse como regresión de esta versión, sin usar datos reales.

## Controles aún pendientes

Revisión de código y pruebas ejecutadas; aprobación de la enmienda y académica si
corresponde; definición y custodia del snapshot; versionado del cambio; instrucciones
separadas de exportación/evaluación; acta privada auténtica con sus referencias y
huellas; identidad del equipo/operador, exclusión real de Git y aceptación del cierre
de exportación. No se ejecutará B para probar estos controles ni se creará un acta
operativa antes de esas decisiones. OneDrive no garantiza exclusión entre máquinas.
