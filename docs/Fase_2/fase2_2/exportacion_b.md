# Bloque 4 — Preparación del exportador de B

Se preparó `scripts/modelado/exportar_dataset_corte_b.py` mediante revisión de código.
**No se ejecutó el exportador, no se abrió ningún archivo B, no se consultó PostgreSQL
y no se generó un dataset ni una huella de B.** La exportación y el test siguen
requiriendo autorizaciones posteriores separadas. Política, SHA256 y evaluador permanecen intactos.

## Definición reutilizada y ventanas

La unidad es PERSONA aproximada, representada por `usuario_seudonimo`. Se reutiliza
la relación Silver existente; no se recalculan identidades ni claves. El SQL de identidad
integra aproximadamente identificadores numéricos de Transmetro/Transurbano/MetroRiel
y mantiene separado Aerómetro; la seudonimización usa `USR:` más HMAC-SHA256 con la
clave ya empleada en Silver. No se lee ni publica esa clave.

El exportador importa, solo al autorizarse su ejecución, `SQL_EVENTOS`, las consultas
CDC/disponibilidad y `preparar_fechas` de `scripts/etiquetado/calcular_etiquetas.py`,
y `SQL_ETIQUETAS` de `scripts/modelado/exportar_dataset_corte_a.py`. No llama a sus
funciones `main()` ni cambia esos archivos. Se conserva exactamente la elegibilidad:
al menos dos abordajes previos y al menos un identificador disponible. Una última
operación CDC `DELETE` anterior al corte inhabilita esa tarjeta Transmetro; sin
historial no se considera automáticamente eliminada.

| Uso | Inicio incluido | Fin excluido |
|---|---|---|
| Features y elegibilidad previa (28 días) | 2026-07-03 | 2026-07-31 |
| Eventos de los últimos siete días | 2026-07-24 | 2026-07-31 |
| Etiqueta posterior (30 días) | 2026-07-31 | 2026-08-30 |
| Estado CDC de elegibilidad | Historial disponible | 2026-07-31 |

B es el corte **2026-07-31**. `abandono=1` significa cero abordajes válidos en la
ventana posterior; `abandono=0` significa al menos uno. La etiqueta usa únicamente
esa ventana para determinar el abandono; los eventos previos solo determinan elegibilidad.

Las características se leen de `features.feat_abandono_cortes` para B y su fecha exacta.
La definición dbt `eventos_previos` restringe todos los agregados, modos y zonas a
`fecha >= fecha_corte - 28 días AND fecha < fecha_corte`; no utiliza la etiqueta ni
eventos posteriores. Se preservan reglas de desempate de modo/zona, montos y horarios.
El exportador comprueba el rango de `ultimo_evento_previo` y reconcilia el conteo de
28 días y el último evento contra los eventos de la misma ventana.

Esto verifica la lógica temporal del código y añade auditorías para la ejecución futura;
no certifica ahora los valores materializados en la base ni que Silver no haya cambiado.
La identidad es aproximada y su tabla no es una reconstrucción histórica completa a
cada corte: se mantiene la misma limitación de A. Se conserva la convención UTC de A.

## Contrato del CSV y compatibilidad estática

Destino fijo y privado: `datos_modelado_local/fase2_2/dataset_corte_B.csv`.
Se conservan las once columnas de A, en el mismo orden, y se agregan dos metadatos
que el evaluador congelado exige. No puede producirse un CSV de solo once columnas
y cumplir simultáneamente ese contrato sin modificar el evaluador; por eso se usa
esta ampliación explícita a trece columnas:

```text
usuario_seudonimo
eventos_ultimos_7_dias
eventos_ultimos_28_dias
modo_mas_usado
cantidad_modos_distintos
dias_desde_ultimo_evento
proporcion_eventos_hora_pico
zona_origen_mas_frecuente
gasto_acumulado_gtq
gasto_promedio_evento_gtq
abandono
corte
fecha_corte
```

`corte` es siempre `B` y `fecha_corte` siempre `2026-07-31`. El CSV usa UTF-8 y se
ordena por seudónimo como A. Las nueve características coinciden exactamente con la
lista de la política; los metadatos y el identificador no son predictores. No se hace
imputación, escalado ni codificación al exportar: el evaluador aplicará el pipeline
ajustado exclusivamente en A. Los valores categóricos ausentes se preservan como
vacíos, compatibles con la sustitución constante del evaluador.

Por revisión estática, el destino y los trece nombres satisfacen todos los campos
requeridos por `evaluar_test_unico_b.py`. El manifiesto privado proporciona
`dataset_b_sha256` para vincular la autorización futura del test. No se ejecutó
el evaluador para comprobarlo y no se modificó su código ni la política congelada.

## Controles preparados

