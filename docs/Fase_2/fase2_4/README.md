# Fase 2.4 — Arquitectura inicial de inferencia (Paolo Marroquín)

Implementación técnica inicial realizada desde el equipo de José, para revisión
con Paolo. Autoría Git futura acordada: Paolo Marroquín, con su autorización.
No se configuró Git ni credenciales y no se creó commit. Fases 2.2/2.3 intactas.

**No hay pipeline real persistido ni predicciones C generadas en este paso.**
No ejecutar ni repetir exportación/evaluación B. Las pruebas usan únicamente fixtures.

[Ficha de modelo inicial](ficha_modelo.borrador.md): resume la especificación y
métricas históricas públicas, distinguiéndolas del artefacto aún no reproducido.

## Persistencia separada y procedencia

`scripts/mlops/persistir_pipeline_a.py` verifica política/sidecar, huellas del código
histórico, hash de A, nueve características, hiperparámetros y versiones. Reutiliza
la carga y constructor históricos sin ejecutar sus main. Solo con confirmación
explícita ajustaría una vez sobre todo A y guardaría pipeline completo en
`modelos/fase2_4/pipeline.joblib`, acompañado de `manifiesto.json` con hashes,
semilla, versiones, código y HEAD. Esquema de publicación v2: requiere además
`reserva.json` y el marcador final `finalizado.json`. La salida es exclusiva;
no sobrescribe artefactos ni borra reservas fallidas.

Este sería un **nuevo ajuste reproducido solo desde A**, no el mismo objeto en
memoria usado en B. No se usa B para comprobar equivalencia, seleccionar o ajustar.
La evidencia histórica de B describe la especificación evaluada, no demuestra
identidad binaria de un artefacto posterior. El modelo/manifiesto deberán revisarse
y versionarse antes de inferencia oficial; todavía no existen.

Comando propuesto para una etapa posterior autorizada, NO ejecutado:

```powershell
# Sustituir el marcador por el SHA completo revisado tras cerrar el versionado.
.\.venv\Scripts\python.exe scripts/mlops/persistir_pipeline_a.py --entrenar-a --confirmacion REPRODUCIR_PIPELINE_SOLO_A --head-esperado <SHA_COMPLETO_REVISADO>
```

## Inferencia y entorno

`predecir.py --datos <carpeta> --fecha-corte 2026-08-30` carga el pipeline y
manifiesto locales confiables, verifica hashes/versiones y utiliza únicamente
`predict_proba`, nunca fit/fit_transform. Joblib puede ejecutar código al cargar:
no se admite un artefacto de terceros ni una ruta de modelo suministrada en CLI.
El lector exige esquema v2, marcador FINALIZADO, reserva y modelo/manifiesto con
hashes concordantes, y rechaza cualquier fallo registrado o publicación incompleta.
No admite silenciosamente artefactos del esquema antiguo sin esos controles.
El hash del manifiesto no es una firma: modelo y manifiesto deben provenir del
repositorio revisado, no de la carpeta de datos.

Python 3.12.10; dependencias específicas en `requirements-fase2_4.txt`, sin alterar
el entorno compartido. Se conserva sklearn 1.9.1/numpy 2.5.4/pandas 3.1.0 y semilla
42. Falta validar instalación limpia y completar lock transitivo antes de declarar
reproducibilidad de despliegue; el archivo inicial fija las dependencias principales.

Salida por defecto privada: `datos_modelado_local/fase2_4/predicciones_C.csv`.
Esquema exacto `unidad_id,tarjetas,puntaje,contactar`; una fila por unidad elegible,
ordenada por unidad. Tarjetas CARD:hex64 autorizadas, únicas, ordenadas y separadas
por punto y coma. Unidad USR:hex64; nunca se exportan secretos HMAC ni IDs originales.
Umbral `float(Fraction(1,3))`, contacto con >=, sin redondear probabilidades para decidir.
No se sobrescriben predicciones previas. La publicación GitHub será una copia revisada
posteriormente, no automática; hasta entonces no hay entregable C público.

## Contrato normalizado C y bloqueo de integración con fuentes reales

**El extractor desde Bronze/Silver/dbt todavía NO está implementado ni validado.**
`scripts/mlops/adaptador_c.py` implementa solo preflight y conversiones puras;
`require_real_ready` bloquea cualquier intento de habilitar extracción real.
No se utiliza la identidad global de Silver porque podría incorporar asociaciones
posteriores. El módulo puro `scripts/mlops/features_c.py` requiere una carpeta con:

