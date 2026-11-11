# Propuesta de enmienda metodológica: evaluación única B limitada al snapshot

## Estado y alcance

**BORRADOR PARA REVISIÓN. APROBACIÓN DE ENMIENDA: PENDIENTE.** No autoriza
exportación, lectura de etiquetas B, entrenamiento final ni evaluación.

Último commit publicado comunicado: `789d2ed`. El modo
`ACEPTACION_LIMITADA_DEL_SNAPSHOT` ya está implementado en el exportador, con
**15/15 pruebas sintéticas aprobadas según el estado confirmado**; no se repitieron
ahora. Implementación y pruebas no equivalen a aprobación metodológica ni permiso
operativo. B nunca exportado ni evaluado según el estado comunicado.

Se apoya en [el informe de cobertura](informe_auditoria_cobertura_b.md),
[los modos y contrato vigentes](modos_exportacion_b.md) y el
[descriptor borrador](descriptor_snapshot_b.borrador.json). Los textos históricos
que presentaban este modo como diseño futuro quedan actualizados por este documento.

## Rúbrica original 2.2 y controles adicionales

Fuente: transcripción de la rúbrica original de «Proyecto 2 Red Metropolitana»
comunicada por el usuario; no se atribuye una revisión independiente del original.
El apartado 2.2 vale 12 puntos y exige:

| Requisito | Entregable actual o cierre pendiente |
|---|---|
| Derivar el umbral para contacto Q5, retención 25% y valor Q60 | Cuenta: 0.25 × 60 × p − 5 = 15p − 5; contactar desde p ≥ 5/15 = 1/3. No contactar da cero; el empate da cero y se contacta según política. |
| Elegirlo usando validación cruzada de A | Cinco folds y resultados OOF existentes contrastan la política económica con alternativas. El 1/3 se adopta por rentabilidad y respaldo OOF, sin afirmar optimización empírica del umbral. |
| Entrenar con todo A y evaluar una única vez en B | Pendiente; el evaluador congelado implementa ajuste solo con A y predicción en B al umbral fijo. |
| Documentar fecha, commit, métrica, matriz y ganancia | El evaluador está preparado para registrar fecha UTC, commit, métricas, TP/FP/FN/TN y ganancias en quetzales; aún no hay resultados B. |
| Explicar deterioro frente a validación sin reajustar | Pendiente de comparar agregados B con OOF de A, sin volver a ajustar ni afirmar causas no demostradas. |

La certificación externa de completitud del origen y la restauración completa del
respaldo son **controles adicionales propios, no requisitos explícitos de esta
rúbrica**. Su ausencia no se presenta como resuelta: se propone aceptarla como
limitación, sin prolongar auditorías para cerrar 2.2. La procedencia original sigue
sin acreditarse y `certificado_origen=false` permanece vigente.

El contrato operativo sí exige acta, hashes, HEAD, evidencias permitidas y
autorizaciones. Son controles propios implementados que se conservan. El campo
`validacion_academica` admite `NO_REQUERIDA_JUSTIFICADA` con referencia no vacía:
el equipo deberá justificar expresamente su aplicabilidad con esta rúbrica antes
de usarlo. No representa aprobación docente ni se registra ahora como decisión
obtenida. Si existe otra exigencia académica aplicable, deberá respetarse.

## Alcance prospectivo y antecedentes separados

Se propone aceptar el **estado disponible de la base `red_metropolitana_p2` que
capture la futura transacción consistente REPEATABLE READ de exportación B**.
Todavía no existe captura de exportación ni se conoce su fecha o identificador de
transacción. El entorno concreto, custodio, máquina/operador y control de escritores
deben quedar delimitados antes de ejecutar. La consistencia transaccional no prueba
inmutabilidad histórica ni igualdad con antecedentes.

- Auditoría del **10 de noviembre**: `20261110T040649Z_eec3c7f64818`, fecha
  `2026-11-10T04:06:49.332515+00:00`. Su `resultado.json` tiene SHA256
  `3066d1aab88fda0248cd6f0b5f13c0dff060c5e16e0370aea557f66fdef7489e`.
  Los demás hashes de reportes y manifiestos existentes permanecen en el descriptor.
  La auditoría acredita los controles de integridad interna revisados, no
  completitud independiente. Conserva `PENDIENTE_CERTIFICACION_ORIGEN` y certificado falso.
- Respaldo del **11 de noviembre**: `20261111T060925Z_3dfebab0`, creado
  `2026-11-11T06:09:25Z`, formato `pg_dump -Fc`, 313537281 bytes, SHA256
  `3c744ae115df1fab32b67dc5d5c9fc1474be1791a721720a94aa64b4c5721a37`.
  Cotejo Docker/Windows y catálogo `pg_restore --list` confirmados por el usuario;
  no restaurado. Su ruta privada y manifiesto se referencian separadamente en el
  descriptor, fuera de `evidencias`; no se abrieron en esta revisión.

**No está demostrada ni se presupone igualdad entre auditoría, dump y futura
exportación.** El ID existente identifica el descriptor documental. Su campo
`fecha_snapshot_utc` conserva la fecha de evidencia histórica, con alcance explícito;
no se transforma en una fecha ficticia de exportación. La futura captura permanece
sin fecha ni identificador asignados.

## Implementación vigente y límites del contrato

Los modos son explícitos y mutuamente excluyentes. El modo certificado requiere
cobertura completa declarada hasta el fin de la ventana; no se utilizará para
representar esta aceptación limitada. El modo limitado exige:

