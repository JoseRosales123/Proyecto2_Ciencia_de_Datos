# Auditoría estática previa al acceso a B — Fase 2.2

## Alcance y dictamen

Revisión de código, SQL/dbt, política, documentación, reglas de exclusión y metadatos
locales de Git. No se abrió, enumeró ni creó ningún dataset, autorización, manifiesto
o bitácora de B. No se consultó PostgreSQL, no se importaron ni ejecutaron los scripts,
no se entrenaron modelos y no se ejecutó el test. Solo se crea este documento.

**Dictamen: compatibilidad estructural aprobada; acceso a B todavía no habilitado.**
No se encontró una discrepancia actual en esquema, lista de predictores, huellas
congeladas o autoría que exija modificar la política o el evaluador. Hay condiciones
operativas bloqueantes y limitaciones de automatización que deben cerrarse en las
etapas indicadas. Esta auditoría no acredita cobertura real de las fuentes ni
ejecución previa/ausencia física de artefactos B, pues inspeccionarlos está fuera del alcance.

Estados: **APROBADO** = propiedad comprobada estáticamente en este checkout;
**PENDIENTE** = dependencia o limitación cuya verificación no se hizo aquí;
**BLOQUEANTE** = condición que impide habilitar la etapa indicada hasta que conste su cierre.
Un bloqueo operativo no demuestra un fallo en los datos ni exige por sí solo cambiar código.

## Base de revisión y commits

- Política: `e9e0ed5d5d40d2ec43cb2edd2e3eb4a64deb7cf7`, autora **Paula Navarro**.
- Exportador y HEAD local: `03455c507886615c088f00f89c9741b023b07b9a`, autora **Paula Navarro**.
- `politica_congelada.json` y `evaluar_test_unico_b.py` tienen los mismos objetos Git
  en `e9e0ed5` y HEAD. Se comprobó mediante `git rev-parse commit:ruta`, sin leer B.
- El `commit_base` de la política es `1f1adce73c3f130290d4cf7051b73b0cf9270b96`;
  el objeto existe y corresponde a la base de 2.1, no a una autorización del test.
- La autoría de los commits se verificó localmente; no se consultó GitHub ni se certificó
  sincronización remota. No se hizo add, commit ni push.

## Controles de contrato y modelado

