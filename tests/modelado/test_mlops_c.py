"""Pruebas sintéticas 2.4: sin datasets reales, modelos ajustados ni B."""
import ast
import copy
import csv
from datetime import datetime, timedelta
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import predecir
from scripts.mlops import features_c as fc
from scripts.mlops import persistir_pipeline_a as persist
from scripts.mlops.contrato_c import FEATURES, cutoff, digest, policy_contract, POLICY
from scripts.mlops.contrato_c import TemporalControls, normalize_source_time, normalize_cdc_commit, utc_time
from scripts.mlops import adaptador_c as adapter


def card(n):
    return 'CARD:' + f'{n:064x}'


def unit(n):
    return 'USR:' + f'{n:064x}'


def inputs():
    identities = [dict(tarjeta_id=card(1), unidad_id=unit(1), sistema='Transmetro',
                       vigente_desde='2026-07-01T00:00:00', disponible_utc='2026-07-01T00:00:00Z', seq='1')]
    events = [dict(evento_id=str(i), tarjeta_id=card(1), sistema='Transmetro',
                   fecha_feature=date, disponible_utc='2026-08-29T00:00:00Z', zona='ZONA_SINTETICA', gasto_gtq='1.20')
              for i, date in enumerate(['2026-08-02T06:00:00', '2026-08-23T16:00:00', '2026-08-29T12:00:00'])]
    return events, identities, []


class FakeModel:
    classes_ = np.array([0, 1])

    def predict_proba(self, frame):
        if list(frame) != list(FEATURES):
            raise AssertionError('Orden incorrecto')
        p = np.clip(frame['eventos_ultimos_28_dias'].to_numpy(float) / 10, 0, 1)
        return np.column_stack([1 - p, p])

    def fit(self, *args, **kwargs):
        raise AssertionError('Inferencia no entrena')

    fit_transform = fit


