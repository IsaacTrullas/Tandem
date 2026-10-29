import csv
import io
import json
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

from tandem.db import connect, digest, store_artifact
from tandem.ingest import KINDS, ingest_csv, import_source
from tandem.pdf import parse_ocr_page, profile_extract
from tandem.sync import accept_downloads, label, plan
from tandem.cli import status


def csv_bytes(kind, rows):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=KINDS[kind])
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8-sig')


def row(kind='MCG', stamp='2026-10-25T02:30:00', **changes):
    result = dict.fromkeys(KINDS[kind], '')
    result['Número de serie'] = 'SYNTHETIC'
    field = 'Fecha y hora de finalización' if kind == 'Bolo' else 'Fecha del evento' if kind == 'Suministro basal por hora' else 'Fecha y hora del caso'
    result[field] = stamp
    if kind == 'MCG': result['Lecturas (mg/dl)'] = '123'
    result.update(changes)
    return result


class Pipeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root/'test.sqlite'
        self.c = connect(self.db)

    def tearDown(self):
        self.c.close()
        self.temp.cleanup()

    def ingest(self, kind, rows, filename='test.csv'):
        with self.c:
            return ingest_csv(self.c, csv_bytes(kind, rows), filename, filename, None)

    def count(self, table):
        return self.c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]

    def test_idempotence_and_overlap_provenance(self):
        a = row()
        b = row(stamp='2026-10-25T02:35:00')
        self.ingest('MCG', [a])
        self.ingest('MCG', [a])
        self.ingest('MCG', [a,b], 'overlap.csv')
        self.assertEqual(self.count('records'), 2)
        self.assertEqual(self.count('raw_rows'), 3)
        self.assertEqual(self.count('record_sources'), 3)
        self.assertEqual(status(self.c,True)['raw_rows_without_record'], 0)

    def test_identical_occurrences_are_not_lost(self):
        self.ingest('MCG', [row(),row()])
        self.ingest('MCG', [row(),row(),row(stamp='2026-10-25T03:00:00')], 'overlap.csv')
        self.assertEqual(self.count('records'), 3)
        self.assertEqual(self.count('raw_rows'), 5)

    def test_opening_existing_database_does_not_write_schema(self):
        self.c.execute('BEGIN')
        self.c.execute('SELECT count(*) FROM records').fetchone()
        other=connect(self.db)
        try:
            # A concurrent read-only opening must not invalidate this read snapshot.
            self.c.execute("INSERT INTO quality_issues(issue_type,severity,details_json,created_at) VALUES('synthetic','info','{}','2026-10-28')")
            self.c.commit()
        finally:other.close()

    def test_clock_backwards_remains_device_local(self):
        self.ingest('MCG', [row(stamp='2026-10-25T02:55:00'),row(stamp='2026-10-25T02:05:00')])
        self.assertEqual(self.count('clock_observations'), 1)
        self.assertEqual([r[0] for r in self.c.execute('SELECT clock_segment FROM record_sources ORDER BY raw_row_id')],[0,1])
        self.assertEqual(self.c.execute('SELECT COUNT(*) FROM records WHERE utc_timestamp IS NULL').fetchone()[0],2)

    def test_hourly_null_zero_and_repeated_date(self):
        a = row('Suministro basal por hora','2026-10-25', **{'0':'0','1':'0.5'})
        b = dict(a, **{'1':'0.6'})
        self.ingest('Suministro basal por hora',[a,b])
        self.assertEqual(self.count('records'),2)
        self.assertEqual(self.count('basal_hourly'),48)
        self.assertEqual(self.c.execute('SELECT delivered_units FROM basal_hourly WHERE hour=0 LIMIT 1').fetchone()[0],0)
        self.assertIsNone(self.c.execute('SELECT delivered_units FROM basal_hourly WHERE hour=2 LIMIT 1').fetchone()[0])

    def test_carbs_are_not_food_name_or_meal_time(self):
        self.ingest('Bolo',[row('Bolo',**{'Cantidad de carbohidratos':'32','Insulina suministrada':'1.25'})])
        c = self.c.execute('SELECT * FROM carbohydrate_entries').fetchone()
        self.assertEqual(c['grams'],32)
        self.assertIsNone(c['food_name'])
        self.assertEqual(c['timestamp_meaning'],'bolus_completion_not_meal_time')

    def test_unknown_schema_preserved_quarantined(self):
        path=self.root/'bad.csv'; path.write_text('unknown\n123\n')
        result=import_source(self.c,path)
        self.assertEqual(len(result['failures']),1)
        artifact=self.c.execute('SELECT * FROM artifacts').fetchone()
        self.assertEqual(artifact['status'],'quarantined')
        self.assertEqual(artifact['content'],path.read_bytes())
        self.assertEqual(self.count('records'),0)

    def test_outside_window_rejected_transactionally(self):
        with self.assertRaises(ValueError),self.c:
            ingest_csv(self.c,csv_bytes('MCG',[row()]),'bad.csv','bad.csv',None,period=('2026-10-26','2026-10-26'))
        self.assertEqual(self.count('raw_rows'),0)

    def test_reused_csv_is_still_checked_against_window(self):
        self.ingest('MCG',[row()])
        with self.assertRaises(ValueError),self.c:
            ingest_csv(self.c,csv_bytes('MCG',[row()]),'same.csv','same.csv',None,period=('2026-10-26','2026-10-26'))
        self.assertEqual(self.count('records'),1)

    def test_same_file_keeps_multiple_period_receipts(self):
        with self.c:
            for start,end in [('2026-10-01','2026-10-02'),('2026-10-01','2026-10-03')]:
                store_artifact(self.c,b'same-content','fixture','application/zip','fixture',None,start,end)
        self.assertEqual(self.count('artifacts'),1)
        self.assertEqual(self.count('artifact_receipts'),2)

    def zip(self):
        path=self.root/'data.zip'
        with zipfile.ZipFile(path,'w') as z:
            for kind in KINDS:
                z.writestr(kind+'.csv',csv_bytes(kind,[row()] if kind=='MCG' else []))
        return path

    def test_sync_rolls_back_whole_pair_and_backup_opens(self):
        zipped=self.zip()
        invalid=self.root/'invalid.pdf';invalid.write_bytes(b'not a PDF')
        manifest=self.root/'manifest.json'
        manifest.write_text(json.dumps({'schema_version':1,'windows':[{'start':'2026-10-25','end':'2026-10-25','csv_zip':{'path':str(zipped)},'pdf':{'path':str(invalid)}}]}))
        with self.assertRaises(Exception):
            accept_downloads(self.c,manifest,self.root/'archive',self.root/'backups')
        self.assertEqual(self.count('records'),0)
        self.assertEqual(self.count('artifacts'),0)
        self.assertEqual(self.c.execute('SELECT status FROM sync_runs').fetchone()[0],'failed')
        with closing(sqlite3.connect(next((self.root/'backups').glob('*.sqlite')))) as backup:
            self.assertEqual(backup.execute('PRAGMA integrity_check').fetchone()[0],'ok')

    def test_successful_sync_and_repeat_are_idempotent(self):
        import pymupdf
        doc=pymupdf.open();page=doc.new_page()
        page.insert_text((50,50),'Resumen general 25 oct 2026\nCronograma diario 25 oct 2026')
        pdf=self.root/'report.pdf';doc.save(pdf);doc.close()
        manifest=self.root/'manifest.json'
        zipped=self.zip()
        manifest.write_text(json.dumps({'schema_version':1,'windows':[{'start':'2026-10-25','end':'2026-10-25','csv_zip':{'path':str(zipped),'sha256':digest(zipped.read_bytes()).upper()},'pdf':{'path':str(pdf)}}]}))
        first=accept_downloads(self.c,manifest,self.root/'archive',self.root/'backups')
        second=accept_downloads(self.c,manifest,self.root/'archive',self.root/'backups')
        self.assertEqual(first['new_raw_rows'],1)
        self.assertEqual(second['new_raw_rows'],0)
        self.assertEqual(self.count('records'),1)
        self.assertEqual(self.count('pdf_pages'),1)

    def test_plan_windows_overlap_and_orphan(self):
        with self.c:
            for mime in ['application/zip','application/pdf']:
                aid,_=store_artifact(self.c,mime.encode(),'sample',mime,'fixture',None,'2026-09-28','2026-10-27')
                self.c.execute("UPDATE artifacts SET status='imported' WHERE id=?",(aid,))
        self.assertEqual(plan(self.c,'2026-10-28')['start'],'2026-10-21')
        windows=plan(self.c,'2026-10-28','2026-08-01')['windows']
        self.assertEqual([(w['start'],w['end']) for w in windows],[('2026-08-01','2026-08-30'),('2026-08-31','2026-09-29'),('2026-09-30','2026-10-28')])
        with self.c:
            aid,_=store_artifact(self.c,b'orphan','sample','application/zip','fixture',None,'2026-09-01','2026-09-15')
            self.c.execute("UPDATE artifacts SET status='imported' WHERE id=?",(aid,))
        self.assertEqual(plan(self.c,'2026-10-28')['start'],'2026-09-01')

    def test_ocr_evidence_is_unreviewed_and_legend_is_not_event(self):
        with self.c:
            aid,_=store_artifact(self.c,b'fixture','fixture','application/pdf','fixture',None)
            pid=self.c.execute("INSERT INTO pdf_pages(artifact_id,page_number,width_points,height_points,native_text,words_json,raster_image_count) VALUES(?,1,600,800,'','[]',0)",(aid,)).lastrowid
            def line(text,y):
                return {'text':text,'words':[{'bounding_rect':{'x':10,'y':y,'width':500,'height':12}}]}
            result={'lines':[line('25 de oct de 2026',100),line('Promedio: 123 mg/dL Carbos: 32 g',100),line('Sueño Ejercicio Alarma de la bomba',300),line('Alertas de MCG: 04:15 Señal perdida',400)]}
            parse_ocr_page(self.c,pid,result,1200,1600)
        self.assertEqual(self.count('daily_panels'),1)
        self.assertEqual(self.count('therapy_events'),1)
        event=self.c.execute('SELECT * FROM therapy_events').fetchone()
        self.assertEqual(event['review_status'],'ocr_unreviewed')
        self.assertEqual(event['start_local'],'2026-10-25T04:15:00')
        self.assertEqual(json.loads(self.c.execute('SELECT facts_json FROM daily_panels').fetchone()[0])['carbohydrates']['value'],32)

    def test_profile_date_is_upload_not_report_window(self):
        with self.c:
            aid,_=store_artifact(self.c,b'x','x','application/pdf','x',None)
            pid=self.c.execute("INSERT INTO pdf_pages(artifact_id,page_number,width_points,height_points,native_text,words_json,raster_image_count) VALUES(?,1,600,800,'','[]',0)",(aid,)).lastrowid
            profile_extract(self.c,pid,'Configuración de la bomba 27 oct 2026\nConfiguración del perfil de la bomba - Ejemplo Activo en la subida\n00:00 0,25 1:100 1:20 110\n')
        self.assertEqual(self.c.execute('SELECT as_of_date FROM profiles').fetchone()[0],'2026-10-27')
        self.assertEqual(self.count('profile_segments'),1)


if __name__=='__main__': unittest.main()
