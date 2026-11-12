"""Inferencia C con pipeline persistido; sin entrenamiento ni acceso a A/B."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path

from scripts.mlops.contrato_c import (
    FEATURES, MODEL_DIR, ROOT, POLICY, digest, cutoff, policy_contract, check_versions,
)
from scripts.mlops.features_c import read_inputs, build_features


def load_model(directory=MODEL_DIR):
    """Solo artefacto local confiable/versionado; joblib no es formato para terceros."""
    import joblib

    directory = Path(directory)
    manifest_path = directory / 'manifiesto.json'
    model_path = directory / 'pipeline.joblib'
    marker_path = directory / 'finalizado.json'
    reservation_path = directory / 'reserva.json'
    for path in (manifest_path, model_path, marker_path, reservation_path):
        if not path.is_file() or path.is_symlink() or path.resolve() != path.absolute():
            raise ValueError('Artefacto incompleto o redirigido')
    if (directory / 'fallo.json').exists():
        raise ValueError('Publicación con fallo registrado; revisar sin cargar')
    policy = policy_contract()
    check_versions(policy)
    metadata = json.loads(manifest_path.read_text(encoding='utf-8'))
    marker = json.loads(marker_path.read_text(encoding='utf-8'))
    if (marker.get('version') != 2 or marker.get('estado') != 'FINALIZADO' or
            marker.get('manifiesto_sha256') != digest(manifest_path) or
            marker.get('modelo_sha256') != digest(model_path) or
            marker.get('reserva_sha256') != digest(reservation_path) or
            marker.get('reserva_sha256') != metadata.get('reserva_sha256') or
            marker.get('commit') != metadata.get('commit')):
        raise ValueError('Marcador de publicación ausente o inconsistente')
    if (metadata.get('version') != 2 or metadata.get('estado') != 'PIPELINE_A_REPRODUCIDO' or
            metadata.get('publicacion') != 'REQUIERE_MARCADOR_FINALIZADO' or
            metadata.get('features') != list(FEATURES) or
            metadata.get('politica_sha256') != digest(POLICY) or
            metadata.get('modelo_sha256') != digest(model_path) or
            metadata.get('umbral') != policy['umbral'] or
            metadata.get('versiones') != policy['versiones'] or
            metadata.get('dataset_a_sha256') != policy['dataset_a']['sha256'] or
            metadata.get('codigo_historico') != policy['sha256_codigo']):
        raise ValueError('Manifiesto del modelo incompatible')
    code_hashes = metadata.get('codigo_entrenamiento_sha256', {})
    required_code = {'scripts/mlops/persistir_pipeline_a.py', 'scripts/mlops/contrato_c.py'}
    if not required_code.issubset(code_hashes):
        raise ValueError('Falta procedencia del código local')
    for name, expected in policy['sha256_codigo'].items():
        if code_hashes.get(name) != expected:
            raise ValueError('Procedencia de código histórico incompatible')
    for stage in ('antes_carga', 'despues_carga', 'despues_ajuste', 'antes_publicacion'):
        snapshot = metadata.get('controles_integridad', {}).get(stage, {})
        if (snapshot.get('commit') != metadata['commit'] or
                snapshot.get('dataset_a_sha256') != metadata['dataset_a_sha256'] or
                snapshot.get('archivos_sha256') != code_hashes):
            raise ValueError('Puntos de control de integridad incompletos o distintos')
    model = joblib.load(model_path)
    if model.named_steps['model'].get_params() != policy['hiperparametros']:
        raise ValueError('Hiperparámetros incompatibles')
    if list(model.feature_names_in_) != list(FEATURES):
        raise ValueError('Orden de features incompatible')
    return model


def prediction_rows(model, features):
    import numpy as np

    if features.unidad_id.duplicated().any():
        raise ValueError('Población duplicada')
    if len(features) == 0:
        return []
    classes = np.asarray(model.classes_)
    if classes.tolist() != [0, 1]:
        raise ValueError('Orden de clases incompatible')
    probabilities = model.predict_proba(features.loc[:, list(FEATURES)])[:, 1]
    if not np.isfinite(probabilities).all() or ((probabilities < 0) | (probabilities > 1)).any():
        raise ValueError('Puntajes inválidos')
    rows = []
    for unit, cards, score in zip(features.unidad_id, features.tarjetas, probabilities):
        # Umbral derivado de fracción, nunca 0.3333 redondeado.
        rows.append(dict(unidad_id=unit, tarjetas=cards, puntaje=float(score),
                         contactar=int(score >= float(Fraction(1, 3)))))
    return sorted(rows, key=lambda row: row['unidad_id'])


def write_predictions(rows, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['unidad_id', 'tarjetas', 'puntaje', 'contactar'])
        writer.writeheader()
        writer.writerows(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--datos', required=True, type=Path)
    parser.add_argument('--fecha-corte', required=True)
    parser.add_argument('--salida', type=Path,
                        default=ROOT / 'datos_modelado_local/fase2_4/predicciones_C.csv')
    args = parser.parse_args(argv)
    cutoff(args.fecha_corte)
    if args.salida.exists():
        raise FileExistsError('Predicciones previas: no sobrescribir')
    events, identities, cdc, controls = read_inputs(args.datos.absolute(), args.fecha_corte, with_controls=True)
    features = build_features(events, identities, cdc, args.fecha_corte, controls=controls)
    model = load_model()
    write_predictions(prediction_rows(model, features), args.salida)
    print('Inferencia C terminada; revisar privacidad antes de publicar cualquier salida.')


if __name__ == '__main__':
    main()
