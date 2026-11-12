"""Reproducción separada del pipeline final A; no es el objeto histórico de B."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.mlops.contrato_c import (  # noqa: E402
    FEATURES, POLICY, MODEL_DIR, digest, policy_contract, check_versions,
)


def git_value(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def training_paths(policy):
    """Código local realmente utilizado; nuevo código puede seguir untracked."""
    relative = set(policy['sha256_codigo']) | {
        'scripts/mlops/persistir_pipeline_a.py', 'scripts/mlops/contrato_c.py',
        'requirements-fase2_4.txt', str(POLICY.relative_to(ROOT)).replace('\\', '/'),
        str(POLICY.with_suffix('.sha256').relative_to(ROOT)).replace('\\', '/'),
    }
    return {name: ROOT / name for name in sorted(relative)}


def verify_integrity(source, expected_a, expected_head, paths, expected_hashes):
    """Detecta cambios en puntos de control; NO bloquea escrituras concurrentes."""
    if git_value('rev-parse', 'HEAD') != expected_head:
        raise ValueError('HEAD cambió o no coincide con el esperado')
    a_hash = digest(source)
    if a_hash != expected_a:
        raise ValueError('A cambió o no coincide con el hash congelado')
    hashes = {name: digest(path) for name, path in paths.items()}
    if hashes != expected_hashes:
        raise ValueError('Código, política o sidecar cambiaron')
    return dict(commit=expected_head, dataset_a_sha256=a_hash, archivos_sha256=hashes)


def write_json_exclusive(path, value):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.flush()
        os.fsync(handle.fileno())


def training_components():
    # Estos main() NO se ejecutan al importar; huellas verificadas antes de importar.
    sys.path.insert(0, str(ROOT / 'scripts/modelado'))
    from comparar_ensembles import load_data
    from entrenar_baselines_logistica import make_model, NUMERIC, CATEGORICAL
    return load_data, make_model, NUMERIC + CATEGORICAL


def publish_model(model, metadata, output, check):
    """Publicación controlada: marcador atómico ÚLTIMO, sin sobrescritura.

    Un conjunto de archivos no es transacción atómica. El lector solo acepta
    modelo+manifiesto cuyos hashes coincidan con finalizado.json. Parciales,
    reserva y fallos se conservan. Requiere hard links locales (NTFS).
    """
    import joblib

    model_partial = output / 'pipeline.joblib.partial'
    with model_partial.open('xb') as handle:
        joblib.dump(model, handle, compress=3)
        handle.flush()
        os.fsync(handle.fileno())
    metadata['modelo_sha256'] = digest(model_partial)
    metadata['controles_integridad']['antes_publicacion'] = check()
    manifest_partial = output / 'manifiesto.json.partial'
    write_json_exclusive(manifest_partial, metadata)
    # Links exclusivos: jamás os.replace ni reemplazo de artefactos previos.
    os.link(model_partial, output / 'pipeline.joblib')
    os.link(manifest_partial, output / 'manifiesto.json')
    check()  # HEAD/A/código otra vez antes del marcador válido.
    if digest(output / 'pipeline.joblib') != metadata['modelo_sha256']:
        raise ValueError('Modelo publicado no coincide')
    manifest_hash = digest(output / 'manifiesto.json')
    if manifest_hash != digest(manifest_partial):
        raise ValueError('Manifiesto publicado no coincide')
    marker_partial = output / 'finalizado.json.partial'
    write_json_exclusive(marker_partial, dict(
        version=2, estado='FINALIZADO', fecha_utc=datetime.now(timezone.utc).isoformat(),
        modelo_sha256=metadata['modelo_sha256'], manifiesto_sha256=manifest_hash,
        reserva_sha256=digest(output / 'reserva.json'), commit=metadata['commit'],
    ))
    os.link(marker_partial, output / 'finalizado.json')
    # No limpiar automáticamente ni siquiera los parciales propios.


def reproduce_a(expected_head):
    """Solo se llama desde flag explícito; fuente A fija y salida exclusiva."""
    if not isinstance(expected_head, str) or len(expected_head) != 40 or any(c not in '0123456789abcdef' for c in expected_head):
        raise ValueError('HEAD esperado debe ser SHA Git completo')
    if MODEL_DIR.exists():
        raise FileExistsError('Artefactos o reserva previos: no sobrescribir ni borrar')
    if git_value('rev-parse', 'HEAD') != expected_head:
        raise ValueError('HEAD no coincide con el esperado antes de entrenar')
    policy_hash_initial = digest(POLICY)
    sidecar_hash_initial = digest(POLICY.with_suffix('.sha256'))
    policy = policy_contract()
    versions = check_versions(policy)
    source = ROOT / policy['dataset_a']['ruta']
    if source.resolve() != source.absolute() or source.is_symlink():
        raise ValueError('A redirigido')
    paths = training_paths(policy)
    expected_hashes = {name: digest(path) for name, path in paths.items()}
    policy_key = str(POLICY.relative_to(ROOT)).replace('\\', '/')
    sidecar_key = str(POLICY.with_suffix('.sha256').relative_to(ROOT)).replace('\\', '/')
    if expected_hashes[policy_key] != policy_hash_initial or expected_hashes[sidecar_key] != sidecar_hash_initial:
        raise ValueError('Política o sidecar cambiaron durante el preflight')
    if any(expected_hashes[name] != expected for name, expected in policy['sha256_codigo'].items()):
        raise ValueError('Código histórico cambió durante el preflight')
    reservation_sha = None

    def check():
        snapshot = verify_integrity(source, policy['dataset_a']['sha256'], expected_head, paths, expected_hashes)
        if reservation_sha is not None and digest(MODEL_DIR / 'reserva.json') != reservation_sha:
            raise ValueError('Reserva de reproducción alterada')
        return snapshot

    checkpoints = dict(antes_carga=check())
    relative_paths = list(paths)
    initial_status = git_value('status', '--porcelain', '--untracked-files=all', '--', *relative_paths)
    # Reserva ANTES de cargar/ajustar A; un fallo conserva el directorio y bloquea repetición automática.
    MODEL_DIR.mkdir(parents=True, exist_ok=False)
    try:
        write_json_exclusive(MODEL_DIR / 'reserva.json', dict(
            estado='INICIADO', fecha_utc=datetime.now(timezone.utc).isoformat(),
            commit=expected_head, integridad_inicial=checkpoints['antes_carga'],
        ))
        reservation_sha = digest(MODEL_DIR / 'reserva.json')
        load_data, make_model, features = training_components()
        if features != list(FEATURES):
            raise ValueError('Features alteradas')
        x, y = load_data()  # EXACTAMENTE carga histórica, todas las filas de A.
        checkpoints['despues_carga'] = check()
        model = make_model('l1', 1.0)
        if model.named_steps['model'].get_params() != policy['hiperparametros']:
            raise ValueError('Hiperparámetros alterados')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            model.fit(x, y)  # Sin CV ni selección adicional.
        checkpoints['despues_ajuste'] = check()
        if caught:
            raise RuntimeError('Avisos al ajustar A: revisar antes de persistir')
        metadata = dict(
            version=2, estado='PIPELINE_A_REPRODUCIDO', publicacion='REQUIERE_MARCADOR_FINALIZADO',
            reserva_sha256=reservation_sha,
            fecha_utc=datetime.now(timezone.utc).isoformat(), commit=expected_head,
            dataset_a_sha256=checkpoints['antes_carga']['dataset_a_sha256'],
            politica_sha256=expected_hashes[policy_key],
            codigo_historico=policy['sha256_codigo'], codigo_entrenamiento_sha256=expected_hashes,
            controles_integridad=checkpoints, features=list(FEATURES),
            hiperparametros=model.named_steps['model'].get_params(), versiones=versions,
            semilla=42, umbral=policy['umbral'], n_a=len(y),
            codigo_git=dict(antes=initial_status,
                            despues=git_value('status', '--porcelain', '--untracked-files=all', '--', *relative_paths),
                            alcance='HEAD identifica repositorio; hashes identifican código nuevo incluso untracked. No se exige inclusión artificial en HEAD.'),
            procedencia='Nuevo ajuste exclusivo A; no es el objeto en memoria del test B histórico.',
            uso_b='NO_LEIDO_NI_UTILIZADO; no comparar para seleccionar artefacto',
            limite_integridad='Hash en puntos de control, no bloqueo físico. Cambios transitorios revertidos entre controles pueden no detectarse. Operador único y entradas estables obligatorios.',
        )
        publish_model(model, metadata, MODEL_DIR, check)
    except BaseException as error:
        # No reemplazar ni borrar reserva/artefactos. Mensaje sin datos individuales.
        failure = MODEL_DIR / 'fallo.json'
        if not failure.exists() and not (MODEL_DIR / 'finalizado.json').exists():
            write_json_exclusive(failure, dict(estado='FALLO_REQUIERE_REVISION', tipo=type(error).__name__))
        raise
    print('Pipeline A reproducido. Sin evaluación B ni inferencia C.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--entrenar-a', action='store_true')
    parser.add_argument('--confirmacion')
    parser.add_argument('--head-esperado', help='SHA Git completo revisado antes de la reproducción')
    args = parser.parse_args(argv)
    if not args.entrenar_a:
        parser.print_help()
        return
    if args.confirmacion != 'REPRODUCIR_PIPELINE_SOLO_A':
        parser.error('Falta confirmación explícita de reproducción A')
    if not args.head_esperado:
        parser.error('Falta --head-esperado; no se infiere ni sustituye una revisión')
    reproduce_a(args.head_esperado)


if __name__ == '__main__':
    main()
