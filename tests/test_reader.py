import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tandem.reader import Reader, EXPORT_FORMAT


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / 'test.sqlite'
        with closing(sqlite3.connect(self.path)) as conn:
            conn.execute('PRAGMA journal_mode=WAL')
            conn.executescript('''
                CREATE TABLE schema_version(version INTEGER PRIMARY KEY);
                INSERT INTO schema_version VALUES(6);
                CREATE TABLE data(id INTEGER PRIMARY KEY, local_timestamp TEXT, value REAL);
                CREATE VIEW v_api_events AS SELECT * FROM data;
                CREATE TABLE source_links(event_id INTEGER,source_table TEXT,source_id INTEGER,relation TEXT,details_json TEXT);
                CREATE VIEW v_source_links AS SELECT * FROM source_links;
            ''')
            conn.executemany('INSERT INTO data VALUES(?,?,?)',
                             [(i, f'2026-10-{20 + (i % 3):02d}T01:00:00', i / 10) for i in range(1, 26)])
            conn.executemany('INSERT INTO source_links VALUES(?,?,?,?,?)',
                             [(1, 'records', 1, 'candidate', '{}'), (1, 'records', 2, 'candidate', '{}')])
            conn.commit()

    def tearDown(self):
        self.temp.cleanup()

    def test_read_only_missing_file_and_allowlist(self):
        with self.assertRaises(sqlite3.OperationalError):
            Reader(self.root / 'missing.sqlite')
        self.assertFalse((self.root / 'missing.sqlite').exists())
        with Reader(self.path) as reader:
            self.assertEqual(reader.datasets(), ['api_events', 'source_links'])
            with self.assertRaises(sqlite3.OperationalError):
                reader._conn.execute('DELETE FROM data')
            with self.assertRaises(ValueError):
                reader.rows('api_events; DROP TABLE data; --')
            self.assertEqual(len(reader.rows('api_events')), 25)

    def test_dates_bounds_and_stable_paging(self):
        with Reader(self.path) as reader:
            page1 = reader.rows('api_events', limit=7)
            page2 = reader.rows('api_events', limit=7, offset=7)
            self.assertEqual([r['id'] for r in page1 + page2], list(range(1, 15)))
            selected = reader.rows('api_events', since='2026-10-21', until='2026-10-21')
            self.assertEqual(len(selected), 9)
            self.assertTrue(all(r['local_timestamp'].startswith('2026-10-21') for r in selected))
            for limit in (0, -1, 10001, True, '4'):
                with self.assertRaises(ValueError):
                    reader.rows('api_events', limit=limit)
            for offset in (-1, True, '0'):
                with self.assertRaises(ValueError):
                    reader.rows('api_events', offset=offset)
            for since, until in [('2026-10-22', '2026-10-20'), ("2026-10-20' OR 1=1--", None), ('2026-02-30', None)]:
                with self.assertRaises(ValueError):
                    reader.rows('api_events', since=since, until=until)
            with self.assertRaises(ValueError):
                reader.rows('source_links', since='2026-10-20')

    def test_export_all_pages_and_metadata_no_overwrite(self):
        output = self.root / 'events.jsonl'
        with Reader(self.path) as reader:
            result = reader.export_jsonl('api_events', output, page_size=4)
            self.assertEqual(result['records'], 25)
            lines = [json.loads(s) for s in output.read_text(encoding='utf-8').splitlines()]
            self.assertEqual(lines[0]['format'], EXPORT_FORMAT)
            self.assertEqual(lines[0]['schema_version'], 6)
            self.assertEqual(lines[0]['source_view'], 'v_api_events')
            self.assertEqual([r['data']['id'] for r in lines[1:-1]], list(range(1, 26)))
            self.assertEqual(lines[-1], {'type': 'complete', 'records': 25})
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                reader.export_jsonl('api_events', output)
            self.assertEqual(output.read_bytes(), before)
            self.assertFalse(reader._conn.in_transaction)

    def test_composite_order_and_empty_filter_export(self):
        with Reader(self.path) as reader:
            self.assertEqual([r['source_id'] for r in reader.rows('source_links')], [1, 2])
            output = self.root / 'empty.jsonl'
            result = reader.export_jsonl('api_events', output, since='2027-01-01')
            self.assertEqual(result['records'], 0)
            self.assertEqual(len(output.read_text().splitlines()), 2)

    def test_export_holds_snapshot_when_another_writer_inserts(self):
        with Reader(self.path) as reader:
            original_rows = reader.rows
            written = False
            def rows(*args, **kwargs):
                nonlocal written
                page = original_rows(*args, **kwargs)
                if not written:
                    with closing(sqlite3.connect(self.path)) as writer:
                        writer.execute("INSERT INTO data VALUES(26,'2026-10-22T02:00:00',2.6)")
                        writer.commit()
                    written = True
                return page
            reader.rows = rows
            result = reader.export_jsonl('api_events', self.root / 'snapshot.jsonl', page_size=3)
            self.assertEqual(result['records'], 25)
            self.assertEqual(len(original_rows('api_events')), 26)


if __name__ == '__main__':
    unittest.main()