| Control | Estado | Justificación y ubicación |
|---|---|---|
| Destino y esquema CSV | APROBADO | Exportador, líneas 21–45 y 81–96: mismo destino que `INPUT_B` del evaluador (línea 24). Conserva las once columnas de A y añade `corte` y `fecha_corte`: trece columnas, todas las requeridas en evaluador, líneas 138–149. La ampliación es necesaria y compatible. |
| Orden exacto de los nueve predictores | APROBADO | Exportador, líneas 40–45; política, `caracteristicas`; `entrenar_baselines_logistica.py`, líneas 35–42. Siete numéricas seguidas de dos categóricas. El orden físico del CSV es el de A; el evaluador selecciona por nombres `NUMERIC + CATEGORICAL` (línea 158), por lo que ese orden físico distinto no causa incompatibilidad. |
| Tipos y valores válidos | APROBADO | `validate_csv`, exportador, líneas 113–155: encabezado exacto, campos completos, numéricos finitos, conteos/días enteros y dominios válidos; etiqueta textual 0/1. COPY produce CSV UTF-8. El evaluador convierte numéricas y categorías como A (líneas 150–156). Categóricas vacías se preservan y luego se sustituyen por `DESCONOCIDO`; no se aprende imputación con B. |
| Identificador y metadatos | APROBADO | Exportador, líneas 124–132: `USR:` más 64 caracteres hexadecimales, unicidad, corte B y fecha 2026-07-31. La seudonimización dbt usa HMAC-SHA256 en `silver_identidad_usuarios_seudonimizada.sql`, líneas 18–26. Evaluador, líneas 142–149: verifica corte, fecha, identificadores no nulos/duplicados. No usa el identificador como predictor. |
| Cardinalidad y correspondencia exacta | APROBADO | Exportador, `SQL_AUDITORIA`, líneas 54–79; ejecución, líneas 232–246: índice único de etiquetas, controles de duplicados y nulos de features, conjuntos de personas iguales por FULL JOIN, tamaños iguales/no vacíos y número de filas CSV reconciliado. No se inventa un conteo esperado de positivos B ni se revela su distribución. |
| Configuración y preprocesamiento L1 | APROBADO | Evaluador, líneas 108–126: reutiliza `make_model('l1', 1.0)`, comprueba parámetros y versiones. `make_model` de A (líneas 55–78) fija C=1, L1, liblinear, semilla 42, imputación mediana/constante, StandardScaler y OneHotEncoder. Sus bytes están cubiertos por la política. |
| Ajuste exclusivamente en A | APROBADO | `comparar_ensembles.load_data`, líneas 37–63, solo lee `DEFAULT_INPUT` de A y valida 60664/8110. El único `fit` del evaluador es `pipe.fit(X_a, y_a)` en línea 126, antes de abrir B. Las transformaciones internas del pipeline se ajustan así solo con A. Con B solo hay `predict_proba` (línea 158). No hay fit, fit_transform, búsqueda de umbral ni recalibración sobre B. |
| Umbral y economía congelados | APROBADO | Evaluador, líneas 55–61 y 159–182: verifica fracción 1/3 y supuestos Q5, 25%, Q60; contacto `>= float(Fraction(1,3))`, misma aproximación computacional usada en A. No usa 0.33 ni optimiza con B. Guarda separadas ganancia esperada y observada simulada; esta última no es retención realizada. |
| Privacidad de salidas | APROBADO | El exportador solo imprime mensajes generales y no calcula prevalencia/rendimiento; manifiesto/bitácora privados no contienen filas ni distribución. El evaluador guarda únicamente `resultado_agregado.json`, líneas 166–189. No exporta probabilidades individuales ni modelos. El CSV y el parcial sí son individuales y requieren protección local. |

Orden de predictores comprobado:

```text
eventos_ultimos_7_dias
eventos_ultimos_28_dias
cantidad_modos_distintos
dias_desde_ultimo_evento
proporcion_eventos_hora_pico
gasto_acumulado_gtq
gasto_promedio_evento_gtq
modo_mas_usado
zona_origen_mas_frecuente
```

## Temporalidad, elegibilidad y cobertura

