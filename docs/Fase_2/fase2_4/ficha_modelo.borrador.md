# Ficha de modelo — Fase 2.4 (borrador de una página)

**Responsable:** Paolo Marroquín. Estado: arquitectura y pruebas sintéticas;
pipeline reproducido y predicciones C **todavía no generados**.
Suite actual: **41/41 pruebas sintéticas aprobadas** (25 MLOps y 16 persistencia).

| Aspecto | Especificación y evidencia disponible |
|---|---|
| Datos y unidad | Fuentes simuladas de Red Metropolitana. Unidad: persona integrada de forma aproximada y seudonimizada; Aerómetro mantiene identidad separada según contrato heredado. No se acredita identidad civil. |
| Entrenamiento | Corte A=2026-07-01, 60,664 personas, 8,110 positivos. Ventana previa 28 días, etiqueta posterior 30 días. Preprocesamiento ajustado solo con A. |
| Población C propuesta | Corte 2026-08-30; >=2 eventos en [2026-08-02,2026-08-30), algún identificador disponible a corte. Historia de identidad/CDC y disponibilidad filtradas antes de agrupar. N C aún desconocido. |
| Etiqueta histórica | Ausencia de actividad registrada en ventana posterior; no abandono real confirmado. No se genera etiqueta C para inferencia. |
| Modelo | LogisticRegression L1, C=1, semilla 42. Siete numéricas y dos categóricas; mediana, StandardScaler, imputación constante y one-hot del pipeline histórico. Sin segmento KMeans como predictor. |
| Validación A | OOF CV5 estratificada, shuffle=True, random_state=42. AP=0.482160, precisión=0.512609, recall=0.443650, Brier=0.089065, log-loss=0.296666. La misma CV participó en selección; no es validación externa independiente. |
| Test histórico B | Único, consumido el 2026-11-11; commit 931146e26c0dec88ec374bd2b8015c185fdaf90f. AP=0.440916, precisión=0.488829, recall=0.427902, Brier=0.085068, log-loss=0.281870. No repetir ni reajustar. |
| Política económica | Q5 por contacto, retención condicional 25%, valor Q60: G(p)=15p−5. Contactar si p>=1/3 exacto, sin optimización con B. Ganancia B observada simulada Q14,825; no beneficio causal realizado. |
| Persistencia pendiente | Nuevo pipeline a reproducir exclusivamente con A y guardar con hash/manifiesto. No es el objeto de memoria histórico de B. Las métricas B anteriores no demuestran identidad binaria de un futuro artefacto. |
| Fuga revisada | Contrato C excluye eventos futuros, identidades posteriores y correcciones disponibles tarde antes de deduplicar/seleccionar población. 25 pruebas sintéticas aprobadas, incluyendo relojes y límites independientes; no sustituyen conciliación con fuentes reales. |
| Limitaciones/bloqueos | certificado_origen=false; completitud y procedencia independientes no acreditadas. Identidad aproximada, llegadas tardías, cambios de población y calibración. Revisar relojes UTC/civiles y adapter antes de inferencia real. |
| Publicación | Solo IDs sintéticos/seudonimizados autorizados; nunca claves HMAC ni datos personales reales. Predicciones C privadas por defecto y revisión previa a entrega GitHub. |

Fuentes públicas existentes: [métricas A](../../reportes_fase2_2/metricas_oof.csv),
[resultado B agregado](../fase2_2/resultado_test_b.agregado.json) y
[política congelada](../fase2_2/politica_congelada.json). No se abrieron datasets.
Esta ficha no afirma métricas nuevas, aprobación docente ni despliegue completado.
