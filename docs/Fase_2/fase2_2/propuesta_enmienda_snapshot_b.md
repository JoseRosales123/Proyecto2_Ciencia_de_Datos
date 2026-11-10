# Propuesta de enmienda metodológica: evaluación única B limitada al snapshot

## Estado y alcance de la propuesta

**PROPUESTA NO APROBADA. No autoriza exportación, lectura de etiquetas, entrenamiento
final ni evaluación B.** Solo se crea este documento; no se implementan cambios funcionales.

La propuesta se apoya en [el informe de cobertura](informe_auditoria_cobertura_b.md),
[la documentación de cobertura](cobertura_temporal_b.md),
[el plan de cierre](plan_cierre_pre_test_b.md) y los contratos existentes de exportador
y evaluador. Contexto comunicado: último commit publicado 5274f82, política e9e0ed5,
corrección CDC aede6ba y B todavía no exportado ni evaluado.

No se identificó una rúbrica original verificable entre los documentos localizados
en el proyecto. Se localizó un PDF denominado `Documentacion Fase 1 Proyecto 2.pdf`,
pero no se verificó como rúbrica ni se le atribuyen requisitos. Por tanto, este
documento **no afirma conformidad con una rúbrica ni inventa sus exigencias**.
Queda pendiente obtener/verificar el enunciado aplicable y, si exige cobertura de
origen certificada o no admite este alcance, solicitar validación académica expresa.
Si la exigencia resulta incompatible y no se autoriza una excepción, B seguirá bloqueado.

## Evidencia disponible y límites conocidos

| Evidencia existente | Qué respalda | Qué no respalda |
|---|---|---|
| Reconciliación Bronze, manifiestos Batch/CDC y agregados Staging/Silver | Archivos de ingesta identificados mediante hashes declarados y conteos, consistencia interna de las capas bajo los controles revisados. | Completitud independiente o autenticidad del universo original de eventos. |
| Auditoría `20261110T040649Z_eec3c7f64818` | 58 días por operador, 28 previos y 30 posteriores; cero diferencias diarias, fechas nulas y días sin actividad Silver. Cero bloqueos técnicos automáticos. | Que cada día contenga todos los eventos que debieron existir, ni todas sus horas finales. |
| Numeración Batch y offsets Streaming | Rangos observados continuos, sin duplicados/huecos en los controles ejecutados. | Que el productor haya recibido el origen completo o que esos rangos sean definitivos. |
| Manifiestos Batch/CDC | Conteos declarados iguales a metadatos Parquet; hashes de manifiestos y hashes declarados de origen registrados. | Que un hash declarado se haya contrastado con un certificado independiente de generación. |
| Corrección CDC local y 10/10 pruebas sintéticas aprobadas, según estado confirmado | Tratamiento de variantes DELETE alineado con dbt, sin cambiar retrospectivamente A; cobertura de casos sintéticos de disponibilidad y frontera temporal. | Completitud del historial real, suficiencia del estado inicial o datos sin defectos. |
| Informe y resultado oficial de auditoría | `PENDIENTE_CERTIFICACION_ORIGEN`, `certificado=false`. | Autorización implícita para usar B ni certificación positiva. |

El snapshot se considera sintético en el alcance propuesto del proyecto, pero **no
se ha reconstruido su cadena completa de generación**. El generador heredado
configura SEMILLA=2026, INICIO=2026-06-01 y DIAS=45; no explica los archivos ampliados
hasta agosto. No se conoce la versión/configuración real que produjo esos archivos.
La existencia de un generador sintético no prueba la procedencia exacta de cada archivo.

Tampoco existe cierre verificable de llegadas tardías, ampliaciones o correcciones
del origen. Que un productor haya entregado el archivo disponible o no tenga mensajes
pendientes no demuestra que ese archivo fuera el universo definitivo. Permanecen
limitaciones de identidad aproximada, estado inicial CDC y trazabilidad entre
snapshot DB y metadatos de archivos. No se cuantifica un efecto desconocido.

## Dos decisiones distintas, nunca equivalentes

| Tipo de respaldo | Significado | Situación/propuesta |
|---|---|---|
| `CERTIFICACION_DE_ORIGEN` | Evidencia suficiente de generación/extracción completa, procedencia, cobertura temporal y cierre del origen. | No acreditada. No debe declararse ni simularse mediante una fecha. |
| `ACEPTACION_LIMITADA_DEL_SNAPSHOT` | Decisión prospectiva y expresa de medir desempeño respecto de actividad registrada en una versión identificada del snapshot, aceptando incertidumbre de origen/completitud. | Se propone para revisión; no está concedida y no convierte la auditoría en certificación. |