| Control | Estado | Justificación y ubicación |
|---|---|---|
| Fecha B y ventanas semiabiertas | APROBADO | Exportador, líneas 27–29 y 205–207; `preparar_fechas` en etiquetado, líneas 205–216: B=2026-07-31, observación previa [2026-07-03, 2026-07-31), posterior [2026-07-31, 2026-08-30). No se incluyen eventos del día de corte en features. |
| Etiqueta y elegibilidad iguales a A | APROBADO | Se importa exactamente `SQL_ETIQUETAS` de A (exportador B, línea 203). En A, líneas 32–51: al menos dos eventos previos, disponibilidad de persona y abandono por cero eventos posteriores. La etiqueta depende del periodo posterior; el previo determina elegibilidad. |
| Agregados sin eventos futuros | APROBADO | `feat_abandono_cortes.sql`, líneas 166–182: filtro previo; todos los agregados y selecciones de modo/zona derivan de `eventos_previos`. Exportador, líneas 65–78, audita rango de último evento y reconcilia conteo de 28 días/último evento contra la ventana previa. No recertifica independientemente todas las features materializadas. |
| Último estado CDC anterior al corte | APROBADO | `calcular_etiquetas.py`, líneas 67–100: `commit_ts < corte`, desempate por commit_ts/seq, tarjeta Transmetro DELETE inhabilitada y disponibilidad personal mediante BOOL_OR. B reutiliza esas consultas; no introduce una regla distinta de A. |
| Normalización CDC entre etiquetas y features | PENDIENTE | Hay una asimetría real preexistente: etiquetado compara `c.op = 'DELETE'` literalmente (línea 85), mientras dbt usa `UPPER(p.op)` (línea 45). El cargador `scripts/staging/cargar_cdc_staging.py`, líneas 38–42 y 132–164, no impone CHECK de valores ni convierte op a mayúsculas. No prueba que los datos tengan minúsculas, pero no puede asegurarse equivalencia para cualquier entrada admitida. Confirmar el contrato upstream de operaciones con evidencia de procedencia antes de autorizar exportación; no cambiar A ni explorar etiquetas B. La reconciliación futura puede detectar diferencias de población, pero actuaría después de consultar B. |
| Identidad histórica y UTC | PENDIENTE | Se reutiliza la misma identidad aproximada/HMAC y convención UTC que A; `silver_identidad_usuarios.sql` deriva identidades de fuentes sin reconstrucción as-of por corte. No se puede declarar ausencia absoluta de toda influencia futura de identidad. Conservar la limitación y acreditar misma clave/procedencia de las tablas, sin abrir B en este bloque. |
| Evidencia de cobertura completa de los cuatro operadores | BLOQUEANTE | Antes de la primera consulta/exportación B debe constar certificación de ingesta completa hasta 2026-08-30 exclusivo, además del periodo previo y CDC. Exportador, líneas 284–294, solo recibe una fecha declarada y valida que no sea anterior al fin. El manifiesto registra esa declaración (línea 263); no comprueba completitud, origen ni integridad de ingesta. No se revisó aquí evidencia operativa que cierre ese requisito. No inferirlo de MAX(fecha), de actividad al final del periodo ni de población reconciliada. |

La certificación pendiente puede basarse en manifiestos, controles de ingesta y
procedencia ya disponibles, sin revelar etiquetas ni métricas B. El código permite
registrar una declaración, pero **no certifica automáticamente la cobertura**.

## Autorización, bitácoras y protección del test

