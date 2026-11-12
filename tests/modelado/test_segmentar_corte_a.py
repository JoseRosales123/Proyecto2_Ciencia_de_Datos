"""Fixtures sintéticos de 2.3; nunca abre datasets A/B ni ejecuta clasificador."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'scripts/modelado/segmentar_corte_a.py'
spec = importlib.util.spec_from_file_location('segmentacion_a', SOURCE)
seg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(seg)


def fixture():
    rng = np.random.default_rng(71)
    values = np.vstack([rng.normal(-5, .2, (20, 7)), rng.normal(5, .2, (20, 7))])
    frame = pd.DataFrame(values, columns=seg.FEATURES)
    frame['usuario_seudonimo'] = [f'fixture_{i}' for i in range(40)]
    frame['corte'] = 'A'
    frame['fecha_corte'] = '2026-07-01'
    frame['abandono'] = [0, 1] * 20
    frame['tarjeta'] = 'NO_USAR'
    frame['modo_mas_usado'] = 'NO_USAR'
    frame['zona_origen_mas_frecuente'] = 'NO_USAR'
    return frame


class SegmentacionTest(unittest.TestCase):
    def setUp(self):
        self.frame = fixture()

    def test_contrato_a(self):
        seg.validate_a(self.frame, expected_n=40, with_target=True, expected_positive=20)
        for col, value in [('corte', 'B'), ('fecha_corte', '2026-07-31')]:
            broken = self.frame.copy(); broken[col] = value
            with self.assertRaises(ValueError):
                seg.validate_a(broken, expected_n=40)

    def test_cardinalidad_identidad_etiqueta(self):
        with self.assertRaises(ValueError):
            seg.validate_a(self.frame)
        broken = self.frame.copy(); broken.loc[1, 'usuario_seudonimo'] = broken.loc[0, 'usuario_seudonimo']
        with self.assertRaises(ValueError):
            seg.validate_a(broken, expected_n=40)
        broken = self.frame.copy(); broken.loc[0, 'abandono'] = 4
        with self.assertRaises(ValueError):
            seg.validate_a(broken, expected_n=40, with_target=True, expected_positive=20)

    def test_orden_y_exclusion_estricta(self):
        features = seg.select_features(self.frame[self.frame.columns[::-1]])
        self.assertEqual(list(features), list(seg.FEATURES))
        changed = self.frame.copy()
        changed['abandono'] = 999; changed['usuario_seudonimo'] = 'CAMBIO'
        changed['modo_mas_usado'] = 'CAMBIO'; changed['posterior'] = 1e9
        pd.testing.assert_frame_equal(features, seg.select_features(changed))

    def test_diagnostico_no_necesita_etiqueta(self):
        frame = self.frame.drop(columns=['abandono'])
        seg.validate_a(frame, expected_n=40)
        seg.scale_features(frame)

    def test_conversion_imputacion_escalado(self):
        frame = self.frame.copy(); frame.loc[0, seg.FEATURES[0]] = np.nan
        x, _ = seg.scale_features(frame)
        self.assertTrue(np.isfinite(x).all())
        np.testing.assert_allclose(x.mean(axis=0), 0, atol=1e-12)
        np.testing.assert_allclose(x.std(axis=0), 1, atol=1e-12)
        frame[seg.FEATURES[0]] = np.nan
        with self.assertRaises(ValueError):
            seg.select_features(frame)

    def test_k_y_muestra_invalidos(self):
        for k in [1, 11, 2.5, True, 40]:
            with self.assertRaises(ValueError):
                seg.validate_k(k, 40)
        for n in [1, 3001, 3.5, True]:
            with self.assertRaises(ValueError):
                seg.sample_indices(40, n)
        self.assertEqual(len(seg.sample_indices(40)), 40)
        self.assertEqual(len(seg.sample_indices(5000)), 3000)
        np.testing.assert_array_equal(seg.sample_indices(5000), seg.sample_indices(5000))

    def test_reproducibilidad_sin_y(self):
        x, _ = seg.scale_features(self.frame)
        m1 = seg.fit_segments(x, 2); m2 = seg.fit_segments(x, 2)
        np.testing.assert_array_equal(m1.labels_, m2.labels_)
        self.assertEqual(m1.get_params()['n_init'], 10)
        self.assertEqual(m1.get_params()['algorithm'], 'lloyd')

    def test_silueta_sin_representacion_no_inventa(self):
        x, _ = seg.scale_features(self.frame)
        labels = np.array([0] * 20 + [1] * 20)
        score, message, counts = seg.sampled_silhouette(x, labels, np.arange(20), 2)
        self.assertIsNone(score); self.assertTrue(message); self.assertEqual(counts, [20, 0])

    def test_barrido_k1_sin_silueta(self):
        x, _ = seg.scale_features(self.frame)
        rows = seg.scan_k(x, sample_size=40, candidates=[2, 3])
        self.assertEqual([row['k'] for row in rows], [1, 2, 3])
        self.assertIsNone(rows[0]['silueta'])
        self.assertGreater(rows[1]['silueta'], .8)
        self.assertGreaterEqual(rows[0]['inercia'], rows[1]['inercia'])

    def test_pca_y_perfiles_solo_agregados(self):
        x, _ = seg.scale_features(self.frame)
        model = seg.fit_segments(x, 2)
        coords, variance = seg.project_pca(x)
        profiles = seg.segment_profiles(self.frame, model.labels_)
        self.assertEqual(coords.shape, (40, 2))
        self.assertAlmostEqual(variance['pc1'] + variance['pc2'], variance['acumulada'])
        self.assertEqual(sum(p['tamano'] for p in profiles), 40)
        self.assertEqual(set(profiles[0]['medianas']), set(seg.FEATURES))
        self.assertNotIn('fixture_', json.dumps(profiles))
        self.assertNotIn('NO_USAR', json.dumps(profiles))

    def test_carga_fuente_fija_y_usecols(self):
        def fake_read(*args, **kwargs):
            self.assertEqual(args[0], seg.INPUT_A)
            allowed = kwargs['usecols']
            self.assertFalse(allowed('abandono'))
            self.assertFalse(allowed('tarjeta'))
            return self.frame.drop(columns=['abandono'])
        with patch.object(pd, 'read_csv', side_effect=fake_read), patch.object(seg, 'validate_a'):
            seg.load_a()

    def test_importar_help_y_sin_modo_no_ejecutan(self):
        with patch.object(pd, 'read_csv', side_effect=AssertionError('No datasets')):
            new = importlib.util.module_from_spec(spec); spec.loader.exec_module(new)
            with patch.object(new, 'load_a', side_effect=AssertionError('No carga')):
                new.main([])
                with self.assertRaises(SystemExit) as exit_status:
                    new.main(['--help'])
                self.assertEqual(exit_status.exception.code, 0)

    def test_cli_exige_k_justificado_antes_de_leer(self):
        with patch.object(seg, 'load_a', side_effect=AssertionError('No carga')):
            for args in [['--k', '2'], ['--k', '11', '--justificacion', 'x'],
                         ['--analizar-k', '--k', '2'], ['--analizar-k', '--muestra-silueta', '3001']]:
                with self.assertRaises(SystemExit):
                    seg.main(args)

    def test_exportacion_agregada_y_no_sobrescritura(self):
        x, _ = seg.scale_features(self.frame)
        model = seg.fit_segments(x, 2)
        coords, variance = seg.project_pca(x)
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / 'final'
            seg.write_aggregates(out, {'varianza': variance},
                                 profiles=seg.segment_profiles(self.frame, model.labels_),
                                 coordinates=coords, labels=model.labels_)
            self.assertEqual({p.name for p in out.iterdir()}, {'resumen.json', 'perfiles.csv', 'pca_2d.png'})
            for path in [out / 'resumen.json', out / 'perfiles.csv']:
                text = path.read_text(encoding='utf-8')
                self.assertNotIn('fixture_', text)
                self.assertNotIn('usuario_seudonimo', text)
                self.assertNotIn('NO_USAR', text)
            with self.assertRaises(FileExistsError):
                seg.write_aggregates(out, {})


if __name__ == '__main__':
    with threadpool_limits(limits=1):
        unittest.main(verbosity=2)
