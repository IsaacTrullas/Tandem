from contextlib import closing
import json,sqlite3,tempfile,unittest
from pathlib import Path
from tandem.data_dictionary import dictionary,describe,describe_event,generated_files,schema_differences,BASE,main
from tandem.reader import Reader
from tandem.db import connect

class DictionaryTests(unittest.TestCase):
    def test_all_storage_columns_and_dataset_views_have_meanings(self):
        d=dictionary();self.assertEqual(d['coverage']['missing_semantic_entries'],[])
        self.assertEqual(d['coverage']['columns'],sum(len(o['columns']) for o in d['objects'].values()))
        self.assertFalse(d['contains_patient_rows']);self.assertEqual(d['schema_version'],7)
        self.assertTrue(all(o['meaning'] and all(c['meaning'] for c in o['columns']) for o in d['objects'].values()))
        self.assertTrue(all(s['source_object'] in d['objects'] for s in d['datasets'].values()))
    def test_api_unit_conversions_are_code_specific_and_rate_not_guessed(self):
        def field(code,name):return next(f for f in describe_event(code)['fields'] if f['name']==name)
        self.assertEqual(field(279,'commandedRate')['normalized_measures'][0]['factor'],.001)
        self.assertEqual(field(3,'commandedBasalRate')['normalized_measures'][0]['factor'],1)
        self.assertEqual(field(399,'rate')['normalized_measures'],[])
        self.assertEqual(field(399,'rate')['scale_status'],'unvalidated_do_not_rescale')
        self.assertIsNotNone(field(280,'bolusType')['bit_positions'])
        self.assertIsNotNone(field(4,'alertId')['enum'])
    def test_unsupported_code_and_invalid_dataset_are_explicit(self):
        self.assertEqual(describe_event(22)['interpretation_status'],'unresolved')
        with self.assertRaises(ValueError):describe_event(True)
        with self.assertRaises(ValueError):describe('api_events; DROP TABLE x')
    def test_csv_units_and_raw_headers_survive(self):
        d=dictionary();spec=d['csv_sources']['Bolo'];fields={f['header']:f for f in spec['fields']}
        self.assertEqual(fields['Alimento suministrado']['unit'],'U')
        self.assertEqual(fields['Cantidad de carbohidratos']['unit'],'g')
        self.assertEqual(fields['I:C']['unit'],'g/U')
        self.assertEqual(spec['source_time_header'],'Fecha y hora de finalización')
    def test_returned_contract_is_defensive_and_scoped(self):
        first=describe('api_measurements');first['semantic_rules'].clear()
        self.assertTrue(describe('api_measurements')['semantic_rules'])
        self.assertEqual(first['object']['meaning'],dictionary()['objects']['v_api_measurements']['meaning'])
        self.assertNotIn('records',first)
    def test_schema_check_detects_new_undocumented_column_without_reading_rows(self):
        with closing(sqlite3.connect(':memory:')) as c:
            c.executescript((BASE/'schema.sql').read_text(encoding='utf-8'));c.executescript((BASE/'api_schema.sql').read_text(encoding='utf-8'))
            self.assertEqual(schema_differences(c),[])
            c.execute('ALTER TABLE boluses ADD COLUMN future_meaning TEXT')
            self.assertIn('columns differ: boluses',schema_differences(c))
    def test_generated_documents_are_deterministic_and_checked(self):
        self.assertEqual(generated_files(),generated_files())
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(main(['--output',folder]),0)
            self.assertEqual(main(['--output',folder,'--check']),0)
            (Path(folder)/'CSV.md').write_text('stale',encoding='utf-8')
            with self.assertRaises(SystemExit):main(['--output',folder,'--check'])
    def test_reader_metadata_has_no_row_queries_and_export_carries_dictionary_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/'db.sqlite'
            with closing(connect(db)) as c:c.commit()
            with Reader(db) as reader:
                statements=[];reader._conn.set_trace_callback(statements.append)
                contract=reader.describe('api_measurements');reader.describe_event(280)
                self.assertEqual(statements,[])
                output=Path(folder)/'data.jsonl';reader.export_jsonl('api_measurements',output)
                metadata=json.loads(output.read_text(encoding='utf-8').splitlines()[0])
                self.assertEqual(metadata['dictionary']['fingerprint'],contract['fingerprint'])
                self.assertEqual(metadata['dictionary']['format'],contract['format'])

if __name__=='__main__':unittest.main()
