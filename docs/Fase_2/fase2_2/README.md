# 2.2 — Política económica congelada y preparación del test único

Decisión: logística L1 λ=1, C=1; contactar cuando `p >= 1/3` exacto.
B está **NO_EJECUTADO**. No ejecutar el test sin una autorización posterior explícita.

## Entregables

- [Documentación técnica](documentacion_tecnica.md): economía, resultados OOF de A, calibración, límites y protocolo B.
- [Política congelada](politica_congelada.json) y `politica_congelada.sha256`: definición y huella para vincular la autorización posterior.
- `docs/reportes_fase2_2/`: métricas OOF y por fold, curva de ganancia, calibración, comparación de políticas y configuración histórica de A.
- `docs/evidencias/Fase_2/fase2_2/`: cálculo matemático del umbral, calibración y curva de ganancia.
- `scripts/modelado/seleccionar_umbral.py`: ejecución histórica de A. No volver a ejecutar ahora: puede sobrescribir reportes/documentación.
- `scripts/modelado/evaluar_test_unico_b.py`: evaluador futuro bloqueado mediante autorización y bitácora exclusiva.
- [Exportación B — Bloque 4](exportacion_b.md): código preparado en `scripts/modelado/exportar_dataset_corte_b.py`, contrato, controles y procedimiento futuro; no ejecutado.

## Comprobaciones seguras (no entrenan ni leen A/B)

Desde la raíz del repositorio, con el entorno virtual activo:

```powershell
python -m py_compile scripts/modelado/seleccionar_umbral.py scripts/modelado/evaluar_test_unico_b.py
python scripts/modelado/seleccionar_umbral.py --help
python scripts/modelado/evaluar_test_unico_b.py --help
```

Sin flags de ejecución ambos scripts solo muestran ayuda. No se requiere crear una
autorización para inspeccionar `--help`.

En esta revisión se intentaron `py_compile` y `--help` de ambos scripts con `.venv`.
El Python base de WindowsApps no pudo iniciarse, por lo que la compilación y la
ayuda quedan pendientes de verificar desde un PowerShell con el intérprete operativo.
Sí se verificaron el JSON, las huellas, las nueve variables, la fracción 1/3 y la
existencia de las tres evidencias. No se ejecutó CV ni ajuste final ni lectura de B.

## Preparación posterior, todavía no autorizada

1. Revisar y versionar la política y el código antes de habilitar el test. El evaluador exige que estén en Git y sin cambios; este bloque no hace add, commit ni push.
2. Revisar el exportador individual B preparado y sus dependencias en [exportacion_b.md](exportacion_b.md). Su ejecución sigue pendiente de autorización separada; no se modificó el exportador de A. El CSV conserva las columnas de A y añade `corte` y `fecha_corte` para cumplir el contrato del evaluador congelado.
3. Designar una única máquina/operador. Obtener autorización expresa posterior del usuario para el test único. No crear ahora el archivo de autorización.
4. Tras esa autorización, preparar localmente `datos_modelado_local/fase2_2/autorizacion_test_b.json`, con este esquema y valores reales; los marcadores no habilitan ninguna ejecución:

```json
{
  "autorizacion": "AUTORIZO_EVALUACION_UNICA_B",
  "autorizado_por": "<operador autorizado>",
  "referencia_instruccion_usuario": "<referencia a la autorización posterior>",
  "fecha_utc": "<fecha ISO8601 con zona UTC>",
  "politica_sha256": "<SHA256 de los bytes de politica_congelada.json>",
  "commit": "<git rev-parse HEAD del código aprobado>",
  "dataset_b_sha256": "<huella certificada por el exportador B autorizado>"
}
```

La lectura de B para certificar su exportación también requiere autorización posterior;
este bloque no calcula esa huella. El archivo de autorización no es una prueba criptográfica
de consentimiento: el operador debe comprobar la instrucción referenciada.

Solo después de completar lo anterior, el comando futuro será:

```powershell
python scripts/modelado/evaluar_test_unico_b.py --ejecutar-test-b --confirmacion AUTORIZO_EVALUACION_UNICA_B
```

El evaluador reserva y sincroniza `datos_modelado_local/fase2_2/test_b_bitacora.jsonl`
antes de leer B. Ajusta exclusivamente con A y exporta únicamente
`docs/reportes_fase2_2/test_unico_B/resultado_agregado.json`. La política original
permanece intacta; bitácora y resultado reflejarán `EJECUTADO` cuando corresponda.

Cualquier fallo posterior a la reserva bloquea nuevas ejecuciones. No borrar la
bitácora ni el directorio de resultados; conservarlos y auditar. La exclusión no es
distribuida ni resistente a manipulación: no ejecutar desde otra máquina/copia de
OneDrive. No publicar datasets, autorizaciones con datos personales ni probabilidades.
