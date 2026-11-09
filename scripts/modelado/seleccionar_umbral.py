"""2.2: preparar umbral económico con OOF exclusivamente de A; nunca evalúa B.

Sin --ejecutar-a no lee datos ni entrena. --help tampoco importa scikit-learn.
Solo exporta agregados; las predicciones individuales permanecen en memoria.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings

COSTO = 5.0
RETENCION = 0.25
VALOR = 60.0
BENEFICIO = RETENCION * VALOR
UMBRAL = COSTO / BENEFICIO


def ejecutar_a():
    # Importaciones y lectura diferidas: importar este script o pedir ayuda es inocuo.
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    import pandas as pd
    import sklearn
    from sklearn.metrics import average_precision_score, brier_score_loss, log_loss
    from sklearn.model_selection import StratifiedKFold

    from entrenar_baselines_logistica import (
        ROOT, DEFAULT_INPUT, NUMERIC, CATEGORICAL, TARGET, make_model,
    )

    # Ruta fija de A: no se admite una entrada alternativa ni una opción para B/C.
    df = pd.read_csv(DEFAULT_INPUT, encoding='utf-8-sig', low_memory=False)
    missing = set(NUMERIC + CATEGORICAL + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f'Faltan columnas: {sorted(missing)}')
    if 'corte' in df and not df['corte'].astype(str).eq('A').all():
        raise ValueError('Solo se permite corte A')
    if 'fecha_corte' in df and not pd.to_datetime(
        df['fecha_corte'], errors='coerce'
    ).eq(pd.Timestamp('2026-07-01')).all():
        raise ValueError('Fecha incompatible con A')
    if 'usuario_seudonimo' in df and df['usuario_seudonimo'].duplicated().any():
        raise ValueError('Personas duplicadas')
    # Conversiones idénticas a 1.4, sin ordenar, filtrar ni estimar estadísticas globales.
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in CATEGORICAL:
        df[col] = df[col].astype('string').fillna('DESCONOCIDO').astype(str)
    if df[NUMERIC].isna().all(axis=None):
        raise ValueError('Todas las variables numéricas son nulas')
    y = pd.to_numeric(df[TARGET], errors='coerce').to_numpy()
    if not np.isin(y, [0, 1]).all():
        raise ValueError('abandono debe ser 0/1 sin nulos')
    y = y.astype(int)
    if len(y) != 60664 or int(y.sum()) != 8110:
        raise ValueError('Se requieren 60664 personas y 8110 positivos de A')
    X = df[NUMERIC + CATEGORICAL].copy()
    del df
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y))
    oof = np.full(len(y), np.nan)
    coverage = np.zeros(len(y), dtype=int)
    prior_oof = np.full(len(y), np.nan)
    metrics_rows, fold_rows, warning_rows = [], [], []

    def economics(labels, probabilities, threshold):
        contacted = probabilities >= threshold
        n = int(contacted.sum())
        tp = int(labels[contacted].sum())
        fp = n - tp
        positives = int(labels.sum())
        return {
            'umbral': float(threshold), 'personas': len(labels), 'contactados': n,
            'tp': tp, 'fp': fp, 'fn': positives - tp,
            'tn': len(labels) - positives - fp,
            'precision': tp / n if n else 0.0,
            'recall': tp / positives if positives else 0.0,
            'ganancia_esperada_q': float((BENEFICIO * probabilities[contacted] - COSTO).sum()),
            'ganancia_observada_simulada_q': BENEFICIO * tp - COSTO * n,
        }

    def diagnostics(labels, probabilities):
        return {'ap': float(average_precision_score(labels, probabilities)),
                'brier': float(brier_score_loss(labels, probabilities)),
                'log_loss': float(log_loss(labels, probabilities, labels=[0, 1]))}

    for fold, (tr, va) in enumerate(folds, 1):
        print(f'A: fold {fold}/5, logística L1 lambda=1', flush=True)
        pipe = make_model('l1', 1.0)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            pipe.fit(X.iloc[tr], y[tr])
        for warning in caught:
            warning_rows.append({'fold': fold, 'aviso': str(warning.message)})
            print(f'Aviso fold {fold}: {warning.message}', flush=True)
        probabilities = pipe.predict_proba(X.iloc[va])[:, 1]
        oof[va] = probabilities
        coverage[va] += 1
        prior_oof[va] = y[tr].mean()
        metrics_rows.append({'fold': fold, **diagnostics(y[va], probabilities),
                             **economics(y[va], probabilities, UMBRAL)})
        fold_rows.append({'fold': fold, 'n_train': len(tr), 'n_validacion': len(va),
                          'positivos_train': int(y[tr].sum()),
                          'positivos_validacion': int(y[va].sum()),
                          'sha256_indices_validacion': hashlib.sha256(
                              va.astype('<i8').tobytes()).hexdigest()})
    if not (coverage == 1).all() or not np.isfinite(oof).all():
        raise RuntimeError('Cada persona debe tener exactamente una predicción OOF válida')
    if not ((oof >= 0) & (oof <= 1)).all():
        raise RuntimeError('Probabilidades fuera de [0, 1]')

    # Referencias agregadas de A; ninguna lectura de B ni de su evaluación.
    historical = pd.read_csv(ROOT / 'docs/reportes_fase1_4/metricas_por_fold.csv')
    historical = historical[
        historical.modelo.eq('Logistica_l1_lambda_1') &
        historical.metrica.eq('average_precision')][['fold', 'valor']]
    fold_metrics = pd.DataFrame(metrics_rows)
    reconciliation = fold_metrics[['fold', 'ap']].merge(
        historical, on='fold', validate='one_to_one')
    if len(reconciliation) != 5:
        raise ValueError('Faltan referencias históricas de A para logística')
    reconciliation['diferencia_ap'] = reconciliation.ap - reconciliation.valor

    # Umbral económico prefijado; la malla NO se usa para optimizar la política.
    # nextafter(1, +inf) representa inequívocamente no contactar, incluso con p=1.
    thresholds = np.unique(np.r_[np.linspace(0, 1, 1001), UMBRAL,
                                 np.nextafter(1.0, np.inf)])
    curve = pd.DataFrame([economics(y, oof, t) for t in thresholds])
    policies = pd.DataFrame([
        {'politica': name, **economics(y, oof, threshold)}
        for name, threshold in [('no_contactar', np.nextafter(1.0, np.inf)),
                                 ('contactar_todos', 0.0), ('umbral_05', 0.5),
                                 ('umbral_economico', UMBRAL)]])

    # Curva de fiabilidad en diez intervalos fijos; intervalos vacíos explícitos.
    # No se recalibra con las etiquetas OOF y luego se evalúa en esas mismas etiquetas.
    bin_ids = np.minimum((oof * 10).astype(int), 9)
    calibration_rows = []
    for bin_id in range(10):
        mask = bin_ids == bin_id
        n = int(mask.sum())
        mean_p = float(oof[mask].mean()) if n else np.nan
        rate = float(y[mask].mean()) if n else np.nan
        calibration_rows.append({
            'limite_inferior': bin_id / 10, 'limite_superior': (bin_id + 1) / 10,
            'personas': n, 'probabilidad_media': mean_p, 'tasa_observada': rate,
            'error_absoluto': abs(mean_p - rate) if n else np.nan,
        })
    calibration = pd.DataFrame(calibration_rows)
    ece = float((calibration.personas * calibration.error_absoluto.fillna(0)).sum() / len(y))
    aggregate = {
        **diagnostics(y, oof), 'ece_10_bins': ece,
        'probabilidad_media_oof': float(oof.mean()), 'prevalencia': float(y.mean()),
        'brier_baseline_tasa_train': float(brier_score_loss(y, prior_oof)),
        'log_loss_baseline_tasa_train': float(log_loss(y, prior_oof, labels=[0, 1])),
    }
    metric_columns = ['ap', 'brier', 'log_loss', 'precision', 'recall',
                      'ganancia_esperada_q', 'ganancia_observada_simulada_q']
    summary = fold_metrics[metric_columns].agg(['mean', 'std']).T.reset_index()
    summary.columns = ['metrica', 'media', 'desviacion_estandar']
    summary['folds'] = 5

    out = ROOT / 'docs' / 'reportes_fase2_2'
    docs = ROOT / 'docs' / 'Fase_2' / 'fase2_2'
    out.mkdir(parents=True, exist_ok=True)
    docs.mkdir(parents=True, exist_ok=True)
    for filename, frame in [
        ('metricas_por_fold.csv', fold_metrics), ('metricas_resumen.csv', summary),
        ('metricas_oof.csv', pd.DataFrame([aggregate])), ('curva_ganancia.csv', curve),
        ('comparacion_politicas.csv', policies), ('calibracion_oof.csv', calibration),
        ('folds_resumen.csv', pd.DataFrame(fold_rows)),
        ('comparacion_fase1_4.csv', reconciliation),
        ('avisos.csv', pd.DataFrame(warning_rows, columns=['fold', 'aviso'])),
    ]:
        frame.to_csv(out / filename, index=False, encoding='utf-8-sig')
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(curve.umbral, curve.ganancia_esperada_q, label='Esperada según probabilidades OOF')
    ax.plot(curve.umbral, curve.ganancia_observada_simulada_q,
            label='Observada simulada con etiquetas A')
    ax.axvline(UMBRAL, color='black', linestyle='--', label='Umbral económico 1/3')
    ax.axhline(0, color='gray', linewidth=0.8)
    ax.set(xlabel='Umbral (contactar si p ≥ umbral)', ylabel='Ganancia total (Q)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / 'ganancia_vs_umbral.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 6))
    nonempty = calibration[calibration.personas.gt(0)]
    ax.plot([0, 1], [0, 1], '--', color='gray', label='Calibración ideal')
    ax.plot(nonempty.probabilidad_media, nonempty.tasa_observada, 'o-', label='OOF A')
    ax.set(xlabel='Probabilidad media predicha', ylabel='Fracción de abandono observada',
           xlim=(0, 1), ylim=(0, 1))
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / 'calibracion_oof.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(curve.umbral, curve.precision, label='Precisión (0 si no hay contactos)')
    ax.plot(curve.umbral, curve.recall, label='Recall')
    ax.axvline(UMBRAL, color='black', linestyle='--', label='Umbral económico')
    ax.set(xlabel='Umbral', ylabel='Métrica OOF A')
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / 'precision_recall_vs_umbral.png', dpi=180)
    plt.close(fig)

    metadata = {
        'corte': 'A', 'filas': len(y), 'positivos': int(y.sum()), 'semilla': 42,
        'cv': 'StratifiedKFold(n_splits=5, shuffle=True, random_state=42)',
        'modelo': pipe.named_steps['model'].get_params(),
        'costo_contacto_q': COSTO, 'probabilidad_retencion': RETENCION,
        'valor_retenido_q': VALOR, 'beneficio_por_positivo_q': BENEFICIO,
        'umbral_propuesto': UMBRAL,
        'regla': 'p >= 1/3; empate de ganancia esperada cero se contacta',
        'seleccion': 'Teórica prefijada; no se maximiza la curva empírica',
        'estado': 'Propuesta pendiente de revisión de calibración en A; B no autorizado',
        'calibracion': 'Diagnóstico OOF sin reajuste; no garantiza calibración suficiente',
        'sha256_dataset_a': hashlib.sha256(DEFAULT_INPUT.read_bytes()).hexdigest(),
        'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'numpy': np.__version__, 'pandas': pd.__version__,
        'avisos': warning_rows,
    }
    (out / 'configuracion.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    text = f'''# 2.2 — Umbral económico: validación en A

Solo A, {len(y)} personas y {int(y.sum())} positivos. B permanece cerrado como test único.
Se reutiliza make_model('l1', 1.0), con las nueve variables y el preprocesamiento de 1.4.
Cinco folds estratificados, shuffle=True y random_state=42, sin alterar el orden del CSV.
Cada pipeline nuevo se ajusta solo con train. Cada persona recibe una sola predicción OOF.
No se guardan predicciones individuales, identificadores ni modelos finales.

## Escenario económico y política propuesta

Contacto Q5, retención condicional al abandono 25%, valor retenido Q60.
Ganancia esperada individual: 0.25 × 60 × p − 5 = 15p − 5.
Umbral teórico: 5/15 = {UMBRAL:.12f}; contactar si p ≥ umbral.
En el empate se contacta, con ganancia esperada cero. No contactar tiene ganancia cero.
Ganancia esperada del grupo: suma de (15p − 5) entre los contactados.
Ganancia observada simulada: 15TP − 5(TP+FP), usando las etiquetas de A.
Esta última usa retención esperada del 25%: no mide retenciones reales ni beneficio causal realizado.
Se supone costo constante, valor constante, capacidad sin límite y beneficio nulo en no abandonantes.

Se propone 1/3 por la condición de rentabilidad económica, sin optimizar sobre las etiquetas.
La curva empírica es descriptiva; elegir su máximo y reportar ese mismo resultado produciría optimismo.
No se seleccionan candidatos empíricos ni se usan resultados B.
La adopción definitiva queda pendiente de revisar la calibración OOF en A.
Si hace falta recalibrar, debe hacerse dentro del train de cada fold (validación interna),
nunca ajustando con las etiquetas del fold externo ni con B.

## Resultados agregados OOF

AP OOF: {aggregate['ap']:.6f}; Brier: {aggregate['brier']:.6f};
log-loss: {aggregate['log_loss']:.6f}; ECE en diez intervalos: {ece:.6f}.
Probabilidad media: {aggregate['probabilidad_media_oof']:.6f}; prevalencia: {y.mean():.6f}.
Se compara Brier/log-loss contra la tasa del train correspondiente en metricas_oof.csv.
Menor Brier/log-loss es mejor, pero también dependen de discriminación y no demuestran calibración.
La curva de fiabilidad presenta tasas y probabilidades por intervalo, con sus tamaños;
ECE depende de los intervalos y no tiene aquí una regla automática de aprobación.

Políticas comparadas (totales OOF sobre A):

```text
{policies.to_string(index=False)}
```

La media y DE muestral de AP por fold están separadas de AP OOF agrupada;
AP no es aditiva y ambos cálculos pueden diferir. Precisión se define como cero
si no hay contactos, por convención; no significa precisión medida en un grupo vacío.
La ganancia media por fold no es la ganancia total: los totales están en comparacion_politicas.csv.
Los folds comparten train; las DE no son intervalos de confianza.
λ=1 ya fue seleccionado en 1.4 con este CV: no es evaluación externa independiente.
La ganancia esperada depende de probabilidades interpretables; AP mide ranking, no calibración.

## Reproducción y archivos

`python scripts/modelado/seleccionar_umbral.py --ejecutar-a`

CSV y gráficas agregados: docs/reportes_fase2_2/. Configuración incluye versiones,
huella del dataset y parámetros. No se consultó PostgreSQL, Docker ni dbt.
Este script no incluye lectura, preparación, entrenamiento ni evaluación de B/C.
El test único B requerirá autorización explícita posterior y una política previamente fijada.
'''
    (docs / 'documentacion_tecnica.md').write_text(text, encoding='utf-8')
    print(f'Reportes agregados de A: {out}\nDocumentación: {docs}')
    print('Umbral propuesto 1/3, pendiente de revisión de calibración. B no se ha leído.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ejecutar-a', action='store_true',
                        help='Ejecutar CV de A y generar reportes agregados; nunca accede a B/C')
    args = parser.parse_args()
    if not args.ejecutar_a:
        parser.print_help()
        return
    ejecutar_a()


if __name__ == '__main__':
    main()
