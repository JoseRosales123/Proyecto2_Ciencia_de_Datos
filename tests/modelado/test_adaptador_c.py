"""Normalizaciones y paquete C verificable con fixtures, sin conexiones/modelos."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.mlops import adaptador_c as adapter
from scripts.mlops import features_c as fc
from scripts.mlops.contrato_c import digest


def evidence():
    keys = ('disponibilidad_historica', 'historia_identidad', 'historia_catalogos',
            'timezone_sesion_transmetro', 'timezone_cdc', 'claves_eventos_transurbano',
            'deduplicacion_point_in_time', 'collation_equivalente')
    return dict({key: 'Referencia SINTETICA, no evidencia de datos reales' for key in keys},
                tipo_disponibilidad='HISTORICA_ACREDITADA')


class SourceAdapterTest(unittest.TestCase):
    def normalize(self, source, row, **overrides):
        args = dict(tarjeta_id='CARD:' + 'a' * 64, available_utc='2026-08-29T00:00:00Z',
                    availability_reference='Referencia fixture', evidence=evidence())
        args.update(overrides)
        return adapter.normalize_silver_event(source, row, **args)

    def test_actual_silver_columns_all_sources(self):
        fixtures = [
            ('Transmetro', dict(validacion_id=1, fecha_hora_local='2026-08-28T06:30:00-06:00',
                               tarifa_gtq='1.20', zona_conformada='Zona 1'), '2026-08-28T12:30:00'),
            ('Transurbano', dict(source_row_number=2, fecha_hora_local='2026-08-28T06:30:00',
                                monto_gtq='1.20', zona_conformada='Zona 1'), '2026-08-28T06:30:00'),
            ('MetroRiel', dict(trip_id=3, entry_ts='2026-08-28T06:30:00',
                              fare_gtq='1.20', zona_origen_conformada='Zona 1'), '2026-08-28T06:30:00'),
            ('Aerometro', dict(boarding_id=4, timestamp_utc='2026-08-28T12:30:00Z',
                              tarifa_gtq='1.20', zona_conformada='Zona 1'), '2026-08-28T06:30:00'),
        ]
        for source, row, expected in fixtures:
            with self.subTest(source=source):
                row.update(usuario_fuente='NO_PUBLICAR_FIXTURE', raw_value='NO_PUBLICAR_FIXTURE',
                           ingestion_timestamp='2026-11-01T00:00:00Z')
                result = self.normalize(source, row, source_file_sha256='b' * 64)
                self.assertEqual(result['fecha_feature'], expected)
                self.assertEqual(result['disponible_utc'], '2026-08-29T00:00:00+00:00')
                self.assertEqual(set(result), {'evento_id', 'tarjeta_id', 'sistema', 'fecha_feature',
                                               'disponible_utc', 'zona', 'gasto_gtq'})
                self.assertNotIn('NO_PUBLICAR_FIXTURE', json.dumps(result))

    def test_transurbano_cannot_invent_file_identity(self):
        row = dict(source_row_number=1, fecha_hora_local='2026-08-29T00:00:00', monto_gtq='1', zona_conformada=None)
        with self.assertRaises(adapter.IntegrationBlocked):
            self.normalize('Transurbano', row)
        a = self.normalize('Transurbano', row, source_file_sha256='a' * 64)
        b = self.normalize('Transurbano', row, source_file_sha256='b' * 64)
        self.assertNotEqual(a['evento_id'], b['evento_id'])

    def test_historical_availability_required_no_snapshot_fallback(self):
        row = dict(boarding_id=1, timestamp_utc='2026-08-29T06:00:00Z', tarifa_gtq='1', zona_conformada=None)
        for overrides in [dict(available_utc=None), dict(availability_reference=''), dict(evidence={}),
                          dict(evidence=dict(evidence(), tipo_disponibilidad='SNAPSHOT_FIJO'))]:
            with self.subTest(overrides=overrides), self.assertRaises(adapter.IntegrationBlocked):
                self.normalize('Aerometro', row, **overrides)

    def test_transmetro_silver_naive_rejected_and_private_card_rejected(self):
        row = dict(validacion_id=1, fecha_hora_local='2026-08-29T12:00:00', tarifa_gtq='1', zona_conformada='Zona 1')
        with self.assertRaises(ValueError):
            self.normalize('Transmetro', row)
        row['fecha_hora_local'] += 'Z'
        with self.assertRaises(ValueError):
            self.normalize('Transmetro', row, tarjeta_id='tarjeta_original_fixture')

    def test_money_null_and_negative(self):
        row = dict(trip_id=1, entry_ts='2026-08-29T00:00:00', fare_gtq=None, zona_origen_conformada=None)
        result = self.normalize('MetroRiel', row)
        self.assertEqual(result['gasto_gtq'], '0')
        self.assertEqual(result['zona'], '')
        row['fare_gtq'] = '-1'
        with self.assertRaises(ValueError):
            self.normalize('MetroRiel', row)

    def write_package(self, folder):
        headers = {
            'eventos.csv': ['evento_id', 'tarjeta_id', 'sistema', 'fecha_feature', 'disponible_utc', 'zona', 'gasto_gtq'],
            'identidades.csv': ['tarjeta_id', 'unidad_id', 'sistema', 'vigente_desde', 'disponible_utc', 'seq'],
            'cdc.csv': ['tarjeta_id', 'op', 'commit_utc', 'disponible_utc', 'seq'],
        }
        for name, schema in headers.items():
            with (folder / name).open('w', encoding='utf-8', newline='') as handle:
                csv.writer(handle).writerow(schema)
        metadata = dict(contrato='INFERENCIA_C_NORMALIZADA_V3', fecha_corte='2026-08-30',
                        datos_sinteticos=True, ids_autorizados=True, reloj_features='LEGADO_1_4_SIN_ZONA',
                        corte_disponibilidad_utc='2026-08-30T00:00:00Z',
                        corte_efectivo_cdc_utc='2026-08-30T00:00:00Z',
                        referencia_politica_temporal='Decisión fixture', proveniencia=evidence(),
                        archivos_sha256={name: digest(folder / name) for name in headers})
        (folder / 'contrato_c.json').write_text(json.dumps(metadata), encoding='utf-8')
        return metadata

    def test_verified_v3_package_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.write_package(folder)
            tables = fc.read_inputs(folder, '2026-08-30', with_controls=True)
            self.assertEqual(tables[:3], ([], [], []))
            with (folder / 'eventos.csv').open('a', encoding='utf-8') as handle:
                handle.write('ALTERADO')
            with self.assertRaisesRegex(ValueError, 'Hash'):
                fc.read_inputs(folder, '2026-08-30', with_controls=True)

    def test_v3_rejects_missing_evidence_and_hash_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            metadata = self.write_package(folder)
            metadata['proveniencia'].pop('historia_identidad')
            (folder / 'contrato_c.json').write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaises(adapter.IntegrationBlocked):
                fc.read_inputs(folder, '2026-08-30', with_controls=True)
            metadata = self.write_package(folder)
            metadata['archivos_sha256']['inventado.csv'] = 'a' * 64
            (folder / 'contrato_c.json').write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Inventario'):
                fc.read_inputs(folder, '2026-08-30', with_controls=True)

    def test_no_real_extractor_enabled_by_complete_declarations(self):
        with self.assertRaisesRegex(adapter.IntegrationBlocked, 'no implementado'):
            adapter.require_real_ready(evidence())


if __name__ == '__main__':
    unittest.main(verbosity=2)