- `--aceptacion-limitada-del-snapshot`, confirmación
  `AUTORIZO_EXPORTACION_B_SNAPSHOT_LIMITADO`, `--acta-sha256` y `--snapshot-id`;
  rechaza `--cobertura-confirmada-hasta`.
- Acta privada real en `datos_modelado_local/fase2_2/acta_aceptacion_snapshot_b.json`,
  excluida y no versionada, aprobada solo tras instrucciones humanas expresas.
  Exige versión 1, ID, estado APROBADA, tipo limitado, certificado falso,
  evaluación NO_EJECUTADO, aceptación de limitaciones, responsable, referencias de
  aprobación y exportación, validación académica justificada y fecha UTC válida.
- Coincidencias de hashes de propuesta, política y exportador, y HEAD aprobado.
  Propuesta, política, sidecar y exportador deben estar versionados y sin cambios.
- Objeto `snapshot` con ID coincidente, descripción no vacía, fecha con zona no
  posterior a aprobación y evidencias no vacías con rutas/hashes permitidos.
  `snapshot_sha256` corresponde al objeto exacto serializado con
  `json.dumps(snapshot, sort_keys=True, separators=(',', ':'), ensure_ascii=False)`
  y codificado UTF-8, no al hash del dump ni necesariamente al archivo JSON bruto.

Solo admite reportes agregados JSON/JSONL/CSV dentro de
`docs/reportes_fase2_2/cobertura_fuentes/` y manifiestos JSON de `bronze/_manifests/`,
con rutas resueltas dentro de esas áreas, sin duplicados y hashes coincidentes.
La referencia al dump no amplía esa lista. El validador acepta campos documentales
adicionales, pero no comprueba identidad de la base activa con el respaldo ni impone
la semántica del alcance prospectivo. Esa delimitación requiere revisión humana.

El descriptor sigue `BORRADOR_NO_OPERATIVO`, `utilizable_para_exportacion=false` y
aprobación `PENDIENTE`. Compatibilidad estructural no equivale a habilitación.
No hacen falta cambios de código para representar este alcance honestamente.
El evaluador congelado no valida automáticamente el acta ni el manifiesto: su
aceptación humana debe preceder a la autorización separada del test.

## Secuencia posterior, todavía no autorizada

1. Revisar esta propuesta y descriptor; concretar entorno, custodio y control de
   escritores, y justificar si corresponde `NO_REQUERIDA_JUSTIFICADA`.
2. Obtener aprobación humana expresa del alcance limitado y de sus advertencias.
   Esta aprobación no autoriza por sí sola exportación ni evaluación.
3. Tras la revisión y autorización correspondientes, versionar los documentos y
   fijar HEAD antes de crear actas operativas y sus hashes. No se hace en este bloque.
4. Obtener autorización separada de exportación y solo entonces registrar el acta
   privada real con las referencias y huellas exigidas. Confirmar máquina/operador
   únicos, rutas privadas, ausencia de artefactos previos por metadatos y entorno
   compatible. No crear aún `autorizacion_test_b.json`: bloquearía la exportación.
5. Ejecutar únicamente la exportación autorizada en modo limitado. El exportador
   reserva antes de conectar, usa una transacción consistente y registra el cierre.
6. Aceptar humanamente manifiesto y bitácora con `EXPORTADO_VALIDADO`, FINALIZADO,
   certificado falso y hash coincidente, sin explorar etiquetas o filas.
7. Obtener autorización separada del test único ligada al HEAD, política y hash B
   tomado del cierre de exportación; referenciar la aceptación limitada y su cierre.
   El evaluador ajustaría con todo A y evaluaría B una sola vez.
8. Publicar únicamente agregados: fecha/commit, métricas, matriz y ganancias;
   comparar con OOF y explicar deterioro sin reajustar.

Conservar reservas y artefactos ante fallos: no borrar, sobrescribir ni reintentar
automáticamente. La exclusión es local; OneDrive no aporta bloqueo distribuido.

## Limitaciones y decisiones que permanecen congeladas

Se conservan L1 C=1, las nueve características y preprocesamiento, umbral exacto
1/3, economía, ventanas, etiquetas y SQL. No se recalcula A ni se usa B para ajustar.
La diferencia histórica de capitalización CDC entre A y B sigue siendo una limitación.

Las etiquetas describirían ausencia de actividad registrada, no abandono real
certificado. Se desconoce el efecto de faltantes, llegadas tardías, estado inicial
CDC y procedencia incompleta. AP, precisión y recall serían condicionales a esas
etiquetas. La ganancia esperada `sum(15p-5)` depende de probabilidades interpretables;
`15TP-5(TP+FP)` es ganancia observada simulada con retención hipotética del 25%,
no beneficio causal realizado. Una evaluación única no corrige estas limitaciones.

No quedan auditorías adicionales obligatorias propuestas antes de solicitar revisión
y aprobación del alcance. Solo queda concretar los responsables/entorno y someter
el alcance y la justificación académica a decisión humana. Versionado, acta,
autorizaciones y comprobaciones operativas pertenecen a etapas posteriores.

En este cierre solo se actualizan propuesta y descriptor. No se crean actas,
autorizaciones ni reservas; no se consulta PostgreSQL ni se leen datasets o etiquetas,
no se exporta, entrena ni evalúa, y no se hace git add, commit o push.