- `contrato_c.json`: contrato INFERENCIA_C_NORMALIZADA_V1, fecha_corte 2026-08-30,
  datos_sinteticos=true, ids_autorizados=true, reloj_features LEGADO_1_4_SIN_ZONA y
  corte_disponibilidad_utc 2026-08-30T00:00:00Z. Son declaraciones del custodio, no
  certificación automática de procedencia ni autorización de datos reales.
  V1 conserva la disponibilidad y efectividad CDC UTC00 del prototipo. No es un
  contrato congelado de A/B. Para otros límites usar explícitamente V2, como se
  describe en los controles temporales más abajo; no se eligen automáticamente.
- `eventos.csv`: evento_id,tarjeta_id,sistema,fecha_feature,disponible_utc,zona,gasto_gtq.
- `identidades.csv`: tarjeta_id,unidad_id,sistema,vigente_desde,disponible_utc,seq.
- `cdc.csv`: tarjeta_id,op,commit_utc,disponible_utc,seq (puede tener solo cabecera).

Solo campos exactos: no se aceptan CSV de entrenamiento ni columnas de etiqueta.
Los identificadores deben estar seudonimizados previamente por un proceso autorizado,
estable y sin depender del futuro; el script no conoce ni solicita la clave secreta.
Los archivos originales con identificadores reales no son entradas permitidas.

Ventanas de features `[2026-08-02,2026-08-30)` y 7 días `[2026-08-23,2026-08-30)`.
La fecha_feature conserva el reloj de las expresiones SQL: Transmetro usa
fecha_hora_local AT TIME ZONE UTC y exige verificar la zona de sesión histórica;
no se presupone que esa sesión fuera UTC. Transurbano/Aerómetro usan su
fecha_hora_local; MetroRiel usa entry_ts bajo la convención del servidor. El adaptador
debe probar esas conversiones, no interpretar todos los strings como UTC uniforme.
Aerómetro requiere convertir timestamp_utc a America/Guatemala antes de obtener su
reloj local: el límite local equivale a 2026-08-30 06:00Z para eventos.

El contrato normalizado requiere disponibilidad y CDC con zona. V1 propone UTC00
como límite explícito del prototipo; esto NO acredita que commit_ts histórico
estuviera expresado en UTC. V2 permite declarar sus límites independientemente.
Esta separación de relojes NO afirma simultaneidad física. **Revisar con Paolo la compatibilidad del
reloj de disponibilidad con el límite local de Aerómetro**: eventos locales previos
que solo estuvieron disponibles tras UTC00 se excluyen. No cambiar silenciosamente
ese contrato ni afirmar equivalencia real A-C antes de resolverlo.

Identidades y CDC se filtran por fecha efectiva y disponibilidad ANTES de elegir
última versión por timestamp/seq. Eventos futuros y correcciones disponibles tarde
se excluyen ANTES de deduplicar. Conflictos con igual timestamp/seq o evento_id
semánticamente contradictorios se rechazan. Duplicados con el mismo contenido y
distinta ingesta no cuentan dos veces. Las claves de evento incluyen sistema y
evento_id: no se colapsan eventos de distintos operadores por coincidencia del ID.
Población: >=2 eventos previos y algún identificador disponible; op
CDC se normaliza a mayúsculas. Para Transmetro, DELETE deshabilita tarjeta; los
otros sistemas siguen la disponibilidad histórica. Las tarjetas de salida provienen
solo de la identidad disponible a corte, no de registros posteriores.

Las nueve features mantienen orden y fórmulas históricas: siete numéricas y modo/zona
predominantes, desempate lexicográfico; pico 5–8 y 16–19 inclusive; gasto nulo=0;
redondeo decimal a 4/2 posiciones. Falta conciliar collation y dtypes con SQL real
sin tocar A/B. El esquema inicial exige gasto no negativo y rechaza historias ambiguas.

## Pruebas e invariancia

`tests/modelado/test_mlops_c.py` usa fixtures y un modelo falso que prohíbe fit.
Comprueba fechas, features, frontera temporal, CDC, deduplicación, esquema/orden CSV,
umbral en puntos vecinos de 1/3, carga con hash y ausencia de entrenamiento.
Añade 30 días posteriores, nuevas identidades, remapeos, CDC y correcciones tardías;
compara población, tarjetas, todas las features y predicciones del modelo falso.
No demuestra todavía invariancia sobre insumos reales ni pipeline persistido.

