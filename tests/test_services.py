import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import ExitStack, closing, contextmanager
from unittest.mock import MagicMock, patch

from tandem.services import load_dashboard, import_manifest


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / 'test.sqlite'

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self):
        with closing(sqlite3.connect(self.database)) as conn:
            conn.executescript('''
                CREATE TABLE records(id INTEGER PRIMARY KEY,local_timestamp TEXT);
                INSERT INTO records VALUES(1,'2026-03-16T10:54:47');
                INSERT INTO records VALUES(2,'2026-10-27T16:04:06');
                CREATE TABLE pdf_pages(id INTEGER PRIMARY KEY);
                INSERT INTO pdf_pages VALUES(1);
                CREATE TABLE api_events(id INTEGER PRIMARY KEY,local_timestamp TEXT,decode_status TEXT);
                INSERT INTO api_events VALUES(1,'2026-03-16T10:54:50','decoded');
                INSERT INTO api_events VALUES(2,'2026-10-29T08:05:36','unknown');
                INSERT INTO api_events VALUES(3,'2026-10-29T08:00:00','classified');
                INSERT INTO api_events VALUES(4,'2026-10-29T08:00:01','partial');
                CREATE VIEW v_api_events AS SELECT * FROM api_events;
                CREATE TABLE api_payloads(id INTEGER PRIMARY KEY);
                INSERT INTO api_payloads VALUES(1);
                CREATE TABLE source_links(id INTEGER PRIMARY KEY);
                CREATE TABLE api_runs(id INTEGER PRIMARY KEY,started_at TEXT,status TEXT,error_code TEXT);
                CREATE TABLE review(id INTEGER PRIMARY KEY);
                INSERT INTO review VALUES(1);
                INSERT INTO review VALUES(2);
                CREATE VIEW v_pending_review AS SELECT * FROM review;
            ''')
            conn.executemany('INSERT INTO api_runs VALUES(?,?,?,?)',
                             [(i, '2026-10-29T08:00:00Z', 'complete', None) for i in range(1, 106)])
            conn.commit()

    def test_missing_database_does_not_create_file_or_parents(self):
        missing = self.root / 'absent' / 'missing.sqlite'
        result = load_dashboard(missing)
        self.assertEqual(result['status'], 'missing')
        self.assertEqual(result['datasets'], [])
        self.assertIsNone(result['last_run'])
        self.assertFalse(missing.parent.exists())

    def test_dashboard_snapshot_ranges_counts_run_limit_and_read_only(self):
        self.prepare()
        before = hashlib.sha256(self.database.read_bytes()).hexdigest()
        result = load_dashboard(self.database)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['counts'], {'records': 2, 'pdf_pages': 1, 'api_events': 4,
                                            'api_payloads': 1, 'source_links': 0})
        self.assertEqual(result['csv_range'], {'first': '2026-03-16T10:54:47', 'last': '2026-10-27T16:04:06'})
        self.assertEqual(result['api_range']['last'], '2026-10-29T08:05:36')
        self.assertEqual(result['unknown_count'], 2)
        self.assertEqual(result['pending_review'], 2)
        self.assertEqual(len(result['runs']), 100)
        self.assertEqual(result['last_run']['id'], 105)
        self.assertEqual(result['runs'][-1]['id'], 6)
        self.assertIn('api_events', result['datasets'])
        self.assertEqual(hashlib.sha256(self.database.read_bytes()).hexdigest(), before)
        # Successful exclusive access proves the reader connection was closed.
        with closing(sqlite3.connect(self.database, timeout=0)) as conn:
            conn.execute('BEGIN EXCLUSIVE')
            conn.rollback()

    def test_empty_existing_database_is_not_migrated(self):
        sqlite3.connect(self.database).close()
        before = self.database.read_bytes()
        result = load_dashboard(self.database)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['counts']['records'], 0)
        self.assertEqual(result['datasets'], [])
        self.assertEqual(self.database.read_bytes(), before)


class ImportServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.database = self.root / 'test.sqlite'

    def tearDown(self):
        self.temp.cleanup()

    def run_pipeline(self, report):
        order = []
        conn = MagicMock()
        conn.close.side_effect = lambda: order.append('close')

        @contextmanager
        def lock(database):
            order.append('lock')
            try:
                yield
            finally:
                order.append('unlock')

        def result(name, value):
            def execute(*args, **kwargs):
                order.append(name)
                return value
            return execute

        with ExitStack() as stack:
            replacements = {
                'tandem.collector.writer_lock': lock,
                'tandem.db.connect': result('connect', conn),
                'tandem.sync.accept_downloads': result('sync', {'windows': 1, 'new_raw_rows': 2}),
                'tandem.pdf.run_ocr': result('ocr', {'errors': []}),
                'tandem.visual.expand': result('visual', {'errors': []}),
                'tandem.collector.reconcile': result('reconcile', {}),
                'tandem.cli.status': result('audit', report),
                'tandem.collector.audit_api': result('api_audit', {}),
                'tandem.db.backup': result('backup', 'final.sqlite'),
            }
            for target, replacement in replacements.items():
                stack.enter_context(patch(target, replacement))
            try:
                output = import_manifest(self.database, self.root / 'manifest.json')
            except RuntimeError:
                return order, None
        return order, output

    def test_import_pipeline_order_audits_then_backup_and_closes(self):
        order, output = self.run_pipeline({'integrity_check': 'ok'})
        self.assertEqual(order, ['lock', 'connect', 'sync', 'ocr', 'visual', 'reconcile',
                                 'audit', 'api_audit', 'backup', 'close', 'unlock'])
        self.assertEqual(output['new_raw_rows'], 2)
        self.assertEqual(output['status'], 'complete')
        self.assertEqual(json.loads(Path(output['audit']).read_text(encoding='utf-8'))['integrity_check'], 'ok')

    def test_failed_audit_is_saved_but_final_backup_is_not_created(self):
        order, output = self.run_pipeline({'integrity_check': 'ok', 'artifact_hash_errors': [1]})
        self.assertIsNone(output)
        self.assertNotIn('backup', order)
        self.assertEqual(order[-2:], ['close', 'unlock'])
        files = list((self.root / 'auditorias').glob('app_*.json'))
        self.assertEqual(len(files), 1)
        self.assertEqual(json.loads(files[0].read_text(encoding='utf-8'))['artifact_hash_errors'], [1])


if __name__ == '__main__':
    unittest.main()