La integridad técnica es evidencia a favor de utilizar consistentemente los datos
disponibles. No reemplaza ninguna de las dos decisiones. La aceptación limitada
acepta un **alcance inferencial restringido**, no declara solucionado el defecto de procedencia.

## Elementos que no se enmiendan

- Regresión logística L1, λ=1 y C=1, con los hiperparámetros congelados.
- Las nueve características, su selección y orden, y el preprocesamiento de 1.4.
- Umbral exacto 1/3, contacto si p >= 1/3; sin optimización de umbral ni calibración con B.
- Escenario económico: Q5 por contacto, retención condicional del 25%, valor Q60.
- Corte B=2026-07-31; ventana previa [2026-07-03, 2026-07-31) y posterior
  [2026-07-31, 2026-08-30), en las convenciones temporales ya implementadas.
- Elegibilidad, definición de etiqueta y disponibilidad CDC de la versión B corregida.
- Ajuste del modelo y preprocesamiento exclusivamente con A; B nunca sirve para ajustar.
- Test único y controles de autorización, reserva persistente y no sobrescritura.
- `politica_congelada.json`, su SHA256, `evaluar_test_unico_b.py` y el resultado histórico
  de auditoría con `certificado=false` permanecen intactos.

Para Aerómetro, la ventana posterior local equivale a [2026-07-31 06:00 UTC,
2026-08-30 06:00 UTC). La enmienda no mueve ese límite para acomodar faltantes.
La diferencia histórica de capitalización CDC entre A y B sigue documentándose;
no se recalcula A para ocultarla.

## Protocolo prospectivo propuesto, sujeto a aprobación

1. **Revisión metodológica y académica.** Aprobar o rechazar explícitamente este alcance,
   antes de acceder a etiquetas B. Verificar la rúbrica/enunciado; obtener conformidad
   académica cuando sus exigencias lo requieran. Si no se conoce su compatibilidad,
   mantener ese requisito pendiente. La aprobación de la propuesta no autoriza ejecutar.
2. **Identificación de la versión aceptada.** Designar un único snapshot y custodio,
   asociando el informe agregado, manifiestos y sus huellas, inventario/versiones de
   fuentes y referencia del snapshot DB. Registrar qué es declarado y qué se verificó.
   Los conteos o un nombre de snapshot no son una huella de contenido suficiente por sí solos.
   Si no puede vincularse la versión a la exportación, detenerse para resolverlo.
3. **Implementación posterior y revisión.** Solo tras aprobar el diseño, implementar
   el modo explícito del exportador descrito abajo y probarlo con fixtures. Aprobar
   su diff/commit y las protecciones antes de autorizar consultas o exportación.
   No sustituir el requisito actual con un simple permiso verbal para saltarlo.
4. **Acta privada de aceptación.** Registrar la aprobación expresa, alcance y riesgos,
   responsables, referencias académicas aplicables, hashes de política/propuesta y
   evidencias agregadas, identidad del snapshot y HEAD aprobado. No crear esa acta
   en este bloque. Mantener `certificado_origen=false` y `evaluacion_b=NO_EJECUTADO`.
5. **Autorización separada de exportación.** Confirmar equipo/operador únicos, rutas
   excluidas/no versionadas, ausencia de artefactos previos por metadatos de rutas,
   versiones y pruebas aprobadas. Solo una instrucción posterior explícita habilitaría
   la exportación mediante el nuevo modo; no se usa una fecha de cobertura ficticia.
6. **Reserva anterior al primer acceso individual.** El exportador debe crear y sincronizar
   su bitácora exclusiva antes de conectar/leer fuentes para etiquetar B, vinculando acta,
   modo, snapshot y hashes. Mantener un snapshot consistente durante la transacción y
   comprobar las condiciones técnicas aceptadas. Ante cambio de versión o discrepancia,
   fallar sin trasladar automáticamente la aceptación a otros datos.