| Control | Estado | Justificación y ubicación |
|---|---|---|
| Importación y --help sin activar el test | APROBADO | Ambos módulos solo importan librerías estándar y definen constantes/funciones a nivel superior. Sus guardas `if __name__ == '__main__'` (exportador 297; evaluador 210) llaman a argparse. Sin flags muestran ayuda; `--help` termina el parser antes de ejecutar. Dependencias, .env, conexiones y datos se cargan dentro de funciones operativas. Dictamen estático, sin importar/ejecutar los módulos. |
| Autorización de exportación | APROBADO | CLI exige `--exportar-b`, frase `AUTORIZO_EXPORTACION_B` y cobertura declarada (líneas 279–294). No hay archivo autenticado de consentimiento para esta etapa; es un control contra accidentes, no una garantía de permiso humano. La llamada deliberada a `exportar()` puede eludir los argumentos CLI: el control de acceso real depende del operador y credenciales. |
| Autorización posterior de test | APROBADO | Evaluador, líneas 74–88 y 196–211: exige flag/frase, archivo local con identidad/referencia de instrucción, fecha válida posterior a congelación, SHA256 de política, SHA256 de B y commit idéntico a HEAD. No genera ese archivo. La referencia no se autentica criptográficamente. No se abrió ni creó autorización alguna en esta auditoría. |
| Permiso humano para primer acceso B | BLOQUEANTE | Este bloque autoriza solo auditoría estática, no consultas/exportación ni evaluación. Debe existir una instrucción posterior explícita de exportación y, por separado, otra de evaluación. No inferir permiso de frases de ejemplo, del archivo de política ni del estado NO_EJECUTADO. Referencias: `exportacion_b.md`, dependencias; `README.md`, preparación posterior. |
| Reserva antes de primera consulta/exportación | APROBADO | Exportador, líneas 183–213: apertura exclusiva `x`, persist/flush/fsync y evento ANTES_DE_CONSULTAR_B antes de `psycopg.connect`. Los controles previos solo acceden a código/política y metadatos de rutas. No llama a main de los módulos de A importados. |
| Reserva antes de lectura del CSV B por el evaluador | APROBADO | Evaluador, líneas 94–98: reserva exclusiva persistida antes de imports/fit y antes de cualquier hash o lectura B. Evento ANTES_DE_LECTURA_B sincronizado (línea 132) precede `INPUT_B.read_bytes()` (133). La lectura del archivo de autorización es anterior a la reserva, pero no es lectura de etiquetas. |
| No sobrescribir ni reintentar silenciosamente | APROBADO | Exportador, líneas 158–174 y 240–272: rechaza artefactos previos, parcial `xb`, enlace exclusivo, manifiesto `x`, reserva persistente ante fallos. Evaluador, líneas 89–100 y 183–193: resultado/directorio exclusivos; reserva consume intento incluso si falla antes de leer B. No hay opción de forzar/reintentar. |
| Éxito de exportación certificado antes de evaluar | BLOQUEANTE | Antes de la primera lectura B por el evaluador debe cerrarse un control humano de manifiesto EXPORTADO_VALIDADO y bitácora FINALIZADO, según `exportacion_b.md`. El evaluador **no los lee ni los valida**: solo vincula el hash aportado en autorización. Exportador publica el CSV en línea 252 antes del manifiesto y FINALIZADO (254–270); un fallo entre esos pasos puede dejar un CSV final sin certificación completa. La sola existencia del CSV y su hash no bastan. Resolver el procedimiento de aceptación antes de habilitar test; no se propone ni aplica modificación del evaluador congelado. Este cierre corresponde a después de una exportación autorizada y antes del test, no a esta auditoría. |
| Exclusión simultánea entre máquinas | PENDIENTE | Modo x protege procesos que comparten el mismo sistema de archivos; no impide borrar reservas, alterar código o usar otra copia/máquina. OneDrive no ofrece aquí un bloqueo distribuido demostrado. Designar un operador y máquina, respaldar bitácoras y detenerse ante fallos; no borrar reservas para reintentar. Requiere cierre operativo antes de cualquier acceso. |
| Soporte de ejecución y hard links | PENDIENTE | El exportador publica mediante `os.link` (252); debe confirmarse soporte en el destino antes de autorizar acceso, usando solo artefactos sintéticos si se autoriza esa comprobación. La documentación registra Python de WindowsApps no operativo para comprobaciones previas. Esta auditoría es solo estática: no ejecutó py_compile, ayuda, importación ni prueba de filesystem. |

## Exclusión Git y salidas privadas

**APROBADO para las reglas del checkout actual; PENDIENTE para otros clones.**
Se leyó `.git/info/exclude:7`, que contiene `datos_modelado_local/`. `.gitignore`
versionado no incluye esa regla. No hay entradas versionadas bajo esa ruta según
`git ls-files -- datos_modelado_local`, una consulta del índice sin abrir archivos.
La regla cubre todos estos nombres definidos en el código:

| Artefacto privado bajo datos_modelado_local/fase2_2/ | Código que lo define |
|---|---|
| `dataset_corte_B.csv` y `dataset_corte_B.csv.partial` | Exportador, líneas 22–23 |
| `exportacion_b_manifiesto.json` y `exportacion_b_bitacora.jsonl` | Exportador, líneas 24–25 |
| `autorizacion_test_b.json` y `test_b_bitacora.jsonl` | Evaluador, líneas 22–23 |

