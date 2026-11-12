"""Fase 2.3: segmentación independiente, exclusivamente A; importar no lee ni ajusta."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import warnings

ROOT = Path(__file__).resolve().parents[2]
INPUT_A = ROOT / 'datos_modelado_local/fase1_4/dataset_corte_A.csv'
REPORTS = ROOT / 'docs/reportes_fase2_3'
FEATURES = (
    'eventos_ultimos_7_dias', 'eventos_ultimos_28_dias',
    'cantidad_modos_distintos', 'dias_desde_ultimo_evento',
    'proporcion_eventos_hora_pico', 'gasto_acumulado_gtq',
    'gasto_promedio_evento_gtq',
)
CATEGORIES = ('modo_mas_usado', 'zona_origen_mas_frecuente')
SEED = 42
MAX_SAMPLE = 3000


def validate_k(k, n):
    if type(k) is not int or not 2 <= k <= 10 or k >= n:
        raise ValueError('k debe ser entero entre 2 y 10 y menor que N')


def select_features(frame):
    """Lista positiva estricta: ni etiqueta, categorías, IDs o fechas entran a X."""
    import numpy as np
    import pandas as pd

    if any(col not in frame for col in FEATURES):
        raise ValueError('Faltan características numéricas de A')
    numeric = frame.loc[:, list(FEATURES)].apply(pd.to_numeric, errors='coerce')
    if numeric.isna().all().any() or np.isinf(numeric.to_numpy()).any():
        raise ValueError('Feature enteramente nula o con infinitos')
    return numeric


def validate_a(frame, *, expected_n=60664, with_target=False, expected_positive=8110):
    """Contrato A; fecha/corte se comprueban cuando existen como en 1.4/2.1.

    Exige además identidad no nula y única. En diagnóstico no consulta abandono.
    Los parámetros de conteos permiten fixtures, no se exponen en CLI.
    """
    import pandas as pd

    if len(frame) != expected_n:
        raise ValueError('Cardinalidad incompatible con A')
    if 'corte' in frame and not frame['corte'].astype(str).eq('A').all():
        raise ValueError('Solo se admite corte A')
    if 'fecha_corte' in frame and not pd.to_datetime(
        frame['fecha_corte'], errors='coerce'
    ).eq(pd.Timestamp('2026-07-01')).all():
        raise ValueError('Fecha distinta del corte A')
    if 'usuario_seudonimo' not in frame or frame.usuario_seudonimo.isna().any() or frame.usuario_seudonimo.duplicated().any():
        raise ValueError('Identidad de A ausente, nula o duplicada')
    select_features(frame)
    if with_target:
        target = pd.to_numeric(frame['abandono'], errors='coerce')
        if not target.isin([0, 1]).all() or target.sum() != expected_positive:
            raise ValueError('Etiqueta o positivos incompatibles con A')


def load_a(*, with_target=False):
    """Sin argumento de entrada: rechaza redirección del único CSV A permitido."""
    import pandas as pd

    if INPUT_A.is_symlink() or INPUT_A.resolve() != INPUT_A.absolute():
        raise ValueError('No se permite redirigir la fuente A')
    allowed = set(FEATURES) | {'usuario_seudonimo', 'corte', 'fecha_corte'}
    if with_target:
        allowed |= {'abandono', *CATEGORIES}
    frame = pd.read_csv(INPUT_A, encoding='utf-8-sig', low_memory=False,
                        usecols=lambda col: col in allowed)
    validate_a(frame, with_target=with_target)
    return frame


def scale_features(frame):
    from sklearn.impute import SimpleImputer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler

    prep = make_pipeline(SimpleImputer(strategy='median'), StandardScaler())
    return prep.fit_transform(select_features(frame)), prep


def make_kmeans(k):
    from sklearn.cluster import KMeans

    return KMeans(n_clusters=k, init='k-means++', n_init=10,
                  random_state=SEED, algorithm='lloyd')


def sample_indices(n, sample_size=MAX_SAMPLE):
    import numpy as np

    if type(sample_size) is not int or not 2 <= sample_size <= MAX_SAMPLE or n < 2:
        raise ValueError('Muestra debe estar entre 2 y 3000; N >= 2')
    return np.random.default_rng(SEED).choice(n, size=min(n, sample_size), replace=False)


def sampled_silhouette(x, labels, indices, k):
    """Misma muestra uniforme para todos los k, sin reposición ni usar y.

    Al menos dos observaciones por cluster: condición mínima, no garantía de
    precisión. Si falta representación devuelve None con motivo, nunca rellena.
    """
    import numpy as np
    from sklearn import config_context
    from sklearn.metrics import silhouette_score

    counts = np.bincount(np.asarray(labels)[indices], minlength=k)
    if len(np.unique(labels)) != k or len(counts) != k or (counts < 2).any():
        return None, 'Muestra insuficiente: se exigen >=2 observaciones por cluster', counts.tolist()
    with config_context(working_memory=64):
        score = float(silhouette_score(x[indices], np.asarray(labels)[indices]))
    return score, None, counts.tolist()


def scan_k(x, sample_size=MAX_SAMPLE, candidates=range(2, 11)):
    indices = sample_indices(len(x), sample_size)
    rows = []
    # k=1 solo referencia de inercia; no se calcula silueta.
    reference = make_kmeans(1).fit(x)
    rows.append(dict(k=1, inercia=float(reference.inertia_), silueta=None,
                     advertencia='Referencia de codo; silueta no definida',
                     muestra_n=0, conteos_muestra=[]))
    for k in candidates:
        validate_k(k, len(x))
        model = make_kmeans(k).fit(x)
        score, message, counts = sampled_silhouette(x, model.labels_, indices, k)
        if message:
            warnings.warn(f'k={k}: {message}', RuntimeWarning)
        rows.append(dict(k=k, inercia=float(model.inertia_), silueta=score,
                         advertencia=message, muestra_n=len(indices), conteos_muestra=counts))
    return rows


def fit_segments(x, k):
    validate_k(k, len(x))
    model = make_kmeans(k).fit(x)
    if len(set(model.labels_)) != k:
        raise ValueError('No se obtuvieron k clusters distintos')
    return model


def project_pca(x):
    from sklearn.decomposition import PCA

    pca = PCA(n_components=2, svd_solver='full')
    coordinates = pca.fit_transform(x)
    return coordinates, dict(pc1=float(pca.explained_variance_ratio_[0]),
                             pc2=float(pca.explained_variance_ratio_[1]),
                             acumulada=float(pca.explained_variance_ratio_.sum()))


def segment_profiles(frame, labels):
    """Solo después de fijar k; medianas en unidades originales, no imputadas.

    Categorías reservadas para interpretación manual posterior; no se exportan
    textos libres potencialmente identificables. No se exportan asignaciones.
    """
    import numpy as np
    import pandas as pd

    original = select_features(frame)
    y = pd.to_numeric(frame['abandono'], errors='coerce')
    if len(labels) != len(frame) or not y.isin([0, 1]).all():
        raise ValueError('Etiquetas o asignaciones inválidas')
    rows = []
    for label in sorted(set(labels)):
        mask = np.asarray(labels) == label
        medians = original.loc[mask].median()
        rows.append(dict(segmento=int(label), nombre=f'Segmento {int(label)} (revisar perfil)',
                         tamano=int(mask.sum()), porcentaje=float(mask.mean() * 100),
                         tasa_abandono=float(y.loc[mask].mean()),
                         medianas={col: None if pd.isna(medians[col]) else float(medians[col]) for col in FEATURES}))
    return rows


def write_aggregates(output, metadata, *, diagnostic=None, profiles=None, coordinates=None, labels=None):
    """Directorio exclusivo; solo JSON/CSV agregados y PNG sin IDs/tooltips."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import pandas as pd

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'resumen.json').open('x', encoding='utf-8') as handle:
        json.dump(dict(metadata, diagnostico_k=diagnostic, perfiles=profiles),
                  handle, ensure_ascii=False, indent=2, allow_nan=False)
    if diagnostic is not None:
        pd.DataFrame(diagnostic).drop(columns=['conteos_muestra']).to_csv(output / 'diagnostico_k.csv', index=False)
        for key, filename, ylabel in [('inercia', 'codo.png', 'Inercia A completa'),
                                      ('silueta', 'silueta.png', 'Silueta estimada en muestra A')]:
            fig, ax = plt.subplots()
            available = [r for r in diagnostic if r[key] is not None]
            ax.plot([r['k'] for r in available], [r[key] for r in available], 'o-')
            ax.set(xlabel='k', ylabel=ylabel, title='Diagnóstico no supervisado — solo A')
            fig.tight_layout(); fig.savefig(output / filename, dpi=160); plt.close(fig)
    if profiles is not None:
        pd.json_normalize(profiles, sep='_').to_csv(output / 'perfiles.csv', index=False)
        fig, ax = plt.subplots()
        ax.scatter(coordinates[:, 0], coordinates[:, 1], c=labels, cmap='tab10', s=3, alpha=0.25)
        ax.set(xlabel='PC1', ylabel='PC2', title='Segmentos A: observaciones sintéticas; proyección PCA')
        fig.tight_layout(); fig.savefig(output / 'pca_2d.png', dpi=160); plt.close(fig)


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_mutually_exclusive_group()
    modes.add_argument('--analizar-k', action='store_true')
    modes.add_argument('--k', type=int)
    cli.add_argument('--justificacion', help='Decisión previa basada en codo/silueta; obligatoria con --k')
    cli.add_argument('--muestra-silueta', type=int, default=MAX_SAMPLE)
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if not args.analizar_k and args.k is None:
        cli.print_help()
        return
    if not 2 <= args.muestra_silueta <= MAX_SAMPLE:
        cli.error('--muestra-silueta debe estar entre 2 y 3000')
    if args.k is not None and (not 2 <= args.k <= 10 or not args.justificacion or not args.justificacion.strip()):
        cli.error('--k requiere 2..10 y --justificacion previa no vacía')
    if args.analizar_k and args.justificacion:
        cli.error('El diagnóstico no selecciona k; no admite justificación de selección')
    output = REPORTS / ('diagnostico_k' if args.analizar_k else f'segmentacion_k{args.k}')
    if output.exists():
        raise FileExistsError('Salida previa: no sobrescribir')
    # Leer y no se permite antes de decidir k: diagnóstico no carga abandono.
    frame = load_a(with_target=args.k is not None)
    x, _ = scale_features(frame)
    import numpy as np
    import pandas as pd
    import sklearn
    metadata = dict(corte='A', fecha_corte='2026-07-01', n=len(frame), features=list(FEATURES),
                    categorias_distancia=False, semilla=SEED, init='k-means++', n_init=10,
                    algorithm='lloyd', imputacion='mediana A', escalado='StandardScaler A',
                    fecha_utc=datetime.now(timezone.utc).isoformat(),
                    commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    versiones=dict(numpy=np.__version__, pandas=pd.__version__, sklearn=sklearn.__version__),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    limitaciones='Solo A sintético; relaciones descriptivas, no causales. Clasificador 2.2 intacto.')
    if args.analizar_k:
        metadata.update(modo='DIAGNOSTICO_K', muestra_max=args.muestra_silueta,
                        muestreo='Uniforme fijo sin reposición, semilla 42; >=2 por cluster o sin puntuación. No garantiza precisión en clusters pequeños.',
                        memoria_silueta_mb=64, etiqueta_usada=False)
        write_aggregates(output, metadata, diagnostic=scan_k(x, args.muestra_silueta))
    else:
        model = fit_segments(x, args.k)
        coords, variance = project_pca(x)
        metadata.update(modo='SEGMENTACION_FINAL', k=args.k, justificacion=args.justificacion,
                        varianza_pca=variance, pca_uso='Solo visualización; KMeans usa siete dimensiones',
                        etiqueta_uso='Solo perfiles posteriores a decisión k; nunca distancia/selección',
                        pendiente='Interpretar nombres y proponer acciones distintas para >=2 segmentos; revisar tamaños pequeños antes de publicar.')
        write_aggregates(output, metadata, profiles=segment_profiles(frame, model.labels_),
                         coordinates=coords, labels=model.labels_)
    print('Agregados A creados. No se modificó ni ejecutó el clasificador de 2.2.')


if __name__ == '__main__':
    main()