7. **Aceptación de exportación terminada.** Después de una exportación autorizada,
   revisar solo su manifiesto y bitácora privados: validación técnica completa,
   modo correcto y cierre FINALIZADO con hash coincidente. No abrir filas, etiquetas,
   predicciones ni distribución de positivos. Un CSV final sin cierre completo no basta.
8. **Autorización separada del test único.** Vincular la autorización existente del
   evaluador al HEAD aprobado de ejecución, política y hash certificado técnicamente
   por la exportación; adjuntar referencia inequívoca al acta limitada y a su aceptación
   de cierre. No confundir ese hash de archivo con certificación de completitud.
9. **Ejecución futura única y publicación agregada.** El evaluador congelado reservaría
   su bitácora antes de leer bytes de B, ajustaría solo con A y evaluaría al umbral fijo.
   No modificar decisiones tras ver resultados. Publicar solo agregados con las
   advertencias de validez; preservar todos los artefactos y el intento consumido.

Cada paso depende del cierre del anterior. La presencia de este documento no satisface
ninguno de los permisos. No se crean ahora actas, autorizaciones, reservas ni datasets.

## Cambio mínimo futuro en el exportador: diseño, no implementación

El contrato actual exige `--cobertura-confirmada-hasta`, descrito como cobertura
completa certificada, y una fecha igual o posterior a 2026-08-30. El script registra
la declaración pero no comprueba su respaldo. **No permite representar honestamente
la aceptación limitada usando ese mismo parámetro sin cambiar su contrato.**

Se propone añadir una bifurcación explícita, cerrada por defecto:

| Modo propuesto | Requisitos verificables antes de consultas | Registro de salida |
|---|---|---|
| `CERTIFICACION_DE_ORIGEN` | Mantener el requisito de cobertura-confirmada-hasta con respaldo real y autorización; no rebajar su significado. | Tipo de respaldo, referencia a certificado y fecha declarada según contrato. |
| `ACEPTACION_LIMITADA_DEL_SNAPSHOT` | Opción distinta, confirmación específica y acta privada aprobada, vinculada por SHA256 a esta enmienda, política, HEAD y versión del snapshot/evidencias; comprobar campos y coincidencias. | Tipo de respaldo, `certificado_origen=false`, identificador/hash del acta, snapshot y límites de observación utilizados. **Sin fecha de cobertura certificada ficticia.** |

Los modos deben ser mutuamente excluyentes; ningún modo implícito, automático o
activado por que falte evidencia. Rechazar opciones de certificación en el modo limitado,
actas incompletas, hashes/commit incorrectos, aprobación ausente o versiones no vinculadas.
Una frase CLI por sí sola no basta: el acta comprobable documenta el consentimiento,
aunque su autenticidad sigue requiriendo custodia y revisión humana.

La modificación funcional se limitaría a validación de argumentos/acta y metadatos
de reserva/manifiesto; conservar SQL de eventos/etiquetas, ventanas, corrección CDC,
validaciones, rutas privadas y bloqueos de ejecución/repetición. El manifiesto debería
separar `integridad_exportacion=VALIDADA` de `tipo_respaldo` y `certificado_origen`;
FINALIZADO no significaría certificación del origen.

Las pruebas sintéticas futuras deberán cubrir ambos modos, exclusión mutua, falta
de aprobación, acta alterada, discrepancia de política/commit/snapshot, repetición,
errores previos a conexión y conservación de la lógica de etiquetas. No usar B para probar.

Cambiar el exportador altera su SHA256 y exige nuevo commit/revisión, preservando
03455c5 y aede6ba como antecedentes. El manifiesto futuro registrará los nuevos bytes.
El exportador no está en `sha256_codigo` de la política congelada; este diseño no
necesita cambiar la política e9e0ed5 ni su sidecar. Versionar la enmienda/código cambiará
HEAD: la futura autorización del evaluador deberá corresponder al HEAD aprobado final.

El evaluador congelado no valida automáticamente actas de aceptación limitada ni
manifiestos de exportación. Se propone conservarlo intacto y exigir aceptación humana
documentada antes de emitir su autorización. Su archivo de autorización comprueba
solo los campos actuales; esa limitación no debe presentarse como un control nuevo
automatizado. Si la revisión exige automatizarlo dentro del evaluador, requeriría otra
propuesta de modificación y revisión de sus huellas; queda fuera de esta enmienda mínima.

## Evidencia privada y bitácoras obligatorias propuestas