- Ausencia de eventos sin identidad, seudónimos HMAC con formato válido, no nulos y únicos.
- Población elegible no vacía y cardinalidad igual a features, sin personas exclusivas de uno u otro conjunto. No se fija un número de positivos ni se consulta su distribución.
- Coincidencia de conteo previo y último evento entre features y eventos anteriores al corte, con ventanas semiabiertas.
- Encabezado y número de campos exactos; etiqueta binaria; numéricos finitos; conteos/días enteros; dominios de actividad, diversidad, recencia y proporción válidos.
- Igualdad entre filas exportadas y población reconciliada, comprobada internamente sin imprimir conteos.
- Una sesión UTC y un snapshot `REPEATABLE READ`. Solo se crean tablas/índice temporales; siempre se ejecuta `ROLLBACK`. No se modifica ninguna tabla permanente ni se ejecuta dbt.
- Salidas fijas, excluidas y no versionadas en Git; si la exclusión no está vigente, el proceso se niega a consultar datos. En este checkout se verificó la exclusión local en `.git/info/exclude`; no se propaga automáticamente a otros clones.
- Flag y frase de confirmación; declaración explícita de cobertura completa; bloqueo si ya existen autorización, reserva o resultados del test B.
- Bitácora propia con creación exclusiva antes de conectar a PostgreSQL. Un fallo conserva los artefactos y exige revisión; no existe opción automática de sobrescritura/reintento.
- Escritura `.partial` exclusiva, validación privada, SHA256 y publicación mediante enlace exclusivo. Si el destino existe o el sistema de archivos no soporta hard links, falla sin reemplazarlo. La exclusión es local, no distribuida mediante OneDrive; usar una sola máquina/operador y respaldar los artefactos.

No se imprimen filas, etiquetas, identificadores, conteos de positivos/negativos,
prevalencia ni rendimiento. Los errores de base/librerías se sustituyen por un mensaje
genérico para evitar filtrar valores o credenciales. No se calculan probabilidades,
métricas, umbrales ni modelos.

## Dependencias previas a una exportación futura

1. Autorización posterior explícita para consultar y exportar B, distinta de la autorización del test único.
2. Python con `psycopg` y `python-dotenv`; `.env` local de A y acceso al mismo PostgreSQL. Las credenciales y la clave de seudonimización no se publican.
3. Fuentes Silver, identidad seudonimizada, historial CDC y `features.feat_abandono_cortes` ya disponibles y coherentes. El exportador no reconstruye ni ejecuta modelos dbt.
4. Certificación operativa de ingesta completa de los cuatro sistemas durante los 30 días posteriores, hasta **2026-08-30 exclusivo**, y disponibilidad histórica previa/CDC. El parámetro de cobertura registra una declaración del operador, no una prueba automática. Un máximo de fecha observado no demuestra integridad; falta de eventos por sí sola no distingue abandono de ingesta incompleta.
5. Revisar y versionar el exportador antes de ejecutarlo, designar un operador/máquina y conservar la procedencia/snapshot de los datos. El manifiesto registra commit y hashes de los seis archivos fuente; repetir sobre fuentes modificadas no garantiza idénticos bytes.
6. Confirmar exclusión de todos los archivos locales en el clon que se usará. No autorizar el test mientras falte un manifiesto `EXPORTADO_VALIDADO` y bitácora `FINALIZADO`, o haya un fallo pendiente de auditoría.

## Comprobaciones permitidas ahora

Desde la raíz, con Python operativo:

```powershell
python -m py_compile scripts/modelado/exportar_dataset_corte_b.py
python scripts/modelado/exportar_dataset_corte_b.py --help
git check-ignore datos_modelado_local/fase2_2/dataset_corte_B.csv
```

Las dos primeras no consultan datos ni cargan `.env`. Sin `--exportar-b`, el script
solo muestra ayuda. `git check-ignore` comprueba la regla sin leer el CSV.

En este bloque se intentaron ambas comprobaciones de Python con `.venv`; el Python
base de WindowsApps no pudo iniciarse. Sintaxis y `--help` quedan pendientes de
verificación desde un intérprete operativo. La revisión estática, exclusión de las
cuatro salidas y ausencia de cambios en política/evaluador sí se comprobaron.

## Procedimiento futuro: no ejecutar en este bloque

Solo después de certificar las dependencias y recibir autorización de exportación:

```powershell
python scripts/modelado/exportar_dataset_corte_b.py --exportar-b --confirmacion AUTORIZO_EXPORTACION_B --cobertura-confirmada-hasta 2026-08-30
```

Este comando sí consulta datos y etiquetas B; se muestra únicamente como procedimiento
futuro. No se ejecutó. La fecha de cobertura es un fin exclusivo, no una fecha a la
que se recortan artificialmente fuentes incompletas.

Las únicas salidas son privadas en `datos_modelado_local/fase2_2/`:

- `dataset_corte_B.csv`: individuos y etiquetas, nunca publicar ni abrir para explorar.
- `exportacion_b_manifiesto.json`: SHA256 del CSV, columnas, ventanas, commit, hashes fuente y verificaciones, sin distribución.
- `exportacion_b_bitacora.jsonl`: reserva y eventos de exportación, sin filas ni distribución.
- `dataset_corte_B.csv.partial`: solo mientras se exporta o si un fallo requiere revisión; no es entrada válida para el evaluador.

No borrar ni sobrescribir artefactos tras un fallo; auditar antes de decidir cualquier
acción. La bitácora de exportación es independiente de `test_b_bitacora.jsonl`: exportar
no ejecuta ni reserva una evaluación. No se genera `autorizacion_test_b.json`; preparar
ese archivo y ejecutar el test requerirá una instrucción explícita posterior.
