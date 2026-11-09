"""Fase 2.1. Ejecutar explícitamente; importar este archivo no entrena.

Desde la raíz: python scripts/modelado/comparar_ensembles.py
Requiere las dependencias de 1.4 (numpy, pandas, matplotlib, scikit-learn).
Solo lee corte A y reportes agregados de 1.4. No guarda datos individuales.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline

from entrenar_baselines_logistica import (
    ROOT, DEFAULT_INPUT, NUMERIC, CATEGORICAL, TARGET, SEED, make_model,
)

OUTPUT = ROOT / 'docs' / 'reportes_fase2_1'
DOCUMENTATION = ROOT / 'docs' / 'Fase_2' / 'fase2_1'


def load_data():
    # Misma lectura, orden de filas y conversiones de 1.4; no ordenar ni filtrar.
    df = pd.read_csv(DEFAULT_INPUT, encoding='utf-8-sig', low_memory=False)
    missing = set(NUMERIC + CATEGORICAL + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f'Faltan columnas: {sorted(missing)}')
    if 'corte' in df and not df['corte'].astype(str).eq('A').all():
        raise ValueError('Solo se permite corte A')
    if 'fecha_corte' in df and not pd.to_datetime(
        df['fecha_corte'], errors='coerce'
    ).eq(pd.Timestamp('2026-07-01')).all():
        raise ValueError('Fecha incompatible con corte A')
    if 'usuario_seudonimo' in df and df['usuario_seudonimo'].duplicated().any():
        raise ValueError('Hay personas duplicadas')
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in CATEGORICAL:
        df[col] = df[col].astype('string').fillna('DESCONOCIDO').astype(str)
    if df[NUMERIC].isna().all(axis=None):
        raise ValueError('Todas las variables numéricas son nulas')
    y = pd.to_numeric(df[TARGET], errors='coerce').to_numpy()
    if not np.isin(y, [0, 1]).all():
        raise ValueError('abandono debe ser binario sin nulos')
    y = y.astype(int)
    if len(y) != 60664 or y.sum() != 8110:
        raise ValueError('Se requieren exactamente 60664 personas y 8110 positivos')
    return df[NUMERIC + CATEGORICAL].copy(), y


def recency(X):
    return X['dias_desde_ultimo_evento'].fillna(28).clip(0, 28).to_numpy(float) / 28


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arboles', type=int, default=300)
    parser.add_argument('--repeticiones', type=int, default=10,
                        help='Permutaciones por característica y fold de validación')
    parser.add_argument('--jobs', type=int, default=-1,
                        help='Paralelismo del bosque; permutaciones secuenciales')
    args = parser.parse_args()
    if args.arboles < 1 or args.repeticiones < 2 or args.jobs == 0:
        parser.error('arboles >= 1, repeticiones >= 2 y jobs distinto de 0')
    X, y = load_data()
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=42).split(X, y))
    records, importance_rows, warning_rows, fold_info = [], [], [], []
    for fold, (tr, va) in enumerate(folds, 1):
        fold_info.append({'fold': fold, 'n_train': len(tr), 'n_validacion': len(va),
                          'positivos_train': int(y[tr].sum()),
                          'positivos_validacion': int(y[va].sum()),
                          'sha256_indices_validacion': hashlib.sha256(
                              va.astype('<i8').tobytes()).hexdigest()})
        logit = make_model('l1', 1.0)
        forest = Pipeline([
            ('prep', clone(logit.named_steps['prep'])),
            ('model', RandomForestClassifier(
                n_estimators=args.arboles, max_depth=None, min_samples_leaf=1,
                max_features='sqrt', bootstrap=True, class_weight=None,
                random_state=SEED, n_jobs=args.jobs)),
        ])
        for name, pipe in [('Baseline_tasa_positiva', None),
                           ('Baseline_recencia', None),
                           ('Logistica_l1_lambda_1', logit), ('RandomForest', forest)]:
            print(f'Fold {fold}/5: {name}', flush=True)
            if pipe is not None:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    pipe.fit(X.iloc[tr], y[tr])
                for warning in caught:
                    warning_rows.append({'fold': fold, 'modelo': name,
                                         'aviso': str(warning.message)})
                    print(f'  Aviso: {warning.message}', flush=True)
            values = {}
            for split, idx in [('train', tr), ('validacion', va)]:
                if pipe is not None:
                    scores = pipe.predict_proba(X.iloc[idx])[:, 1]
                elif name == 'Baseline_recencia':
                    scores = recency(X.iloc[idx])
                else:
                    scores = np.full(len(idx), y[tr].mean())
                values[split] = float(average_precision_score(y[idx], scores))
            records.append({'modelo': name, 'fold': fold,
                            'ap_train': values['train'],
                            'ap_validacion': values['validacion'],
                            'brecha': values['train'] - values['validacion']})
            if name == 'RandomForest':
                # Solo VALIDACIÓN. El preprocesador ya fue ajustado con train.
                # Permutar columnas codificadas permite un top 10 con 9 variables originales.
                transformed = pipe.named_steps['prep'].transform(X.iloc[va])
                if hasattr(transformed, 'toarray'):
                    transformed = transformed.toarray()
                result = permutation_importance(
                    pipe.named_steps['model'], transformed, y[va],
                    scoring='average_precision', n_repeats=args.repeticiones,
                    random_state=SEED + fold, n_jobs=1,
                )
                names = pipe.named_steps['prep'].get_feature_names_out()
                for feature, drops in zip(names, result.importances):
                    for repeat, drop in enumerate(drops, 1):
                        importance_rows.append({'fold': fold, 'caracteristica': feature,
                                                'repeticion': repeat, 'caida_ap': float(drop)})

    results = pd.DataFrame(records)
    summary = results.groupby('modelo', as_index=False).agg(
        ap_train_media=('ap_train', 'mean'), ap_train_de=('ap_train', 'std'),
        ap_validacion_media=('ap_validacion', 'mean'),
        ap_validacion_de=('ap_validacion', 'std'),
        brecha_media=('brecha', 'mean'), brecha_de=('brecha', 'std'),
        folds=('fold', 'count'))
    # Comparación histórica por fold, sin reemplazar los resultados recién calculados.
    historical = pd.read_csv(ROOT / 'docs/reportes_fase1_4/metricas_por_fold.csv')
    historical = historical[historical['metrica'].eq('average_precision')][
        ['modelo', 'fold', 'valor']]
    reconciliation = results.merge(historical, on=['modelo', 'fold'], how='inner')
    reconciliation['diferencia_ap'] = reconciliation.ap_validacion - reconciliation.valor
    if len(reconciliation) != 15:
        raise ValueError('Se esperaban 15 referencias históricas de AP en 1.4')

    importance = pd.DataFrame(importance_rows)
    per_fold = importance.groupby(['caracteristica', 'fold'], as_index=False).agg(
        caida_ap_media=('caida_ap', 'mean'), de_permutaciones=('caida_ap', 'std'))
    ranking = per_fold.groupby('caracteristica', as_index=False).agg(
        caida_ap_media=('caida_ap_media', 'mean'),
        de_entre_folds=('caida_ap_media', 'std'), folds=('fold', 'count'))
    # No promediar características presentes solamente en algunos folds en el top 10.
    top = ranking[ranking.folds.eq(5)].sort_values('caida_ap_media', ascending=False).head(10)
    if len(top) != 10:
        raise ValueError('No hay diez características codificadas comunes a los cinco folds')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    DOCUMENTATION.mkdir(parents=True, exist_ok=True)
    for filename, frame in [
        ('metricas_por_fold.csv', results), ('metricas_resumen.csv', summary),
        ('comparacion_fase1_4.csv', reconciliation),
        ('permutaciones_validacion.csv', importance), ('importancias_por_fold.csv', per_fold),
        ('importancias_resumen.csv', ranking), ('top10_importancias.csv', top),
        ('folds_resumen.csv', pd.DataFrame(fold_info)),
        ('avisos.csv', pd.DataFrame(warning_rows, columns=['fold', 'modelo', 'aviso'])),
    ]:
        frame.to_csv(OUTPUT / filename, index=False, encoding='utf-8-sig')
    fig, ax = plt.subplots(figsize=(10, 5))
    positions = np.arange(len(summary))
    for offset, split, label in [(-0.17, 'train', 'Train'), (0.17, 'validacion', 'Validación')]:
        ax.bar(positions + offset, summary[f'ap_{split}_media'], width=0.34,
               yerr=summary[f'ap_{split}_de'], capsize=3, label=label)
    ax.set_xticks(positions, summary.modelo, rotation=15, ha='right')
    ax.set_ylabel('Average Precision (media ± DE entre folds)')
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT / 'ap_train_validacion.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(10, 6))
    ordered = top.iloc[::-1]
    ax.barh(ordered.caracteristica, ordered.caida_ap_media,
            xerr=ordered.de_entre_folds, capsize=3)
    ax.set_xlabel('Caída de AP en validación (media ± DE entre folds)')
    fig.tight_layout()
    fig.savefig(OUTPUT / 'top10_permutation_validacion.png', dpi=180)
    plt.close(fig)
    metadata = {
        'filas': len(y), 'positivos': int(y.sum()), 'semilla': SEED,
        'cv': 'StratifiedKFold(n_splits=5, shuffle=True, random_state=42)',
        'sha256_dataset': hashlib.sha256(DEFAULT_INPUT.read_bytes()).hexdigest(),
        'python': platform.python_version(), 'sklearn': sklearn.__version__,
        'numpy': np.__version__, 'pandas': pd.__version__,
        'random_forest': forest.named_steps['model'].get_params(),
        'logistica': logit.named_steps['model'].get_params(),
        'repeticiones': args.repeticiones, 'avisos': warning_rows,
        'desviacion_estandar': 'muestral, ddof=1; folds correlacionados',
    }
    (OUTPUT / 'configuracion.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# Fase 2.1 — Ensemble y sesgo-varianza', '',
        'Solo corte A: 60664 personas y 8110 positivos. Sin etiquetas B/C.',
        'Mismos cinco folds y orden de filas que 1.4. Preprocesamiento dentro de pipelines,',
        'ajustado exclusivamente con train. L1 λ=1 conserva la configuración de 1.4.',
        'Bosque con parámetros prefijados, sin búsqueda de hiperparámetros.', '',
        '## Resultados observados', '',
    ]
    for row in summary.itertuples():
        lines.append(f'- {row.modelo}: AP train {row.ap_train_media:.6f} ± {row.ap_train_de:.6f}; '
                     f'AP validación {row.ap_validacion_media:.6f} ± {row.ap_validacion_de:.6f}; '
                     f'brecha train−validación {row.brecha_media:.6f} ± {row.brecha_de:.6f}.')
    paired = results.pivot(index='fold', columns='modelo', values='ap_validacion')
    delta = paired['RandomForest'] - paired['Logistica_l1_lambda_1']
    lines += ['', f'Diferencia RF−L1 de AP en validación: {delta.mean():.6f} ± {delta.std():.6f}; '
              f'RF supera L1 en {int((delta > 0).sum())}/5 folds.', '',
              '## Interpretación y límites', '',
              'Una AP train mayor que validación es compatible con sobreajuste. La magnitud de',
              'la brecha y la dispersión deben leerse junto con AP de validación y los baselines.',
              'Una brecha pequeña no demuestra bajo sesgo: ambos desempeños pueden ser bajos.',
              'Estas mediciones no constituyen una descomposición formal de sesgo y varianza.',
              'Los folds comparten entrenamiento; la DE no es un intervalo de confianza.',
              'L1 λ=1 ya fue seleccionado usando este CV en 1.4; no hay evaluación externa independiente.',
              f'Máxima diferencia absoluta frente a AP histórica: '
              f'{reconciliation.diferencia_ap.abs().max():.9g}. Revisar avisos y versiones si difiere.', '',
              '## Importancia por permutación', '',
              'RF: caída de AP al permutar exclusivamente validación, sin reentrenar.',
              'Top 10 de columnas codificadas comunes a los cinco folds, no diez variables originales:',
              'solo existen nueve variables originales. Se conservan valores negativos.',
              'La DE entre folds usa las medias de las repeticiones por fold; las repeticiones',
              'y su dispersión interna se guardan por separado. No representan personas.',
              'Permutar una dummy puede producir combinaciones categóricas no observadas.',
              'Correlación entre variables puede repartir u ocultar importancia; no indica causalidad.', '',
              '## Reproducción', '',
              f'`python scripts/modelado/comparar_ensembles.py --arboles {args.arboles} '
              f'--repeticiones {args.repeticiones} --jobs {args.jobs}`', '',
              'Los CSV y gráficos están en `docs/reportes_fase2_1/`. La configuración incluye',
              'versiones, parámetros, avisos y huellas agregadas de dataset/folds.',
              'No se exportan identificadores, predicciones ni filas individuales.']
    (DOCUMENTATION / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(summary.to_string(index=False))
    print(f'Reportes: {OUTPUT}\nDocumentación: {DOCUMENTATION}')


if __name__ == '__main__':
    main()