**25/25 pruebas sintéticas aprobadas** en la revisión temporal (11 iniciales y
14 adicionales). Se ejecutaron sin datasets reales, entrenamiento o modelos reales.
No se ejecutan consultas, dbt ni modelos reales en estas pruebas. Las futuras pruebas
de integración usarán copias privadas/temporales sin alterar predicciones oficiales.

## Entregables pendientes de revisión

1. Resolver relojes, adaptador de fuentes e identidad histórica con Paolo.
2. Autorizar posteriormente la reproducción A; guardar y revisar pipeline/manifiesto.
3. Revisar y completar la ficha borrador de una página con datos, periodos, población,
   etiqueta, métricas públicas A/B, economía, fuga revisada y límites sintéticos.
   Usar resultados agregados ya publicados, nunca reabrir el test B.
4. Validar instalación limpia, invariancia del pipeline y contrato con fuentes reales.
5. Solo entonces generar C y revisar seguridad de su entrega pública en GitHub.

No se afirma cumplimiento final de la rúbrica: esta etapa deja arquitectura y pruebas,
sin entrenamiento A real, inferencia C ni nuevos resultados académicos.

## Integridad reforzada para reproducción A (sin entrenamiento real todavía)

Se conserva EXACTAMENTE `load_data()` y `make_model('l1', 1.0)` históricos,
con todas las filas de A y sin CV, selección adicional o uso B/C. No se modifican
los constructores ni las políticas congeladas de 2.2/2.3.

- `--head-esperado` es obligatorio: compara HEAD antes de cargar, después de cargar,
  después del ajuste, después de serializar y antes del marcador de publicación.
- SHA256 A se compara siempre con el congelado antes/después de carga, tras ajuste
  y antes de publicación. El manifiesto usa ese valor validado, no una lectura
  posterior sin cotejar. `load_data` conserva sus validaciones históricas.
- Se comparan política y sidecar desde antes del preflight, así como hashes de
  código histórico. Se capturan y revisan hashes de persistir_pipeline_a.py,
  contrato_c.py, requirements-fase2_4.txt y dependencias Python locales históricas.
- HEAD y hashes se registran por punto de control. El estado Git de estos archivos
  se registra aparte: que un archivo sea untracked NO lo obliga a aparecer
  artificialmente en HEAD ni bloquea las pruebas. Antes de la ejecución real el
  equipo cerrará su versionado y revisará el HEAD que suministre al comando.

La reserva se crea de forma exclusiva antes de cargar/ajustar; su hash también
se verifica. Modelo y manifiesto se escriben primero en parciales, se sincronizan
con flush/fsync y se publican con hard links exclusivos, sin os.replace. Se verifican
los archivos publicados y solo entonces se enlaza el marcador final, que incluye
hashes de ambos y de la reserva. El lector considera válido únicamente el conjunto
completo con ese marcador. No es una transacción atómica de varios archivos: es una
publicación controlada con marcador final atómico, sobre filesystem local compatible
con hard links (NTFS). No asumir garantías distribuidas de OneDrive.

Un fallo conserva reserva, parciales y cualquier archivo ya enlazado; registra
fallo sin publicar cierre válido. No se limpian automáticamente ni se autoriza
sobrescritura o reintento automático. Debe revisar el operador los restos.

**Límite:** los hashes detectan cambios en puntos de control, no bloquean físicamente
escrituras. Cambios transitorios y restaurados entre comprobaciones pueden escapar
a la detección. Exigir operador único y entradas/código estables durante el ajuste;
la igualdad de hashes no prueba ausencia de toda carrera ni autenticidad del autor.

`tests/modelado/test_persistir_pipeline_a.py` prueba estos fallos con archivos
temporales, constructor/fit falsos y serialización simulada, sin leer A/B reales.
El test de carga v2 en test_mlops_c.py verifica que un bundle incompleto no llega
a joblib.load y que el lector nunca entrena.
Resultado conjunto actual: **41/41 pruebas sintéticas aprobadas** (25 MLOps y
16 persistencia). No se entrenó con A real ni se generó un artefacto real.

## Controles temporales explícitos incorporados

`TemporalControls` distingue tres decisiones: ventanas de eventos por fuente,
corte UTC de disponibilidad y corte UTC efectivo de CDC. `build_features` recibe
estos controles, no infiere uno a partir de otro. Los cortes UTC admitidos para
pruebas son UTC00 o UTC06 del 30 de agosto; cambiar a UTC06 no se aprueba por código.

