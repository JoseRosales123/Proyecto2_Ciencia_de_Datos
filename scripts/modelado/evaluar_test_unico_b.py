"""Evaluador futuro de B. Sin doble autorización no lee datos ni entrena.

Requiere autorización posterior del usuario, política versionada, archivo local
de autorización y reserva persistente exclusiva antes de leer cualquier byte de B.
No hay opción de reintento ni de sobrescritura.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'docs/Fase_2/fase2_2/politica_congelada.json'
LOCAL = ROOT / 'datos_modelado_local/fase2_2'
AUTH = LOCAL / 'autorizacion_test_b.json'
LEDGER = LOCAL / 'test_b_bitacora.jsonl'
INPUT_B = LOCAL / 'dataset_corte_B.csv'
OUTPUT = ROOT / 'docs/reportes_fase2_2/test_unico_B'
PHRASE = 'AUTORIZO_EVALUACION_UNICA_B'


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def persist(handle, event):
    handle.write(json.dumps({'fecha_utc': utc(), **event}, ensure_ascii=False) + '\n')
    handle.flush()
    os.fsync(handle.fileno())


def evaluar():
    # Preflight solo de política/código/autorización; nunca inspecciona B.
    policy_bytes = POLICY.read_bytes()
    policy = json.loads(policy_bytes)
    if POLICY.with_suffix('.sha256').read_text(encoding='utf-8').split()[0] != sha(policy_bytes):
        raise ValueError('La huella de la política no coincide')
    if policy['estado_b'] != 'NO_EJECUTADO' or policy['estado_politica'] != 'CONGELADA':
        raise ValueError('La política no está habilitada para un primer test')
    if policy['umbral'] != {'numerador': 1, 'denominador': 3, 'comparador': '>='}:
        raise ValueError('Umbral diferente del congelado')
    if policy['economia'] != {'costo_contacto_q': 5, 'probabilidad_retencion': 0.25,
                             'valor_retenido_q': 60, 'beneficio_por_positivo_q': 15}:
        raise ValueError('Escenario económico alterado')
    if policy['cv'] != {'n_splits': 5, 'shuffle': True, 'random_state': 42}:
        raise ValueError('CV alterado')
    for relative, expected in policy['sha256_codigo'].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path.read_bytes()) != expected:
            raise ValueError('Código diferente del congelado')
    commit = git('rev-parse', 'HEAD')
    guarded = [str(POLICY.relative_to(ROOT)).replace('\\', '/'),
               str(POLICY.with_suffix('.sha256').relative_to(ROOT)).replace('\\', '/'),
               *policy['sha256_codigo'].keys()]
    for relative in guarded:
        git('ls-files', '--error-unmatch', '--', relative)
    if git('status', '--porcelain', '--', *guarded):
        raise ValueError('La política y el código deben estar versionados y sin cambios')
    authorization_bytes = AUTH.read_bytes()
    authorization = json.loads(authorization_bytes)
    if (authorization.get('autorizacion') != PHRASE or
            authorization.get('politica_sha256') != sha(policy_bytes) or
            authorization.get('commit') != commit or
            not authorization.get('autorizado_por') or
            not authorization.get('referencia_instruccion_usuario')):
        raise ValueError('Falta autorización posterior vinculada a política y commit')
    date = datetime.fromisoformat(authorization['fecha_utc'])
    frozen_at = datetime.fromisoformat(policy['fecha_congelacion_utc'])
    if date.tzinfo is None or not frozen_at <= date <= datetime.now(timezone.utc):
        raise ValueError('Fecha de autorización inválida')
    expected_b_sha = authorization.get('dataset_b_sha256', '')
    if len(expected_b_sha) != 64 or any(c not in '0123456789abcdef' for c in expected_b_sha):
        raise ValueError('Falta huella del futuro exportador B autorizado')
    if OUTPUT.exists():
        raise FileExistsError('Ya existe un directorio de resultados de B; se bloquea')
    LOCAL.mkdir(parents=True, exist_ok=True)
    # Modo x = creación exclusiva atómica en este sistema de archivos.
    # No borrar jamás: incluso un fallo consume el intento y bloquea reintentos.
    with LEDGER.open('x', encoding='utf-8') as ledger:
        persist(ledger, {'evento': 'INTENTO_RESERVADO', 'estado': 'INICIADO',
                         'commit': commit, 'politica_sha256': sha(policy_bytes),
                         'autorizacion_sha256': sha(authorization_bytes),
                         'lectura_b_iniciada': False})
        try:
            OUTPUT.mkdir(parents=True, exist_ok=False)
            # Todo import/fit ocurre después de autorización; ningún ajuste usa B.
            import numpy as np
            import pandas as pd
            import sklearn
            import warnings
            from sklearn.metrics import (average_precision_score, brier_score_loss,
                                         log_loss, roc_auc_score)
            from comparar_ensembles import load_data
            from entrenar_baselines_logistica import (
                DEFAULT_INPUT, NUMERIC, CATEGORICAL, TARGET, make_model,
            )
            if policy['versiones'] != {'sklearn': sklearn.__version__,
                                       'numpy': np.__version__, 'pandas': pd.__version__}:
                raise ValueError('Versiones distintas a las congeladas')
            if policy['caracteristicas'] != NUMERIC + CATEGORICAL:
                raise ValueError('Características diferentes de 1.4')
            if sha(DEFAULT_INPUT.read_bytes()) != policy['dataset_a']['sha256']:
                raise ValueError('El dataset A cambió')
            X_a, y_a = load_data()
            pipe = make_model('l1', 1.0)
            if pipe.named_steps['model'].get_params() != policy['hiperparametros']:
                raise ValueError('Hiperparámetros diferentes de los congelados')
            # La huella del código de 1.4 fija también los pasos del preprocesador.
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                pipe.fit(X_a, y_a)
            if caught:
                persist(ledger, {'evento': 'AJUSTE_A_CON_AVISOS', 'cantidad': len(caught)})
                raise RuntimeError('Avisos al ajustar A: revisión requerida antes de leer B')
            persist(ledger, {'evento': 'MODELO_A_AJUSTADO', 'n_train': len(y_a)})
            # Se registra y sincroniza ANTES de abrir B, incluida su huella.
            persist(ledger, {'evento': 'ANTES_DE_LECTURA_B', 'lectura_b_iniciada': True})
            raw_b = INPUT_B.read_bytes()
            if sha(raw_b) != expected_b_sha:
                raise ValueError('B no coincide con la exportación autorizada')
            df = pd.read_csv(io.BytesIO(raw_b), encoding='utf-8-sig', low_memory=False)
            del raw_b
            required = NUMERIC + CATEGORICAL + [TARGET, 'corte', 'fecha_corte',
                                               'usuario_seudonimo']
            if any(col not in df for col in required):
                raise ValueError('Esquema B incompleto; requiere metadatos de corte')
            if not len(df) or not df['corte'].eq('B').all():
                raise ValueError('Archivo vacío o no exclusivo de B')
            if not pd.to_datetime(df.fecha_corte, errors='coerce').eq(
                    pd.Timestamp('2026-07-31')).all():
                raise ValueError('Fecha de B inválida')
            if df.usuario_seudonimo.isna().any() or df.usuario_seudonimo.duplicated().any():
                raise ValueError('Identificadores B nulos o duplicados')
            for col in NUMERIC:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            for col in CATEGORICAL:
                df[col] = df[col].astype('string').fillna('DESCONOCIDO').astype(str)
            y_b = pd.to_numeric(df[TARGET], errors='coerce').to_numpy()
            if not np.isin(y_b, [0, 1]).all():
                raise ValueError('Etiqueta B inválida')
            y_b = y_b.astype(int)
            # Solo predict: ninguna selección, calibración, fit ni búsqueda con B.
            probabilities = pipe.predict_proba(df[NUMERIC + CATEGORICAL])[:, 1]
            threshold = float(Fraction(policy['umbral']['numerador'],
                                       policy['umbral']['denominador']))
            contacted = probabilities >= threshold
            tp = int(y_b[contacted].sum())
            n = int(contacted.sum())
            positives = int(y_b.sum())
            fp = n - tp
            metrics = {
                'fecha_utc': utc(), 'commit': commit, 'politica_sha256': sha(policy_bytes),
                'dataset_b_sha256': expected_b_sha, 'estado_b': 'EJECUTADO',
                'personas': len(y_b), 'positivos': positives, 'contactados': n,
                'tp': tp, 'fp': fp, 'fn': positives - tp,
                'tn': len(y_b) - positives - fp,
                'precision': tp / n if n else 0.0,
                'recall': tp / positives if positives else 0.0,
                'ap': float(average_precision_score(y_b, probabilities)) if positives else None,
                'roc_auc': float(roc_auc_score(y_b, probabilities))
                           if 0 < positives < len(y_b) else None,
                'brier': float(brier_score_loss(y_b, probabilities)),
                'log_loss': float(log_loss(y_b, probabilities, labels=[0, 1])),
                'ganancia_esperada_q': float((15 * probabilities[contacted] - 5).sum()),
                'ganancia_observada_simulada_q': 15 * tp - 5 * n,
                'umbral_fraccion': '1/3',
            }
            with (OUTPUT / 'resultado_agregado.json').open('x', encoding='utf-8') as result:
                json.dump(metrics, result, ensure_ascii=False, indent=2, allow_nan=False)
                result.flush()
                os.fsync(result.fileno())
            persist(ledger, {'evento': 'FINALIZADO', 'estado': 'EJECUTADO',
                             'resultado_sha256': sha((OUTPUT / 'resultado_agregado.json').read_bytes())})
            print('Test B finalizado. Solo se guardaron métricas agregadas; no repetir.')
        except BaseException as error:
            # No copiar mensajes de librerías: podrían contener valores individuales.
            persist(ledger, {'evento': 'FALLO_NO_REINTENTAR', 'tipo': type(error).__name__})
            raise RuntimeError('Intento consumido. Revisar bitácora; no borrar ni repetir.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ejecutar-test-b', action='store_true',
                        help='Solo tras autorización posterior explícita del usuario')
    parser.add_argument('--confirmacion', help=f'Debe ser exactamente {PHRASE}')
    args = parser.parse_args()
    if not args.ejecutar_test_b:
        parser.print_help()
        return
    if args.confirmacion != PHRASE:
        parser.error('Falta confirmación explícita; no se ha leído ningún dataset')
    evaluar()


if __name__ == '__main__':
    main()
