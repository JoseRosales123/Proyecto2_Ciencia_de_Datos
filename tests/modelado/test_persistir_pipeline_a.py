"""Integridad de persistencia con archivos temporales y fit FALSO, sin A/B reales."""
from contextlib import contextmanager, ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.mlops import persistir_pipeline_a as persist
from scripts.mlops.contrato_c import FEATURES, digest

HEAD = 'a' * 40


class FakeModel:
    def __init__(self, state, params):
        self.state, self.params = state, params
        self.fit_calls = 0
        self.named_steps = {'model': self}

    def get_params(self):
        return self.params

    def fit(self, x, y):
        # No sklearn ni algoritmo: solo comprueba objetos y dispara mutaciones.
        assert x is self.state['x'] and y is self.state['y']
        self.fit_calls += 1
        self.state['on_fit']()
        return self


@contextmanager
def harness():
    with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
        root = Path(tmp)
        source = root / 'fixture_a.txt'
        source.write_bytes(b'fixture sintetico; no dataset real')
        names = ['politica.json', 'politica.sha256', 'scripts/mlops/persistir_pipeline_a.py',
                 'scripts/mlops/contrato_c.py', 'requirements-fase2_4.txt', 'historico.py']
        paths = {}
        for name in names:
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('contenido sintetico ' + name).encode())
            paths[name] = path
        policy = dict(dataset_a=dict(ruta='fixture_a.txt', sha256=digest(source)),
                      sha256_codigo={'historico.py': digest(paths['historico.py'])},
                      hiperparametros={'C': 1.0, 'random_state': 42},
                      umbral={'numerador': 1, 'denominador': 3, 'comparador': '>='})
        state = dict(head=HEAD, on_load=lambda: None, on_fit=lambda: None,
                     on_dump=lambda: None, x=object(), y=[0, 1, 0], root=root,
                     source=source, paths=paths, policy=policy, output=root / 'output')
        model = FakeModel(state, policy['hiperparametros']); state['model'] = model

        def load():
            state['on_load']()
            return state['x'], state['y']

        def make(penalty, lam):
            assert penalty == 'l1' and lam == 1.0
            return model

        def git(*args):
            return state['head'] if args[0] == 'rev-parse' else '?? scripts/mlops/contrato_c.py'

        def dump(obj, handle, compress):
            assert obj is model and compress == 3
            handle.write(b'artefacto FALSO; no pipeline entrenado')
            state['on_dump']()

        stack.enter_context(patch.multiple(persist, ROOT=root, POLICY=paths['politica.json'], MODEL_DIR=state['output']))
        stack.enter_context(patch.object(persist, 'git_value', side_effect=git))
        stack.enter_context(patch.object(persist, 'policy_contract', return_value=policy))
        stack.enter_context(patch.object(persist, 'check_versions', return_value={'fixture': '1'}))
        stack.enter_context(patch.object(persist, 'training_paths', return_value=paths))
        stack.enter_context(patch.object(persist, 'training_components', return_value=(load, make, list(FEATURES))))
        stack.enter_context(patch('joblib.dump', side_effect=dump))
        yield state


