"""Fase 1.4: dos baselines y regresión logística regularizada.

Ejecutar desde la raíz del repositorio:
    python scripts/modelado/entrenar_baselines_logistica.py

Dataset esperado: datos_modelado_local/fase1_4/dataset_corte_A.csv
Salida: docs/reportes_fase1_4/ (sin identificadores individuales).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / 'datos_modelado_local' / 'fase1_4' / 'dataset_corte_A.csv'
DEFAULT_OUTPUT = ROOT / 'docs' / 'reportes_fase1_4'
NUMERIC = [
    'eventos_ultimos_7_dias', 'eventos_ultimos_28_dias',
    'cantidad_modos_distintos', 'dias_desde_ultimo_evento',
    'proporcion_eventos_hora_pico', 'gasto_acumulado_gtq',
    'gasto_promedio_evento_gtq',
]
CATEGORICAL = ['modo_mas_usado', 'zona_origen_mas_frecuente']
TARGET = 'abandono'
LAMBDAS = [0.01, 0.1, 1.0, 10.0, 100.0]
SEED = 42


def metrics(y_true, scores, preds):
    return {
        'average_precision': float(average_precision_score(y_true, scores)),
        'roc_auc': float(roc_auc_score(y_true, scores)),
        'f1_umbral_05': float(f1_score(y_true, preds, zero_division=0)),
    }


def make_model(penalty: str, lam: float) -> Pipeline:
    # El ajuste de imputadores, escalador y OHE ocurre únicamente en train de cada fold.
    numeric_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler()),
    ])
    categorical_pipe = Pipeline([
        ('imputer', SimpleImputer(strategy='constant', fill_value='DESCONOCIDO')),
        ('onehot', OneHotEncoder(handle_unknown='ignore', drop='first')),
    ])
    prep = ColumnTransformer([
        ('num', numeric_pipe, NUMERIC),
        ('cat', categorical_pipe, CATEGORICAL),
    ], remainder='drop', sparse_threshold=0.3)
    return Pipeline([
        ('prep', prep),
        ('model', LogisticRegression(
            l1_ratio=1.0 if penalty == 'l1' else 0.0,
            C=1.0 / lam,
            solver='liblinear',
            max_iter=1500,
            random_state=SEED,
        )),
    ])


def save_csv(path, rows, fieldnames):
    with path.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description='Entrenar y comparar modelos del corte A')
    parser.add_argument('--entrada', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--salida', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if not args.entrada.is_file():
        sys.exit(f'ERROR: dataset no encontrado: {args.entrada}')
    df = pd.read_csv(args.entrada, encoding='utf-8-sig', low_memory=False)
    needed = NUMERIC + CATEGORICAL + [TARGET]
    missing = [col for col in needed if col not in df.columns]
    if missing:
        sys.exit(f'ERROR: faltan columnas en el CSV: {missing}. Columnas existentes: {df.columns.tolist()}')
    if 'corte' in df.columns and not (df['corte'].astype(str) == 'A').all():
        sys.exit('ERROR: el dataset contiene cortes distintos de A')
    if 'fecha_corte' in df.columns:
        if not pd.to_datetime(df['fecha_corte'], errors='coerce').eq(pd.Timestamp('2026-07-01')).all():
            sys.exit('ERROR: fechas de corte distintas de 2026-07-01')
    if 'usuario_seudonimo' in df.columns and df['usuario_seudonimo'].duplicated().any():
        sys.exit('ERROR: usuarios duplicados en corte A')
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    for col in CATEGORICAL:
        df[col] = df[col].astype('string').fillna('DESCONOCIDO').astype(str)
    if df[NUMERIC].isna().all(axis=None):
        sys.exit('ERROR: todas las variables numéricas son nulas')
    if df[TARGET].isna().any():
        sys.exit('ERROR: abandono contiene nulos')
    y = pd.to_numeric(df[TARGET], errors='coerce').to_numpy()
    if not np.isin(y, [0, 1]).all():
        sys.exit('ERROR: la variable abandono debe ser binaria (0/1)')
    y = y.astype(int)
    positives = int(y.sum())
    if len(df) != 60664 or positives != 8110:
        sys.exit(f'ERROR de reconciliación con 1.2: filas={len(df)} y positivos={positives}; esperados 60664/8110')
    X = df[NUMERIC + CATEGORICAL].copy()
    out = args.salida
    out.mkdir(parents=True, exist_ok=True)
    print(f'Dataset: {len(df):,} personas, {positives:,} positivos ({y.mean():.4%}).')
    print('Validación: 5 folds estratificados, semilla 42. Métrica principal: Average Precision (AP).')
    folds = list(StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED).split(X, y))
    records = []

    # Baseline 1: constante = tasa positiva del TRAIN de cada fold, no del dataset entero.
    for fold, (tr, va) in enumerate(folds, 1):
        prior = float(y[tr].mean())
        scores = np.full(len(va), prior)
        for key, val in metrics(y[va], scores, np.zeros(len(va), dtype=int)).items():
            records.append({'modelo': 'Baseline_tasa_positiva', 'penalizacion': 'ninguna',
                            'lambda': '', 'fold': fold, 'metrica': key, 'valor': val})

    # Baseline 2: puntuación monotónica de recencia (días sin abordar / 28).
    # No se ajusta un modelo, ni se calcula ninguna estadística global de entrenamiento.
    for fold, (_, va) in enumerate(folds, 1):
        scores = (X.iloc[va]['dias_desde_ultimo_evento'].fillna(28)
                  .clip(lower=0, upper=28).to_numpy(dtype=float) / 28.0)
        for key, val in metrics(y[va], scores, scores >= 0.5).items():
            records.append({'modelo': 'Baseline_recencia', 'penalizacion': 'ninguna',
                            'lambda': '', 'fold': fold, 'metrica': key, 'valor': val})

    # Búsqueda de λ idéntica para L1 y L2 en los mismos 5 folds.
    for penalty in ('l1', 'l2'):
        for lam in LAMBDAS:
            label = f'Logistica_{penalty}_lambda_{lam:g}'
            print(f'Entrenando {label}...', flush=True)
            for fold, (tr, va) in enumerate(folds, 1):
                pipe = make_model(penalty, lam)
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter('always')
                    pipe.fit(X.iloc[tr], y[tr])
                if caught:
                    print(f'  Aviso de entrenamiento {label} fold {fold}: {caught[0].message}')
                score = pipe.predict_proba(X.iloc[va])[:, 1]
                for key, val in metrics(y[va], score, score >= 0.5).items():
                    records.append({'modelo': label, 'penalizacion': penalty,
                                    'lambda': lam, 'fold': fold, 'metrica': key, 'valor': val})

    fieldnames = ['modelo', 'penalizacion', 'lambda', 'fold', 'metrica', 'valor']
    save_csv(out / 'metricas_por_fold.csv', records, fieldnames)
    results = pd.DataFrame(records)
    summary = (results.groupby(['modelo', 'penalizacion', 'lambda', 'metrica'],
                               dropna=False, as_index=False)
               .agg(media=('valor','mean'), desviacion_estandar=('valor','std'), folds=('valor','count')))
    summary.to_csv(out / 'metricas_resumen_todos.csv', index=False, encoding='utf-8-sig')
    ap = summary[summary.metrica == 'average_precision'].copy()
    selected = {}
    for penalty in ('l1','l2'):
        subset = ap[ap.penalizacion == penalty].sort_values(
            ['media', 'lambda'], ascending=[False, True])
        best = subset.iloc[0]
        selected[penalty] = float(best['lambda'])
        print(f'Mejor {penalty}: lambda={selected[penalty]:g}, AP={best["media"]:.5f} ± {best["desviacion_estandar"]:.5f}')

    chosen_models = ['Baseline_tasa_positiva', 'Baseline_recencia'] + [
        f'Logistica_{p}_lambda_{selected[p]:g}' for p in ('l1','l2')
    ]
    comparison = summary[summary.modelo.isin(chosen_models)].copy()
    comparison['modelo_elegido'] = comparison.modelo.map({
        chosen_models[0]:'Baseline 1 — tasa del train', chosen_models[1]:'Baseline 2 — recencia',
        chosen_models[2]:f'Logística L1 (λ={selected["l1"]:g})',
        chosen_models[3]:f'Logística L2 (λ={selected["l2"]:g})',
    })
    comparison[['modelo_elegido','metrica','media','desviacion_estandar','folds']].to_csv(
        out / 'tabla_modelos.csv', index=False, encoding='utf-8-sig')

    fig, ax = plt.subplots(figsize=(9, 5.5))
    for penalty in ('l1','l2'):
        part = ap[ap.penalizacion == penalty].sort_values('lambda')
        ax.errorbar(part['lambda'], part['media'], yerr=part['desviacion_estandar'],
                    marker='o', capsize=3, label=f'Regresión logística {penalty.upper()}')
    ax.set_xscale('log')
    ax.set_xlabel('λ = 1 / C (mayor λ implica mayor regularización)')
    ax.set_ylabel('Average Precision (AP) — media ± DE en 5 folds')
    ax.set_title('Fase 1.4: validación cruzada vs. regularización')
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / 'ap_vs_lambda.png', dpi=180)
    plt.close(fig)

    # Coeficientes finales: reentrenar en TODO el corte A después de elegir λ.
    # Son interpretaciones descriptivas, no estimaciones independientes de desempeño.
    best_penalty = max(('l1','l2'), key=lambda p: float(
        ap[(ap.penalizacion==p) & (ap['lambda']==selected[p])]['media'].iloc[0]))
    best_lam = selected[best_penalty]
    best_model = make_model(best_penalty, best_lam)
    best_model.fit(X, y)
    names = best_model.named_steps['prep'].get_feature_names_out()
    weights = best_model.named_steps['model'].coef_.ravel()
    coefs = pd.DataFrame({'feature_codificada': names,
                          'coeficiente_log_odds': weights,
                          'odds_ratio_exp_coef': np.exp(np.clip(weights,-30,30))})
    coefs['abs_coef'] = coefs['coeficiente_log_odds'].abs()
    coefs.sort_values('abs_coef', ascending=False).drop(columns='abs_coef').to_csv(
        out / 'coeficientes_modelo_elegido.csv', index=False, encoding='utf-8-sig')
    top = coefs.sort_values('abs_coef', ascending=False).head(10)
    meta = {
        'fecha_corte':'2026-07-01', 'filas':len(df), 'positivos':positives,
        'negativos':len(df)-positives, 'metrica_principal':'average_precision',
        'validacion':'StratifiedKFold 5 folds shuffle=True seed=42',
        'mejor_lambda_l1': selected['l1'], 'mejor_lambda_l2': selected['l2'],
        'regularizacion_ganadora':best_penalty, 'lambda_ganador':best_lam,
        'nota':'El mismo CV selecciona lambda y estima desempeño; no es una evaluación externa independiente. No se utiliza B.'
    }
    (out / 'configuracion_resultados.json').write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nRESULTADO: MODELOS EVALUADOS')
    print(comparison[comparison.metrica=='average_precision'][
        ['modelo_elegido','media','desviacion_estandar']].to_string(index=False))
    print('\nCOEFICIENTES MÁS INFLUYENTES (por magnitud; modelo final):')
    print(top[['feature_codificada','coeficiente_log_odds','odds_ratio_exp_coef']].to_string(index=False))
    print(f'\nReportes guardados en: {out}')
    print('No se modificó PostgreSQL. No se utilizó el corte B para entrenar.')


if __name__ == '__main__':
    main()