El exportador valida exclusión/no versionado para sus cuatro salidas antes de conectar
(líneas 159–167). El evaluador no incorpora esa misma validación para autorización y
bitácora: su protección actual procede de la regla local leída, no de una comprobación
automática propia. `.git/info/exclude` no viaja con los commits; certificar esa exclusión
en la máquina operativa antes de acceso. Git permite forzar add de archivos ignorados:
la regla no sustituye la prohibición de publicar datos individuales.

El resultado público previsto es solo el JSON agregado en
`docs/reportes_fase2_2/test_unico_B/`; no es una salida individual y no requiere esa
exclusión. No se abrió ese directorio ni se inspeccionó su existencia.

## Huellas y posible cambio de autoría

**APROBADO: no se detectó incompatibilidad actual atribuible a la autoría.**
Se calcularon SHA256 únicamente sobre código/configuración permitidos, nunca sobre A/B:

| Archivo | SHA256 actual, igual al esperado |
|---|---|
| `politica_congelada.json` | `9f7cfe4cb20423dc02e6f11153000dfd8e42e7b0d47f523828b4ba37e5e2b5ae` |
| `entrenar_baselines_logistica.py` | `6ab6e410d72c4afcfe566bb99b92c35e3abf60b0d046f0e589bf3692c94423e2` |
| `comparar_ensembles.py` | `440e3adc7078d0a2fde3f1d7c26f65de476907d522030bd08fba73bc08cb8fd4` |
| `evaluar_test_unico_b.py` | `8f067d710085ab3b6122af426aef77a24f86b2d6ddda5deb58a8aa56cb47407e` |

El SHA256 de política coincide con `politica_congelada.sha256`; los otros tres
coinciden con `sha256_codigo`. El evaluador comprueba bytes, no el nombre de autora.
Cambiar autoría puede cambiar el identificador del commit sin cambiar estos bytes.
`commit_base` no se utiliza como commit permitido por el evaluador; no debe editarse
para sustituirlo por e9e0ed5 ni por el HEAD actual.

**PENDIENTE: vinculación de autorización al commit de ejecución.** La autorización
futura deberá llevar exactamente el HEAD aprobado cuando se ejecute (`git rev-parse HEAD`),
que en esta revisión es 03455c5 completo. Usar e9e0ed5 como `commit` con HEAD 03455c5
provocaría un rechazo seguro antes de reservar o abrir B. Si se versiona esta auditoría
u otro cambio, HEAD volverá a cambiar y la futura autorización deberá corresponder a
ese nuevo commit aprobado. No se necesita actualizar la política por ello.

**PENDIENTE: estabilidad de bytes entre checkouts.** `core.autocrlf=true` en este entorno;
las huellas son de bytes del working tree y pueden verse afectadas por finales de línea
en otros checkouts. Hoy coinciden. Si difieren en la máquina operativa, detener y revisar
representación/procedencia sin recalcular silenciosamente las huellas congeladas.
La huella de dataset A se comprobará en el futuro por el evaluador; no se releyó A aquí.

## Condiciones de cierre antes de avanzar

1. **Antes de cualquier consulta/exportación B:** autorización posterior expresa y evidencia de
   cobertura completa de los cuatro sistemas, periodo previo y CDC; confirmar el contrato
   de operaciones CDC, exclusión Git, Python/dependencias, hard links y operador/máquina únicos.
2. **Después de exportar con autorización y antes de leer B para evaluar:** acreditar éxito de
   manifiesto y bitácora sin inspeccionar filas/distribución; no aceptar un CSV final huérfano.
   La aceptación humana debe quedar documentada porque el evaluador no impone ese enlace.
3. **Antes del test único:** autorización separada vinculada a política/hash de exportación y al
   HEAD exacto aprobado; conservar reservas sin borrarlas ni intentar otra máquina tras fallo.

No se corrigió código ni se modificaron política, SHA256, evaluador, exportadores,
Fase 1, Fase 2.1, dbt o Docker. Los puntos pendientes/bloqueantes quedan documentados
para revisión; este documento no constituye autorización de acceso a B.
