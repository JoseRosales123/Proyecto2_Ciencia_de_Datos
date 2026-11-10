"""CDC sintético: solo stdlib, fuentes de código y SQLite en memoria.

No importa exportadores, psycopg ni .env; no abre datasets ni usa PostgreSQL.
SQLite ejecuta la disponibilidad real; DISTINCT ON se traduce a ROW_NUMBER
exclusivamente en el arnés. No sustituye una prueba de integración PostgreSQL.
Ejecutar: python tests/modelado/test_cdc_disponibilidad_b.py -v
"""
import ast
from pathlib import Path
import sqlite3
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXPORTER = ROOT / 'scripts/modelado/exportar_dataset_corte_b.py'
LABELER = ROOT / 'scripts/etiquetado/calcular_etiquetas.py'
CUTOFF = '2026-07-31 00:00:00'
BEFORE = '2026-07-30 23:59:59'
AFTER = '2026-07-31 00:00:01'


def constant(path, name):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f'Constante no encontrada: {name}')


class BoolOr:
    def __init__(self):
        self.value = False

    def step(self, value):
        self.value = self.value or bool(value)

    def finalize(self):
        return int(self.value)


class DisponibilidadCDC(unittest.TestCase):
    def availability(self, identities, events, *, original=False):
        # Todos los registros son fixtures definidos en este archivo.
        with sqlite3.connect(':memory:') as connection:
            connection.execute("ATTACH DATABASE ':memory:' AS staging")
            connection.execute("ATTACH DATABASE ':memory:' AS silver")
            connection.create_aggregate('BOOL_OR', 1, BoolOr)
            connection.execute('CREATE TABLE staging.cdc_padron_usuarios '
                               '(tarjeta TEXT, op TEXT, commit_ts TEXT, seq INTEGER)')
            connection.execute('CREATE TABLE silver.silver_identidad_usuarios_seudonimizada '
                               '(usuario_seudonimo TEXT, sistema TEXT, llave_original TEXT)')
            connection.executemany('INSERT INTO staging.cdc_padron_usuarios VALUES (?, ?, ?, ?)', events)
            connection.executemany('INSERT INTO silver.silver_identidad_usuarios_seudonimizada '
                                   'VALUES (?, ?, ?)', identities)
            # Traducción del DISTINCT ON PostgreSQL de A: mismo filtro y orden.
            # Su contrato textual se comprueba en test_historial_conservado.
            connection.execute('''
                CREATE TEMP TABLE ultimas_cdc_12 AS
                SELECT tarjeta, op FROM (
                    SELECT tarjeta, op, ROW_NUMBER() OVER (
                        PARTITION BY tarjeta ORDER BY commit_ts DESC, seq DESC
                    ) AS posicion
                    FROM staging.cdc_padron_usuarios
                    WHERE tarjeta IS NOT NULL AND commit_ts < ?
                ) WHERE posicion = 1
            ''', (CUTOFF,))
            sql = constant(LABELER, 'SQL_DISPONIBILIDAD') if original else constant(
                EXPORTER, 'SQL_DISPONIBILIDAD_B')
            connection.executescript(sql)
            connection.executescript(constant(LABELER, 'SQL_DISPONIBILIDAD_PERSONA'))
            return dict(connection.execute('SELECT usuario_seudonimo, habilitada '
                                           'FROM disponibilidad_persona_12'))

    def test_unica_diferencia_sql(self):
        original = constant(LABELER, 'SQL_DISPONIBILIDAD')
        fragment = "WHEN c.op = 'DELETE' THEN FALSE"
        self.assertEqual(original.count(fragment), 1)
        self.assertEqual(constant(EXPORTER, 'SQL_DISPONIBILIDAD_B'), original.replace(
            fragment, "WHEN UPPER(c.op) = 'DELETE' THEN FALSE"))

    def test_consulta_local_usada_sin_importar_la_original(self):
        tree = ast.parse(EXPORTER.read_text(encoding='utf-8-sig'))
        imports = [alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                   for alias in node.names]
        self.assertNotIn('SQL_DISPONIBILIDAD', imports)
        self.assertIn('SQL_ULTIMAS_OPERACIONES', imports)
        self.assertIn('SQL_DISPONIBILIDAD_PERSONA', imports)
        self.assertIn('SQL_ETIQUETAS', imports)
        arguments = [node.args[0].id for node in ast.walk(tree)
                     if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                     and node.func.attr == 'execute' and node.args
                     and isinstance(node.args[0], ast.Name)]
        self.assertEqual(arguments.count('SQL_DISPONIBILIDAD_B'), 1)
        self.assertNotIn('SQL_DISPONIBILIDAD', arguments)

    def test_historial_conservado(self):
        self.assertEqual(' '.join(constant(LABELER, 'SQL_ULTIMAS_OPERACIONES').split()),
                         'CREATE TEMP TABLE ultimas_cdc_12 AS SELECT DISTINCT ON (tarjeta) '
                         'tarjeta, op FROM staging.cdc_padron_usuarios '
                         'WHERE tarjeta IS NOT NULL AND commit_ts < %s '
                         'ORDER BY tarjeta, commit_ts DESC, seq DESC')

    def test_capitalizaciones_y_operaciones_activas(self):
        for op, expected in [('DELETE', 0), ('delete', 0), ('Delete', 0),
                             ('INSERT', 1), ('UPDATE', 1)]:
            with self.subTest(op=op):
                self.assertEqual(self.availability([('p', 'Transmetro', 't')],
                                                   [('t', op, BEFORE, 1)]), {'p': expected})

    def test_impacto_frente_a_regla_original(self):
        for op in ('delete', 'Delete'):
            with self.subTest(op=op):
                identities = [('p', 'Transmetro', 't')]
                events = [('t', op, BEFORE, 1)]
                self.assertEqual(self.availability(identities, events, original=True), {'p': 1})
                self.assertEqual(self.availability(identities, events), {'p': 0})

    def test_historial_ausente(self):
        self.assertEqual(self.availability([('p', 'Transmetro', 't')], []), {'p': 1})

    def test_otro_operador_conserva_persona(self):
        for operator in ('Transurbano', 'MetroRiel', 'Aerometro'):
            with self.subTest(operator=operator):
                self.assertEqual(self.availability(
                    [('p', 'Transmetro', 't'), ('p', operator, 'otra')],
                    [('t', 'delete', BEFORE, 1), ('otra', 'DELETE', BEFORE, 2)]), {'p': 1})

    def test_varias_tarjetas_transmetro(self):
        identities = [('p', 'Transmetro', 't1'), ('p', 'Transmetro', 't2')]
        events = [('t1', 'delete', BEFORE, 1), ('t2', 'Delete', BEFORE, 2)]
        self.assertEqual(self.availability(identities, events), {'p': 0})
        events.append(('t2', 'UPDATE', BEFORE, 3))
        self.assertEqual(self.availability(identities, events), {'p': 1})

    def test_frontera_excluye_corte_y_futuro(self):
        identities = [('p', 'Transmetro', 't')]
        self.assertEqual(self.availability(identities, [
            ('t', 'INSERT', BEFORE, 1), ('t', 'DELETE', CUTOFF, 2),
            ('t', 'DELETE', AFTER, 3)]), {'p': 1})
        self.assertEqual(self.availability(identities, [
            ('t', 'Delete', BEFORE, 1), ('t', 'UPDATE', CUTOFF, 2)]), {'p': 0})
        self.assertEqual(self.availability(identities, [('t', 'DELETE', CUTOFF, 1)]), {'p': 1})

    def test_prioridad_fecha_y_desempate_seq(self):
        identities = [('p', 'Transmetro', 't')]
        self.assertEqual(self.availability(identities, [
            ('t', 'INSERT', '2026-07-29 12:00:00', 100),
            ('t', 'Delete', BEFORE, 1)]), {'p': 0})
        self.assertEqual(self.availability(identities, [
            ('t', 'INSERT', BEFORE, 1), ('t', 'delete', BEFORE, 2)]), {'p': 0})
        self.assertEqual(self.availability(identities, [
            ('t', 'DELETE', BEFORE, 1), ('t', 'UPDATE', BEFORE, 2)]), {'p': 1})


if __name__ == '__main__':
    unittest.main()
