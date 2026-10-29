from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tandem.db import connect,dumps,digest
from tandem.event_decode import decode
from tandem.timeline_data import load_timeline,timeline_bounds,wall_seconds,wall_time

DEVICE='11111111-1111-4111-8111-111111111111'
START='2026-10-29T00:00:00';END='2026-10-30T00:00:00'

class TimelineDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.c=connect(self.path);self.seq=0
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def api(self,code,time,props,serial='PUMP1',identity=None):
        self.seq+=1
        raw={'eventCode':code,'sequenceGroup':1,'sequenceNumber':self.seq,'deviceAssignmentId':DEVICE,
             'pumpDateTime':time,'eventProperties':props}
        d=decode(raw);body=dumps(raw)
        with self.c:
            return self.c.execute('''INSERT INTO api_events(device_id,pump_serial,identity_key,identity_method,
                event_code,event_name,kind,local_timestamp,local_date,clock_status,unit,value,values_json,decode_status,
                raw_json,sha256,decoder_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (DEVICE,serial,identity or str(self.seq),'sequence',code,d['values'].get('event_name'),d['kind'],time,time[:10],
                 'device_local_unresolved',d['unit'],d['value'],dumps(d['values']),d['decode_status'],body,digest(body.encode()),'1.1')).lastrowid
    def cgm(self,sample='2026-10-29T01:00:00',log='2026-10-29T01:00:03',value=110,serial='PUMP1',identity=None):
        seconds=int((datetime.fromisoformat(sample)-datetime(2008,1,1)).total_seconds())
        return self.api(399,log,{'egvTimeStamp':seconds,'currentGlucoseDisplayValue':value,'glucoseValueStatus':0},serial,identity)
    def csv(self,kind,time,value,serial='PUMP1'):
        with self.c:
            rid=self.c.execute('INSERT INTO records(fingerprint,occurrence,kind,pump_serial,local_timestamp,local_date,values_json) VALUES(?,?,?,?,?,?,?)',
              (str(self.seq)+kind+time,0,kind,serial,time,time[:10],'{}')).lastrowid
            if kind in ('MCG','GLUCOSA'):
                self.c.execute('INSERT INTO glucose_readings VALUES(?,?,?,?,?)',(rid,'sensor' if kind=='MCG' else 'pump_entry',value,'',''))
            else:
                self.c.execute('INSERT INTO boluses(record_id,delivered_units,carbohydrate_grams) VALUES(?,?,?)',(rid,value,40))
        return rid
    def load(self,**kw):return load_timeline(self.path,START,END,**kw)
    def test_wall_time_does_not_apply_timezone_or_dst(self):
        a='2026-10-25T02:30:00';self.assertEqual(wall_time(wall_seconds(a)),a)
        self.assertEqual(wall_seconds('2026-10-25T03:30:00')-wall_seconds(a),3600)
        with self.assertRaises(ValueError):wall_seconds(a+'Z')
    def test_window_limits_and_missing_bounds(self):
        self.assertEqual(timeline_bounds(self.path)['devices'],[])
        self.assertIsNone(self.load()['pump_serial'])
        for end in (START,'2026-11-06T00:00:00'):
            with self.assertRaises(ValueError):load_timeline(self.path,START,end)
    def test_measurement_time_and_csv_preference(self):
        aid=self.cgm();rid=self.csv('MCG','2026-10-29T01:00:00',110)
        rows=self.load()['glucose'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['source'],'api_measurement');self.assertEqual(rows[0]['id'],aid)
        self.assertEqual(rows[0]['time'],'2026-10-29T01:00:00');self.assertEqual(rows[0]['details']['log_time'],'2026-10-29T01:00:03')
    def test_late_backfill_included_by_sample_time_not_log_date(self):
        self.cgm(log='2026-11-05T01:00:03')
        self.assertEqual(len(self.load()['glucose']),1)
    def test_csv_fallback_and_other_pump_isolation(self):
        self.cgm();self.cgm(value=250,serial='PUMP2');self.csv('MCG','2026-10-29T02:00:00',120)
        r=self.load(pump_serial='PUMP1');self.assertEqual(len(r['glucose']),2)
        self.assertEqual({p['value'] for p in r['glucose']},{110,120})
        self.assertIn('PUMP2',r['devices'])
    def test_half_open_boundaries(self):
        self.cgm(sample=START,log=START);self.cgm(sample=END,log=END)
        self.assertEqual(len(self.load()['glucose']),1)
    def test_bolus_phases_and_csv_are_not_separate_deliveries(self):
        self.cgm();self.api(64,'2026-10-29T01:59:45',{'bolusId':10,'carbAmount':40,'carbRatio':10000,'iob':1,'bg':110})
        self.api(280,'2026-10-29T02:00:00',{'bolusId':10,'bolusDeliveryStatus':1,'requestedNow':3000,'deliveredTotal':0})
        self.api(280,'2026-10-29T02:01:15',{'bolusId':10,'bolusDeliveryStatus':0,'deliveredTotal':3000})
        self.api(20,'2026-10-29T02:01:15',{'bolusId':10,'insulinDelivered':3,'insulinRequested':3,'iob':4})
        rid=self.csv('Bolo','2026-10-29T02:00:00',3)
        r=self.load();self.assertEqual(len(r['boluses']),1);self.assertEqual(len(r['carbs']),1)
        self.assertEqual(r['boluses'][0]['time'],'2026-10-29T02:00:00')
        self.assertEqual(r['boluses'][0]['details']['completed_at'],'2026-10-29T02:01:15')
        self.assertEqual(r['boluses'][0]['details']['csv_record_id'],rid)
        self.assertEqual(r['carbs'][0]['time'],'2026-10-29T01:59:45')
    def test_started_bolus_is_not_zero_delivery(self):
        self.cgm();self.api(280,'2026-10-29T02:00:00',{'bolusId':10,'bolusDeliveryStatus':1,'deliveredTotal':0})
        self.assertEqual(self.load()['boluses'],[])
    def test_basal_is_commanded_rate_not_csv_dose(self):
        self.cgm();self.api(279,'2026-10-29T02:00:00',{'commandedRate':750,'profileBasalRate':600})
        r=self.load()['basal'][0];self.assertEqual(r['value'],0.75);self.assertEqual(r['unit'],'U/h')
        self.assertEqual(r['details']['profile_rate'],0.6)
    def test_clock_changes_and_modes_keep_raw_properties(self):
        self.cgm();self.api(229,'2026-10-29T02:00:00',{'previousUserMode':0,'currentUserMode':1})
        self.api(13,'2026-10-29T03:00:00',{'timePrior':100,'timeAfter':200})
        r=self.load();self.assertEqual(r['events'][0]['details']['kind'],'mode_change')
        self.assertEqual(r['clock_changes'][0]['details']['properties']['timePrior'],100)
    def test_setup_records_do_not_expand_clinical_bounds(self):
        self.cgm();self.api(13,'2025-01-01T00:00:00',{})
        r=timeline_bounds(self.path);self.assertEqual(r['first'],'2026-10-29T01:00:00')
    def test_query_budget_is_visible_and_data_are_not_mutated(self):
        self.cgm();self.cgm(sample='2026-10-29T01:05:00',log='2026-10-29T01:05:03')
        before=self.c.execute('SELECT count(*) FROM api_events').fetchone()[0]
        with patch('tandem.timeline_data.MAX_SOURCE_ROWS',1):r=self.load()
        self.assertTrue(r['truncated']);self.assertEqual(r['source_rows_loaded'],1);self.assertTrue(r['warnings'])
        self.assertEqual(self.c.execute('SELECT count(*) FROM api_events').fetchone()[0],before)
    def test_revision_variants_not_silently_merged(self):
        self.cgm(identity='same');self.cgm(value=120,identity='same')
        rows=self.load()['glucose'];self.assertEqual(len(rows),2)
        self.assertEqual(len(rows[0]['details']['revision_ids']),2)
    def test_global_revision_outside_window_is_flagged_without_loading_it(self):
        self.cgm(identity='same')
        outside=self.cgm(sample='2026-11-05T01:00:00',log='2026-11-05T01:00:03',value=120,identity='same')
        result=self.load();rows=result['glucose'];self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['details']['revision_count'],2)
        self.assertNotIn(outside,rows[0]['details']['revision_ids'])
        self.assertEqual(result['source_rows_loaded'],1)
    def test_bolus_csv_conflict_is_preserved_without_duplicate_dose(self):
        self.cgm()
        self.api(280,'2026-10-29T02:00:00',{'bolusId':10,'bolusDeliveryStatus':1,'deliveredTotal':0})
        self.api(280,'2026-10-29T02:01:15',{'bolusId':10,'bolusDeliveryStatus':0,'deliveredTotal':3000})
        self.csv('Bolo','2026-10-29T02:00:00',4)
        result=self.load();self.assertEqual(len(result['boluses']),1)
        self.assertEqual(result['boluses'][0]['details']['source_conflict'],{'api_delivered_units':3,'csv_delivered_units':4})
        self.assertTrue(result['warnings'])

if __name__=='__main__':unittest.main()