| Concepto | Regla comprobada con fixtures |
|---|---|
| Evento Aerómetro 28d | UTC [2026-08-02T06:00Z,2026-08-30T06:00Z). |
| Evento Aerómetro 7d | UTC [2026-08-23T06:00Z,2026-08-30T06:00Z). |
| Extremo final | Evento exactamente en el límite queda fuera; inicio incluido. |
| Disponibilidad | Estrictamente anterior al instante declarado; UTC00 y UTC06 se prueban por separado. |
| Efectividad CDC | Límite independiente: mover disponibilidad a UTC06 no mueve por sí solo commit_utc. |
| Identidad | Efectividad en reloj normalizado sin zona y disponibilidad UTC; no se acepta información conocida tarde. |

La conversión de Aerómetro usa `ZoneInfo('America/Guatemala')` con tzdata fijado
en dependencias. No se aplica ese offset a otras fuentes. Transmetro requiere
zona de sesión y referencia explícitas para reproducir `to_timestamp` seguido de
`AT TIME ZONE 'UTC'`; el normalizador falla si faltan. TU/MR conservan timestamps
sin zona conforme a las expresiones SQL; todavía requieren conciliación del
adaptador con el entorno histórico y tipos reales de PostgreSQL.

`normalize_cdc_commit` no acepta el commit_ts ingenuo como UTC implícito: exige
`source_zone` y referencia documental. `normalize_source_cdc` normaliza op/seq y
registra ingesta UTC, pero **no la renombra disponible_utc**, no devuelve tarjeta
original ni fabrica identidad o vigencia. Su resultado es intermediario, no un
registro listo para inferencia.

Para V2 se mantienen esquemas CSV y campos de autorización de V1, cambiando a
`contrato=INFERENCIA_C_NORMALIZADA_V2` y añadiendo obligatoriamente:

```json
{
  "corte_disponibilidad_utc": "2026-08-30T06:00:00Z",
  "corte_efectivo_cdc_utc": "2026-08-30T00:00:00Z",
  "referencia_politica_temporal": "Referencia real a la decisión del equipo; este ejemplo no es aprobación"
}
```

Este ejemplo ilustra límites distintos, no una elección operativa. `read_inputs`
debe invocarse con `with_controls=True` para V2; rechaza descartar la política
temporal. `predecir.py` transmite esos controles sin entrenamiento. Ningún contrato
normalizado declarativo prueba por sí solo la verdad de la disponibilidad histórica.

## Bloqueos y futura integración PostgreSQL

El preflight exige referencias verificables de disponibilidad histórica, historia
de identidad y catálogos, timezone Transmetro/CDC, clave estable Transurbano,
deduplicación point-in-time y equivalencia de collation. `ingestion_timestamp`
generado por los cargadores acredita carga técnica, no conocimiento en agosto.
`source_row_number` sin identidad comprobada del archivo no basta como clave global.
No usar `MIN(fecha_evento)` como fecha efectiva de identidad ni inventar secuencias.

Incluso completando referencias, `require_real_ready` mantiene el bloqueo porque
la extracción PostgreSQL no está implementada ni validada. No importa psycopg,
abre conexiones ni ejecuta SQL. Las referencias no son firmas ni certificaciones.

Procedimiento futuro, sujeto a revisión:

1. Resolver y documentar por fuente qué reloj usa cada campo y elegir explícitamente
   corte de disponibilidad/efectividad. Confirmar historia real o reconocer que falta.
2. Diseñar extractor separado, conexión read-only y snapshot REPEATABLE READ, con
   parámetros de límites por fuente, sin alterar tablas ni consultas A/B.
3. Filtrar evento, disponibilidad y versiones de catálogos ANTES de deduplicar o
   formar identidad. Seleccionar CDC visible por commit_ts/seq después del filtro,
   sin usar `es_version_actual` de la historia completa. Parámetros nunca concatenados.
4. Conciliar nombres/tipos/zonas, gasto no negativo, vacíos y collation. Los fixtures
   prueban desempate por orden de código Unicode en Python; no prueban la collation
   instalada en PostgreSQL. No trasladar esa equivalencia por suposición.
5. Probar con fixtures SQL y luego insumos privados autorizados, en carpetas temporales,
   la invariancia de población, tarjetas, features y scores ante 30 días posteriores.
   No sobrescribir predicciones oficiales ni publicar historias individuales.

Si solo puede fijarse un snapshot actual, se puede proponer una inferencia
retrospectiva limitada a ese snapshot, con aceptación metodológica independiente.
Eso NO acredita disponibilidad histórica en agosto. Congelar la entrada o ignorar
archivos posteriores tampoco constituye por sí solo una prueba de invariancia del
proceso que construye identidad, población y características. No se activa aquí
una ruta de excepción o fallback para esa alternativa.