class MlopsCTest(unittest.TestCase):
    def test_cutoff_and_timezones(self):
        self.assertEqual(cutoff('2026-08-30'), datetime(2026, 8, 30))
        for date in ['2026-08-29', '2026-07-31', '2026-08-30T00:00:00']:
            with self.assertRaises(ValueError):
                cutoff(date)
        with self.assertRaises(ValueError):
            fc.feature_time('2026-08-29T00:00:00Z')
        with self.assertRaises(ValueError):
            fc.utc_time('2026-08-29T00:00:00')

    def test_features_windows_and_order(self):
        frame = fc.build_features(*inputs())
        self.assertEqual(list(frame), ['unidad_id', 'tarjetas', *FEATURES])
        row = frame.iloc[0]
        self.assertEqual(row.eventos_ultimos_28_dias, 3)
        self.assertEqual(row.eventos_ultimos_7_dias, 2)
        self.assertEqual(row.dias_desde_ultimo_evento, 1)
        self.assertAlmostEqual(row.gasto_acumulado_gtq, 3.6)
        self.assertAlmostEqual(row.proporcion_eventos_hora_pico, .6667)
        self.assertNotIn('abandono', frame)

    def test_invariance_thirty_days_all_layers(self):
        events, ids, cdc = inputs()
        baseline = fc.build_features(events, ids, cdc)
        changed_events, changed_ids, changed_cdc = copy.deepcopy((events, ids, cdc))
        for day in range(30):
            date = (datetime(2026, 8, 30) + timedelta(days=day)).isoformat()
            changed_events.append(dict(events[0], evento_id='future' + str(day), fecha_feature=date,
                                       disponible_utc=date + 'Z', gasto_gtq='99999'))
        # Incluso una corrección con fecha efectiva antigua no debe entrar si
        # solo estuvo disponible después del corte.
        changed_events.append(dict(events[0], disponible_utc='2026-09-02T00:00:00Z', gasto_gtq='99999'))
        changed_ids.extend([
            dict(ids[0], unidad_id=unit(99), vigente_desde='2026-09-01T00:00:00', seq='9'),
            dict(ids[0], unidad_id=unit(88), disponible_utc='2026-09-01T00:00:00Z', seq='8'),
            dict(ids[0], tarjeta_id=card(99), vigente_desde='2026-09-01T00:00:00'),
        ])
        changed_cdc.append(dict(tarjeta_id=card(1), op='DELETE', commit_utc='2026-09-01T00:00:00Z',
                                disponible_utc='2026-09-01T00:00:00Z', seq='10'))
        after = fc.build_features(changed_events, changed_ids, changed_cdc)
        pd.testing.assert_frame_equal(baseline, after)
        self.assertEqual(predecir.prediction_rows(FakeModel(), baseline),
                         predecir.prediction_rows(FakeModel(), after))

    def test_boundary_and_cdc(self):
        events, ids, cdc = inputs()
        events.append(dict(events[0], evento_id='cut', fecha_feature='2026-08-30T00:00:00'))
        events.append(dict(events[0], evento_id='old', fecha_feature='2026-08-01T23:59:59'))
        self.assertEqual(fc.build_features(events, ids, cdc).iloc[0].eventos_ultimos_28_dias, 3)
        cdc.append(dict(tarjeta_id=card(1), op='delete', commit_utc='2026-08-29T00:00:00Z',
                        disponible_utc='2026-08-29T00:00:00Z', seq='1'))
        self.assertTrue(fc.build_features(events, ids, cdc).empty)

    def test_cards_dedup_order_and_population(self):
        events, ids, cdc = inputs()
        ids.append(dict(ids[0], tarjeta_id=card(2), sistema='Transurbano'))
        ids.append(dict(ids[1]))
        rows = fc.build_features(events + [events[0]], list(reversed(ids)), cdc)
        self.assertEqual(rows.iloc[0].tarjetas, ';'.join([card(1), card(2)]))
        self.assertEqual(rows.iloc[0].eventos_ultimos_28_dias, 3)
        self.assertTrue(fc.build_features(events[:1], ids, cdc).empty)

    def test_reject_private_ids_and_ambiguous_history(self):
        events, ids, cdc = inputs()
        ids[0]['unidad_id'] = 'nombre_real'
        with self.assertRaises(ValueError):
            fc.build_features(events, ids, cdc)
        events, ids, cdc = inputs()
        ids.append(dict(ids[0], unidad_id=unit(2)))
        with self.assertRaises(ValueError):
            fc.build_features(events, ids, cdc)

    def test_threshold_exact_fraction(self):
        frame = pd.concat([fc.build_features(*inputs())] * 3, ignore_index=True)
        frame['unidad_id'] = [unit(i) for i in [3, 1, 2]]
        threshold = 1 / 3
        class BoundaryModel(FakeModel):
            def predict_proba(self, frame):
                p = np.array([np.nextafter(threshold, 0), threshold, np.nextafter(threshold, 1)])
                return np.column_stack([1 - p, p])
        rows = predecir.prediction_rows(BoundaryModel(), frame)
        self.assertEqual([r['unidad_id'] for r in rows], [unit(1), unit(2), unit(3)])
        self.assertEqual([r['contactar'] for r in rows], [1, 1, 0])

    def test_csv_schema_and_no_overwrite(self):
        rows = predecir.prediction_rows(FakeModel(), fc.build_features(*inputs()))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'synthetic.csv'
            predecir.write_predictions(rows, path)
            with path.open(newline='', encoding='utf-8') as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(reader.fieldnames, ['unidad_id', 'tarjetas', 'puntaje', 'contactar'])
                self.assertEqual(len(list(reader)), 1)
            with self.assertRaises(FileExistsError):
                predecir.write_predictions(rows, path)

    def test_folder_schema_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with self.assertRaises(ValueError):
                fc.read_inputs(folder, '2026-08-30')
            metadata = dict(contrato='INFERENCIA_C_NORMALIZADA_V1', fecha_corte='2026-08-30',
                            datos_sinteticos=True, ids_autorizados=True, reloj_features='LEGADO_1_4_SIN_ZONA',
                            corte_disponibilidad_utc='2026-08-30T00:00:00Z')
            (folder / 'contrato_c.json').write_text(json.dumps(metadata), encoding='utf-8')
            headers = [list(inputs()[0][0]), list(inputs()[1][0]),
                       ['tarjeta_id', 'op', 'commit_utc', 'disponible_utc', 'seq']]
            for name, header, rows in zip(['eventos.csv', 'identidades.csv', 'cdc.csv'], headers, inputs()):
                with (folder / name).open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=header); writer.writeheader(); writer.writerows(rows)
            self.assertEqual(len(fc.read_inputs(folder, '2026-08-30')[0]), 3)
            metadata['ids_autorizados'] = False
            (folder / 'contrato_c.json').write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaises(ValueError):
                fc.read_inputs(folder, '2026-08-30')

    def test_load_model_without_fit(self):
        policy = policy_contract()
        class StoredFake(FakeModel):
            feature_names_in_ = np.array(FEATURES)
            named_steps = {'model': type('Parameters', (), {'get_params': lambda self: policy['hiperparametros']})()}
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / 'pipeline.joblib').write_bytes(b'fixture-no-modelo-real')
            hashes = dict(policy['sha256_codigo'], **{
                'scripts/mlops/persistir_pipeline_a.py': 'a' * 64,
                'scripts/mlops/contrato_c.py': 'b' * 64,
            })
            snapshot = dict(commit='a' * 40, dataset_a_sha256=policy['dataset_a']['sha256'], archivos_sha256=hashes)
            metadata = dict(version=2, estado='PIPELINE_A_REPRODUCIDO', features=list(FEATURES),
                            publicacion='REQUIERE_MARCADOR_FINALIZADO', commit='a' * 40,
                            politica_sha256=digest(POLICY), modelo_sha256=digest(folder / 'pipeline.joblib'),
                            umbral=policy['umbral'], versiones=policy['versiones'],
                            dataset_a_sha256=policy['dataset_a']['sha256'], codigo_historico=policy['sha256_codigo'],
                            codigo_entrenamiento_sha256=hashes,
                            controles_integridad={stage: snapshot for stage in
                                ('antes_carga', 'despues_carga', 'despues_ajuste', 'antes_publicacion')})
            (folder / 'reserva.json').write_text('{"estado":"INICIADO"}', encoding='utf-8')
            metadata['reserva_sha256'] = digest(folder / 'reserva.json')
            (folder / 'manifiesto.json').write_text(json.dumps(metadata), encoding='utf-8')
            (folder / 'finalizado.json').write_text(json.dumps(dict(
                version=2, estado='FINALIZADO', commit=metadata['commit'],
                modelo_sha256=metadata['modelo_sha256'], manifiesto_sha256=digest(folder / 'manifiesto.json'),
                reserva_sha256=digest(folder / 'reserva.json'),
            )), encoding='utf-8')
            with patch('joblib.load', return_value=StoredFake()) as loader:
                model = predecir.load_model(folder)
                predecir.prediction_rows(model, fc.build_features(*inputs()))
                loader.assert_called_once()
            saved_marker = (folder / 'finalizado.json').read_bytes()
            (folder / 'finalizado.json').unlink()  # Solo fixture temporal, nunca reserva real.
            with patch('joblib.load', side_effect=AssertionError('No cargar sin cierre')):
                with self.assertRaises(ValueError):
                    predecir.load_model(folder)
            (folder / 'finalizado.json').write_bytes(saved_marker)
            (folder / 'pipeline.joblib').write_bytes(b'alterado')
            with patch('joblib.load', side_effect=AssertionError('No cargar alterado')):
                with self.assertRaises(ValueError):
                    predecir.load_model(folder)

    def test_no_fit_in_inference_and_import_help_safe(self):
        tree = ast.parse((ROOT / 'predecir.py').read_text(encoding='utf-8'))
        forbidden = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr in ('fit', 'fit_transform')]
        self.assertFalse(forbidden)
        with patch.object(predecir, 'load_model', side_effect=AssertionError('No modelo')):
            with self.assertRaises(SystemExit) as exc:
                predecir.main(['--help'])
            self.assertEqual(exc.exception.code, 0)
        with patch.object(persist, 'reproduce_a', side_effect=AssertionError('No entrenar')):
            persist.main([])
            with self.assertRaises(SystemExit):
                persist.main(['--entrenar-a'])
        spec = importlib.util.spec_from_file_location('inference_import_only', ROOT / 'predecir.py')
        with patch.object(pd, 'read_csv', side_effect=AssertionError('No datos')):
            spec.loader.exec_module(importlib.util.module_from_spec(spec))


