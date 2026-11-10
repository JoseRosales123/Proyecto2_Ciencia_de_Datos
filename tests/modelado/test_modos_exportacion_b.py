"""Solo fixtures temporales sintéticos; nunca usa B ni conecta a PostgreSQL.

python tests/modelado/test_modos_exportacion_b.py -v
"""
import contextlib
import copy
from datetime import date
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'exportador_b_bajo_prueba', ROOT / 'scripts/modelado/exportar_dataset_corte_b.py')
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)  # El módulo solo importa stdlib; no invoca exportar.


class ModosExportacion(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='fixture_modos_sinteticos_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        paths = {
            'ROOT': self.root, 'LOCAL': self.root / 'privado_fixture',
            'OUTPUT': self.root / 'privado_fixture/fixture_salida.csv',
            'PARTIAL': self.root / 'privado_fixture/fixture_parcial',
            'MANIFEST': self.root / 'privado_fixture/fixture_manifiesto.json',
            'LEDGER': self.root / 'privado_fixture/fixture_reserva.jsonl',
            'ACTA': self.root / 'privado_fixture/fixture_acta.json',
            'POLICY': self.root / 'fixture_policy.json',
            'PROPOSAL': self.root / 'fixture_propuesta.md',
            '__file__': str(self.root / 'fixture_exportador.py'),
        }
        for key, value in paths.items():
            p = patch.object(module, key, value)
            p.start()
            self.addCleanup(p.stop)
        module.LOCAL.mkdir()
        module.PROPOSAL.write_text('PROPUESTA SINTETICA', encoding='utf-8')
        Path(module.__file__).write_text('# FIXTURE DE HUELLA', encoding='utf-8')
        self.policy = {'estado_b': 'NO_EJECUTADO', 'estado_politica': 'CONGELADA',
                       'caracteristicas': module.NUMERIC + module.CATEGORICAL,
                       'fecha_congelacion_utc': '2020-01-01T00:00:00+00:00'}
        module.POLICY.write_text(json.dumps(self.policy), encoding='utf-8')
        module.POLICY.with_suffix('.sha256').write_text(module.digest(module.POLICY), encoding='utf-8')
        evidence = self.root / 'docs/reportes_fase2_2/cobertura_fuentes/fixture/resultado.json'
        evidence.parent.mkdir(parents=True)
        evidence.write_text('{"fixture": true, "certificado": false}', encoding='utf-8')
        snapshot = {'id': 'SNAPSHOT_FICTICIO', 'descripcion': 'Solo datos sinteticos de prueba',
                    'fecha_snapshot_utc': '2020-01-02T00:00:00+00:00',
                    'evidencias': [{'ruta': evidence.relative_to(self.root).as_posix(),
                                    'sha256': module.digest(evidence)}]}
        self.commit = 'a' * 40
        self.acta = {'version': 1, 'id': 'ACTA_FICTICIA_NO_OPERATIVA', 'estado': 'APROBADA',
                     'tipo_respaldo': module.LIMITED, 'certificado_origen': False,
                     'evaluacion_b': 'NO_EJECUTADO', 'acepta_limitaciones': True,
                     'aprobado_por': 'FIXTURE', 'referencia_aprobacion_enmienda': 'FIXTURE',
                     'referencia_autorizacion_exportacion': 'FIXTURE',
                     'fecha_utc': '2020-01-03T00:00:00+00:00',
                     'validacion_academica': {'estado': 'APROBADA', 'referencia': 'FIXTURE'},
                     'propuesta_sha256': module.digest(module.PROPOSAL),
                     'politica_sha256': module.digest(module.POLICY),
                     'exportador_sha256': module.digest(Path(module.__file__)),
                     'commit': self.commit, 'snapshot': snapshot}
        self.update_snapshot_hash(self.acta)
        self.connect = Mock(side_effect=AssertionError('Prohibido conectar en pruebas'))
        for p in (
            patch.object(module, 'require_private'),
            patch.object(module, 'git_value', side_effect=lambda *a: self.commit if a[0] == 'rev-parse' else ''),
            patch.dict(sys.modules, {'psycopg': SimpleNamespace(connect=self.connect),
                                     'dotenv': SimpleNamespace(load_dotenv=Mock())}),
        ):
            p.start()
            self.addCleanup(p.stop)

    @staticmethod
    def update_snapshot_hash(acta):
        raw = json.dumps(acta['snapshot'], sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False).encode('utf-8')
        acta['snapshot_sha256'] = hashlib.sha256(raw).hexdigest()

    def write_acta(self, acta=None):
        # Exclusivamente dentro del directorio temporal fixture, nunca en LOCAL real.
        module.ACTA.write_text(json.dumps(self.acta if acta is None else acta), encoding='utf-8')
        return module.digest(module.ACTA)

    def limited_export(self, checksum):
        return module.exportar(modo=module.LIMITED, confirmacion=module.LIMITED_PHRASE,
                               acta_sha256=checksum, snapshot_id='SNAPSHOT_FICTICIO')

    def assert_no_access(self):
        self.connect.assert_not_called()
        self.assertFalse(module.LEDGER.exists())
        self.assertFalse(module.OUTPUT.exists())

    def test_sin_opciones_solo_ayuda(self):
        with patch.object(module, 'exportar') as export, contextlib.redirect_stdout(io.StringIO()):
            module.main([])
        export.assert_not_called()
        self.assert_no_access()

    def test_modos_excluyentes(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            module.main(['--exportar-b', '--certificacion-de-origen',
                         '--aceptacion-limitada-del-snapshot'])
        self.assert_no_access()

    def test_llamada_directa_sin_autorizacion(self):
        with self.assertRaises(ValueError):
            module.exportar()
        with self.assertRaises(ValueError):
            module.exportar(modo=module.LIMITED, acta_sha256='a'*64, snapshot_id='FIXTURE')
        self.assert_no_access()

    def test_falta_modo_en_cli(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            module.main(['--exportar-b', '--confirmacion', module.PHRASE,
                         '--cobertura-confirmada-hasta', '2026-08-30'])
        self.assert_no_access()

    def test_certificacion_preserva_fecha_y_confirmacion(self):
        expected = module.validate_request(module.CERTIFIED, module.PHRASE,
                                           date(2026, 8, 30), None, None)
        self.assertEqual(expected['cobertura_declarada_hasta_exclusiva'], '2026-08-30')
        for coverage in (None, date(2026, 8, 29)):
            with self.subTest(coverage=coverage), self.assertRaises(ValueError):
                module.validate_request(module.CERTIFIED, module.PHRASE, coverage, None, None)
        with self.assertRaises(ValueError):
            module.validate_request(module.CERTIFIED, module.PHRASE, date(2026, 8, 30), 'a'*64, 'x')
        self.assert_no_access()

    def test_limitado_no_admite_fecha_ni_confirmacion_generica(self):
        for coverage, phrase in [(date(2026, 8, 30), module.LIMITED_PHRASE), (None, module.PHRASE)]:
            with self.subTest(coverage=coverage, phrase=phrase), self.assertRaises(ValueError):
                module.exportar(coverage, modo=module.LIMITED, confirmacion=phrase,
                                acta_sha256='a'*64, snapshot_id='SNAPSHOT_FICTICIO')
        self.assert_no_access()

    def test_falta_acta(self):
        with self.assertRaises(FileNotFoundError):
            self.limited_export('a'*64)
        self.assert_no_access()

    def test_acta_no_aprobada_o_incompleta(self):
        for key, value in [('estado', 'PENDIENTE'), ('acepta_limitaciones', False),
                           ('certificado_origen', True), ('referencia_autorizacion_exportacion', ''),
                           ('validacion_academica', {'estado': 'PENDIENTE', 'referencia': ''})]:
            acta = copy.deepcopy(self.acta)
            acta[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.limited_export(self.write_acta(acta))
            self.assert_no_access()

    def test_hash_externo_acta_incorrecto(self):
        self.write_acta()
        with self.assertRaises(ValueError):
            self.limited_export('0'*64)
        self.assert_no_access()

    def test_hashes_y_commit_incorrectos(self):
        for key in ('propuesta_sha256', 'politica_sha256', 'exportador_sha256', 'commit', 'snapshot_sha256'):
            acta = copy.deepcopy(self.acta)
            acta[key] = '0'*64
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.limited_export(self.write_acta(acta))
            self.assert_no_access()

    def test_snapshot_no_coincide(self):
        acta = copy.deepcopy(self.acta)
        acta['snapshot']['id'] = 'OTRO_FIXTURE'
        self.update_snapshot_hash(acta)
        with self.assertRaises(ValueError):
            self.limited_export(self.write_acta(acta))
        self.assert_no_access()

    def test_evidencia_alterada_y_ruta_no_permitida(self):
        for route in (None, 'privado_fixture/fixture_salida.csv'):
            acta = copy.deepcopy(self.acta)
            if route is None:
                acta['snapshot']['evidencias'][0]['sha256'] = '0'*64
            else:
                acta['snapshot']['evidencias'][0]['ruta'] = route
            self.update_snapshot_hash(acta)
            with self.subTest(route=route), self.assertRaises(ValueError):
                self.limited_export(self.write_acta(acta))
            self.assert_no_access()

    def test_archivos_aprobados_con_cambios(self):
        with patch.object(module, 'git_value', side_effect=lambda *a: self.commit
                          if a[0] == 'rev-parse' else (' M fixture' if a[0] == 'status' else '')):
            with self.assertRaises(ValueError):
                self.limited_export(self.write_acta())
        self.assert_no_access()

    def test_intento_repetido_bloquea_sin_conectar(self):
        module.LEDGER.write_text('RESERVA FICTICIA PREVIA', encoding='utf-8')
        before = module.LEDGER.read_bytes()
        with self.assertRaises(FileExistsError):
            self.limited_export(self.write_acta())
        self.connect.assert_not_called()
        self.assertEqual(module.LEDGER.read_bytes(), before)
        self.assertFalse(module.OUTPUT.exists())

    def test_acta_sintetica_valida_solo_preflight(self):
        checksum = self.write_acta()
        metadata = module.validate_request(module.LIMITED, module.LIMITED_PHRASE,
                                           None, checksum, 'SNAPSHOT_FICTICIO')
        metadata.update(module.validate_acta(checksum, 'SNAPSHOT_FICTICIO', self.policy))
        self.assertIs(metadata['certificado_origen'], False)
        self.assertNotIn('cobertura_declarada_hasta_exclusiva', metadata)
        self.assertEqual(metadata['snapshot_id'], 'SNAPSHOT_FICTICIO')
        self.assert_no_access()


if __name__ == '__main__':
    unittest.main()