class PersistenceIntegrityTest(unittest.TestCase):
    def assert_failed(self, state, fit_calls):
        output = state['output']
        self.assertTrue((output / 'reserva.json').exists())
        self.assertTrue((output / 'fallo.json').exists())
        self.assertFalse((output / 'finalizado.json').exists())
        self.assertEqual(state['model'].fit_calls, fit_calls)

    def test_success_complete_controlled_bundle(self):
        with harness() as state:
            persist.reproduce_a(HEAD)
            output = state['output']
            metadata = json.loads((output / 'manifiesto.json').read_text())
            marker = json.loads((output / 'finalizado.json').read_text())
            self.assertEqual(state['model'].fit_calls, 1)
            self.assertEqual(marker['estado'], 'FINALIZADO')
            self.assertEqual(marker['modelo_sha256'], digest(output / 'pipeline.joblib'))
            self.assertEqual(marker['manifiesto_sha256'], digest(output / 'manifiesto.json'))
            self.assertEqual(marker['reserva_sha256'], digest(output / 'reserva.json'))
            self.assertEqual(set(metadata['controles_integridad']),
                             {'antes_carga', 'despues_carga', 'despues_ajuste', 'antes_publicacion'})
            self.assertIn('scripts/mlops/contrato_c.py', metadata['codigo_entrenamiento_sha256'])
            self.assertIn('??', metadata['codigo_git']['antes'])  # untracked permitido, no incluido artificialmente en HEAD

    def test_head_expected_rejected_before_loading(self):
        with harness() as state:
            with self.assertRaisesRegex(ValueError, 'HEAD'):
                persist.reproduce_a('b' * 40)
            self.assertFalse(state['output'].exists())
            self.assertEqual(state['model'].fit_calls, 0)

    def test_invalid_head_format(self):
        with harness() as state:
            with self.assertRaises(ValueError):
                persist.reproduce_a('HEAD')
            self.assertFalse(state['output'].exists())

    def test_head_change_after_load(self):
        with harness() as state:
            state['on_load'] = lambda: state.update(head='b' * 40)
            with self.assertRaisesRegex(ValueError, 'HEAD'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 0)

    def test_head_change_during_fit(self):
        with harness() as state:
            state['on_fit'] = lambda: state.update(head='b' * 40)
            with self.assertRaisesRegex(ValueError, 'HEAD'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)

    def test_head_change_before_publication(self):
        with harness() as state:
            state['on_dump'] = lambda: state.update(head='b' * 40)
            with self.assertRaisesRegex(ValueError, 'HEAD'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)
            self.assertFalse((state['output'] / 'pipeline.joblib').exists())

    def test_a_hash_mismatch_before_load(self):
        with harness() as state:
            state['source'].write_bytes(b'otro fixture')
            with self.assertRaisesRegex(ValueError, 'hash congelado'):
                persist.reproduce_a(HEAD)
            self.assertFalse(state['output'].exists())
            self.assertEqual(state['model'].fit_calls, 0)

    def test_preflight_policy_sidecar_or_historical_code_changed(self):
        for name in ('politica.json', 'politica.sha256', 'historico.py'):
            with self.subTest(name=name), harness() as state:
                def mutate(policy):
                    state['paths'][name].write_bytes(b'cambio durante preflight')
                    return {'fixture': '1'}
                persist.check_versions.side_effect = mutate
                with self.assertRaises(ValueError):
                    persist.reproduce_a(HEAD)
                self.assertFalse(state['output'].exists())
                self.assertEqual(state['model'].fit_calls, 0)

    def test_a_changed_after_load(self):
        with harness() as state:
            state['on_load'] = lambda: state['source'].write_bytes(b'cambio en carga')
            with self.assertRaisesRegex(ValueError, 'A cambió'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 0)

    def test_a_changed_after_fit(self):
        with harness() as state:
            state['on_fit'] = lambda: state['source'].write_bytes(b'cambio durante fit falso')
            with self.assertRaisesRegex(ValueError, 'A cambió'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)

    def test_code_policy_and_sidecar_changes(self):
        for name in ('scripts/mlops/contrato_c.py', 'scripts/mlops/persistir_pipeline_a.py',
                     'historico.py', 'politica.json', 'politica.sha256', 'requirements-fase2_4.txt'):
            with self.subTest(name=name), harness() as state:
                state['on_fit'] = lambda: state['paths'][name].write_bytes(b'alteracion sintetica')
                with self.assertRaisesRegex(ValueError, 'cambiaron'):
                    persist.reproduce_a(HEAD)
                self.assert_failed(state, 1)

    def test_no_overwrite_even_failed_reservation(self):
        with harness() as state:
            state['output'].mkdir()
            reservation = state['output'] / 'reserva.json'
            reservation.write_bytes(b'conservar reserva fixture')
            with self.assertRaises(FileExistsError):
                persist.reproduce_a(HEAD)
            self.assertEqual(reservation.read_bytes(), b'conservar reserva fixture')
            self.assertEqual(state['model'].fit_calls, 0)

    def test_serializer_failure_no_valid_publication(self):
        with harness() as state:
            with patch('joblib.dump', side_effect=OSError('fallo serializacion sintetico')):
                with self.assertRaises(OSError):
                    persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)
            self.assertFalse((state['output'] / 'manifiesto.json').exists())

    def test_reservation_mutation_detected(self):
        with harness() as state:
            state['on_fit'] = lambda: (state['output'] / 'reserva.json').write_bytes(b'alterada')
            with self.assertRaisesRegex(ValueError, 'Reserva'):
                persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)

    def test_second_link_failure_bundle_remains_invalid(self):
        import os
        link = os.link
        with harness() as state:
            def fail_manifest(source, target):
                if Path(target).name == 'manifiesto.json':
                    raise OSError('fallo enlace sintetico')
                link(source, target)
            with patch.object(persist.os, 'link', side_effect=fail_manifest):
                with self.assertRaises(OSError):
                    persist.reproduce_a(HEAD)
            self.assert_failed(state, 1)
            self.assertTrue((state['output'] / 'pipeline.joblib').exists())
            self.assertFalse((state['output'] / 'manifiesto.json').exists())

    def test_cli_requires_expected_head(self):
        with patch.object(persist, 'reproduce_a', side_effect=AssertionError('No entrenar')):
            with self.assertRaises(SystemExit):
                persist.main(['--entrenar-a', '--confirmacion', 'REPRODUCIR_PIPELINE_SOLO_A'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