Todo registro individual o de autorización permanecería en una ubicación privada
excluida de Git, preferentemente bajo `datos_modelado_local/fase2_2/`, verificando
la regla en la máquina elegida antes de crear artefactos. No se prescribe todavía
un nombre operativo ni se crea un archivo que pudiera habilitar el test accidentalmente.

El acta propuesta contendría: versión e identificador; decisión pendiente/aprobada
sin ambigüedad; tipo `ACEPTACION_LIMITADA_DEL_SNAPSHOT`; responsable y referencia
a instrucción expresa; fecha UTC; alcance/limitaciones aceptadas; validación académica
si procede; identificador de snapshot y versiones fuente; hashes de enmienda,
política y evidencias técnicas; HEAD/exportador aprobados; `certificado_origen=false`.
No contendría valores individuales, prevalencia, probabilidades ni métricas B.

Antes de exportar, la reserva exclusiva conservaría referencia/hash del acta y del
snapshot aceptado, equipo/operador y evento anterior al acceso. Los manifiestos y
bitácoras finales conservarían el modo y la misma vinculación. No recalcular por fuera
del flujo autorizado el hash del CSV B: hacerlo también abre el test. El hash para la
autorización futura se tomaría del manifiesto y cierre técnico; el evaluador cotejaría
los bytes reales después de su propia reserva.

Mantener creación exclusiva, flush/fsync, directorios nuevos y rechazo de resultados
previos. Un fallo consume la reserva correspondiente y exige auditoría: no borrar
bitácoras, sobrescribir archivos, reintentar automáticamente ni utilizar otra copia
del repositorio. La exclusión es local; OneDrive no garantiza bloqueo distribuido.
Un custodio conservaría respaldo de actas/bitácoras y una única máquina operativa.

## Validez e interpretación del resultado futuro

AP mediría ranking respecto de etiquetas de ausencia de actividad **registrada en
el snapshot**. Precisión y recall describirían esa clasificación al umbral fijo,
no abandono real confirmado. Faltantes o tardíos pueden producir positivos aparentes,
alterar elegibilidad y features, y sesgar métricas en dirección/magnitud desconocidas.

La ganancia esperada `sum(15p-5)` depende además de probabilidades interpretables y
supuestos económicos; la calibración observada en A no garantiza calibración en B.
La ganancia observada simulada `15TP-5(TP+FP)` usaría etiquetas del snapshot y una
retención hipotética del 25%, no retenciones ni beneficio causal realizados.

Texto propuesto para el informe final, solo si la enmienda y ejecución se aprobaran:

> La evaluación única se realizó bajo aceptación limitada de un snapshot identificado,
> sin certificación independiente de completitud del origen ni cierre acreditado de
> llegadas tardías. Las etiquetas representan ausencia de actividad registrada en ese
> snapshot. AP, precisión, recall y ganancias simuladas son condicionales a dichas
> etiquetas y a los supuestos económicos; no acreditan abandono real, validez externa
> ni ausencia de sesgo por faltantes. Modelo, preprocesamiento y umbral se fijaron antes
> de acceder al test; no se utilizaron sus resultados para ajustarlos.

Una ejecución única preserva la disciplina de evaluación, pero no corrige la falta de
procedencia ni transforma este snapshot en un test de representatividad demostrada.

## Decisiones pendientes antes de continuar

- Aprobar o rechazar expresamente el alcance limitado y las advertencias; hoy no está aprobado.
- Verificar rúbrica/enunciado y resolver validación académica cuando corresponda; no afirmar cumplimiento sin evidencia.
- Definir y vincular de forma verificable el snapshot que se aceptaría; no aceptar versiones móviles o indeterminadas.
- Aprobar el diseño del modo diferenciado y, en otro bloque, autorizar su implementación y pruebas sintéticas.
- Revisar/versionar la enmienda y cualquier cambio aprobado antes de emitir actas operativas.
- Autorizar separadamente exportación y evaluación única, manteniendo aceptación de cierre y custodia privada.

Hasta esos cierres permanece vigente el procedimiento actual, que no habilita
exportar sin respaldo de cobertura. `resultado.json` conserva
`PENDIENTE_CERTIFICACION_ORIGEN` y `certificado=false`; esta propuesta no lo modifica
ni lo reclasifica. No se consultó PostgreSQL, abrió B, entrenó ni evaluó ningún modelo,
ni se hicieron add, commit o push durante la preparación documental.