class TemporalIntegrationTest(unittest.TestCase):
    def test_aerometro_windows_utc06(self):
        controls = TemporalControls()
        self.assertEqual(controls.aerometro_utc_window(),
                         (utc_time('2026-08-02T06:00:00Z'), utc_time('2026-08-30T06:00:00Z')))
        self.assertEqual(controls.aerometro_utc_window(7)[0], utc_time('2026-08-23T06:00:00Z'))
        for system in ('Transmetro', 'Transurbano', 'MetroRiel'):
            self.assertEqual(adapter.source_event_window(system, controls)['bounds'], controls.window())
            self.assertIsNone(adapter.source_event_window(system, controls)['bounds'][0].tzinfo)

    def test_event_borders_and_availability_are_independent(self):
        zero = TemporalControls()
        six = TemporalControls(availability_utc='2026-08-30T06:00:00Z')
        for controls in (zero, six):
            self.assertFalse(adapter.event_is_visible('Aerometro', '2026-08-02T05:59:59Z', '2026-08-02T00:00:00Z', controls))
            self.assertTrue(adapter.event_is_visible('Aerometro', '2026-08-02T06:00:00Z', '2026-08-02T00:00:00Z', controls))
            self.assertFalse(adapter.event_is_visible('Aerometro', '2026-08-30T06:00:00Z', '2026-08-29T00:00:00Z', controls))
        self.assertTrue(adapter.event_is_visible('Aerometro', '2026-08-30T05:59:59Z', '2026-08-29T23:59:59Z', zero))
        self.assertFalse(adapter.event_is_visible('Aerometro', '2026-08-30T05:59:59Z', '2026-08-30T00:00:00Z', zero))
        self.assertTrue(adapter.event_is_visible('Aerometro', '2026-08-30T05:59:59Z', '2026-08-30T00:00:00Z', six))
        self.assertFalse(adapter.event_is_visible('Aerometro', '2026-08-30T05:59:59Z', '2026-08-30T06:00:00Z', six))

    def test_seven_day_border_aerometro(self):
        events, ids, cdc = inputs()
        for row in ids:
            row['sistema'] = 'Aerometro'
        events = [dict(events[0], sistema='Aerometro', evento_id=str(i),
                       fecha_feature=normalize_source_time('Aerometro', moment).isoformat())
                  for i, moment in enumerate(['2026-08-23T05:59:59Z', '2026-08-23T06:00:00Z'])]
        frame = fc.build_features(events, ids, cdc)
        self.assertEqual(frame.iloc[0].eventos_ultimos_7_dias, 1)
        self.assertEqual(frame.iloc[0].eventos_ultimos_28_dias, 2)

    def test_transmetro_requires_session_evidence_not_universal_utc(self):
        with self.assertRaises(ValueError):
            normalize_source_time('Transmetro', '2026-08-29T22:00:00')
        self.assertEqual(normalize_source_time('Transmetro', '2026-08-29T22:00:00',
                                              session_zone='UTC', reference='fixture sesión UTC'),
                         datetime(2026, 8, 29, 22))
        self.assertEqual(normalize_source_time('Transmetro', '2026-08-29T22:00:00',
                                              session_zone='America/Guatemala', reference='fixture sesión local'),
                         datetime(2026, 8, 30, 4))
        self.assertEqual(normalize_source_time('MetroRiel', '2026-08-29T22:00:00'), datetime(2026, 8, 29, 22))

    def test_naive_cdc_cannot_be_assumed_utc(self):
        with self.assertRaises(ValueError):
            normalize_cdc_commit('2026-08-29T23:00:00')
        with self.assertRaises(ValueError):
            normalize_cdc_commit('2026-08-29T23:00:00', source_zone='UTC')
        source = dict(commit_ts='2026-08-29T23:00:00', op='delete', seq='10',
                      ingestion_timestamp='2026-11-01T00:00:00Z', tarjeta='NO_PUBLICAR')
        row = adapter.normalize_source_cdc(source, source_zone='America/Guatemala', reference='fixture')
        self.assertEqual(utc_time(row['commit_utc']), utc_time('2026-08-30T05:00:00Z'))
        self.assertEqual(row['op'], 'DELETE')
        self.assertNotIn('tarjeta', row)
        self.assertNotIn('disponible_utc', row)

    def test_cdc_effective_and_available_cutoffs_separate(self):
        events, ids, cdc = inputs()
        cdc = [dict(tarjeta_id=card(1), op='DELETE', commit_utc='2026-08-30T01:00:00Z',
                    disponible_utc='2026-08-30T02:00:00Z', seq='9')]
        # Availability UTC06 alone does NOT move the CDC effective boundary.
        self.assertFalse(fc.build_features(events, ids, cdc, controls=TemporalControls(
            availability_utc='2026-08-30T06:00:00Z')).empty)
        both = TemporalControls(availability_utc='2026-08-30T06:00:00Z', cdc_effective_utc='2026-08-30T06:00:00Z')
        self.assertTrue(fc.build_features(events, ids, cdc, controls=both).empty)
        cdc[0]['disponible_utc'] = '2026-08-30T06:00:00Z'
        self.assertFalse(fc.build_features(events, ids, cdc, controls=both).empty)

    def test_late_identity_updates_new_cards_and_duplicates(self):
        events, ids, cdc = inputs()
        before = fc.build_features(events, ids, cdc)
        ids.append(dict(ids[0], unidad_id=unit(9), seq='9', disponible_utc='2026-09-02T00:00:00Z'))
        ids.append(dict(ids[0], tarjeta_id=card(9), vigente_desde='2026-08-30T00:00:00'))
        events.append(dict(events[0], disponible_utc='2026-09-01T00:00:00Z', gasto_gtq='99999'))
        pd.testing.assert_frame_equal(before, fc.build_features(events, ids, cdc))

    def test_duplicate_payload_with_different_ingestion_not_double_counted(self):
        events, ids, cdc = inputs()
        before = fc.build_features(events, ids, cdc)
        events.append(dict(events[0], disponible_utc='2026-08-29T01:00:00Z'))
        ids.append(dict(ids[0], disponible_utc='2026-08-01T00:00:00Z'))
        pd.testing.assert_frame_equal(before, fc.build_features(events, ids, cdc))
        pd.testing.assert_frame_equal(before, fc.build_features(list(reversed(events)), list(reversed(ids)), cdc))

    def test_event_ids_are_namespaced_by_source(self):
        events, ids, cdc = inputs()
        ids.append(dict(ids[0], tarjeta_id=card(2), sistema='Transurbano'))
        events.append(dict(events[0], tarjeta_id=card(2), sistema='Transurbano'))
        self.assertEqual(fc.build_features(events, ids, cdc).iloc[0].eventos_ultimos_28_dias, 4)
        events.append(dict(events[0], gasto_gtq='900'))
        with self.assertRaises(ValueError):
            fc.build_features(events, ids, cdc)

    def test_cdc_seq_ties_card_eligibility_and_stable_sort(self):
        events, ids, cdc = inputs()
        cdc = [dict(tarjeta_id=card(1), op=op, commit_utc='2026-08-29T00:00:00Z',
                    disponible_utc='2026-08-29T00:00:00Z', seq=str(seq)) for op, seq in [('DELETE', 2), ('UPDATE', 1)]]
        self.assertTrue(fc.build_features(events, ids, list(reversed(cdc))).empty)
        ids.append(dict(ids[0], tarjeta_id=card(2), sistema='Transurbano'))
        frame = fc.build_features(events, ids, cdc)
        self.assertEqual(frame.iloc[0].tarjetas, card(2))
        self.assertEqual(frame.iloc[0].eventos_ultimos_28_dias, 3)  # Historia no borrada por DELETE actual.

    def test_lexicographic_tie_and_decimal_rounding(self):
        events, ids, cdc = inputs()
        ids.append(dict(ids[0], tarjeta_id=card(2), sistema='Transurbano'))
        events = [dict(events[0], zona='Z10', gasto_gtq='1.005'),
                  dict(events[1], tarjeta_id=card(2), sistema='Transurbano', zona='Z2', gasto_gtq='1.005')]
        frame = fc.build_features(events, ids, cdc)
        self.assertEqual(frame.iloc[0].modo_mas_usado, 'Transmetro')
        self.assertEqual(frame.iloc[0].zona_origen_mas_frecuente, 'Z10')
        self.assertEqual(frame.iloc[0].gasto_promedio_evento_gtq, 1.01)
        pd.testing.assert_frame_equal(frame, fc.build_features(list(reversed(events)), ids, cdc))

    def test_real_adapter_blocked_even_with_declarative_references(self):
        missing = adapter.integration_blockers({})
        self.assertIn('historia_identidad', missing)
        self.assertIn('claves_eventos_transurbano', missing)
        with self.assertRaises(adapter.IntegrationBlocked):
            adapter.require_real_ready({'tipo_disponibilidad': 'SNAPSHOT_FIJO'})
        evidence = {key: 'referencia fixture' for key in missing if ' ' not in key}
        evidence['tipo_disponibilidad'] = 'HISTORICA_ACREDITADA'
        with self.assertRaisesRegex(adapter.IntegrationBlocked, 'no implementado'):
            adapter.require_real_ready(evidence)

    def test_temporal_control_validation(self):
        with self.assertRaises(ValueError):
            TemporalControls(availability_utc='2026-08-30T03:00:00Z')
        with self.assertRaises(ValueError):
            fc.build_features(*inputs(), controls=TemporalControls(date='2026-08-29'))
        with self.assertRaises(ValueError):
            TemporalControls().window(30)

    def test_v2_explicit_controls_and_v1_cannot_change_silently(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            headers = [list(inputs()[0][0]), list(inputs()[1][0]),
                       ['tarjeta_id', 'op', 'commit_utc', 'disponible_utc', 'seq']]
            for name, header, rows in zip(['eventos.csv', 'identidades.csv', 'cdc.csv'], headers, inputs()):
                with (folder / name).open('w', newline='', encoding='utf-8') as handle:
                    writer = csv.DictWriter(handle, fieldnames=header); writer.writeheader(); writer.writerows(rows)
            metadata = dict(contrato='INFERENCIA_C_NORMALIZADA_V2', fecha_corte='2026-08-30',
                            datos_sinteticos=True, ids_autorizados=True, reloj_features='LEGADO_1_4_SIN_ZONA',
                            corte_disponibilidad_utc='2026-08-30T06:00:00Z',
                            corte_efectivo_cdc_utc='2026-08-30T00:00:00Z',
                            referencia_politica_temporal='Decisión sintética para probar dos límites distintos')
            path = folder / 'contrato_c.json'
            path.write_text(json.dumps(metadata), encoding='utf-8')
            *tables, controls = fc.read_inputs(folder, '2026-08-30', with_controls=True)
            self.assertEqual(controls.availability_utc, '2026-08-30T06:00:00Z')
            self.assertEqual(controls.cdc_effective_utc, '2026-08-30T00:00:00Z')
            self.assertEqual(len(tables), 3)
            with self.assertRaises(ValueError):
                fc.read_inputs(folder, '2026-08-30')
            metadata['contrato'] = 'INFERENCIA_C_NORMALIZADA_V1'
            path.write_text(json.dumps(metadata), encoding='utf-8')
            with self.assertRaises(ValueError):
                fc.read_inputs(folder, '2026-08-30', with_controls=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
