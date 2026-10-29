"""Synthetic predecessor queries; no patient data or live account access."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tandem.db import connect
from tandem.timeline_data import load_timeline
import test_timeline_data as fixtures

START='2026-10-29T00:00:00';END='2026-10-30T00:00:00'

class LastEventTests(unittest.TestCase):
    api=fixtures.TimelineDataTests.api
    cgm=fixtures.TimelineDataTests.cgm
    csv=fixtures.TimelineDataTests.csv
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.c=connect(self.path);self.seq=0
        self.cgm()
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def load(self,**kwargs):return load_timeline(self.path,START,END,**kwargs)
    def dose(self,start,end,units=1,bid=1,serial='PUMP1',identity=None):
        self.api(280,start,{'bolusId':bid,'bolusDeliveryStatus':1,'deliveredTotal':0},serial)
        return self.api(280,end,{'bolusId':bid,'bolusDeliveryStatus':0,'deliveredTotal':units*1000},serial,identity)
    def request(self,time,grams,bid=1,serial='PUMP1',identity=None):
        return self.api(64,time,{'bolusId':bid,'carbAmount':grams},serial,identity)
    def test_no_previous_does_not_invent_values(self):
        result=self.load();self.assertEqual(result['predecessors'],{'boluses':[],'carbs':[]})
        self.assertFalse(result['predecessor_truncated'])
    def test_previous_from_weeks_ago_is_separate_from_chart(self):
        self.request('2026-10-01T07:59:00',25)
        self.dose('2026-10-01T08:00:00','2026-10-01T08:02:00',2.5)
        result=self.load();previous=result['predecessors']
        self.assertEqual(previous['boluses'][0]['time'],'2026-10-01T08:00:00')
        self.assertEqual(previous['boluses'][0]['value'],2.5)
        self.assertEqual(previous['boluses'][0]['details']['completed_at'],'2026-10-01T08:02:00')
        self.assertEqual(previous['carbs'][0]['time'],'2026-10-01T07:59:00')
        self.assertEqual(result['boluses'],[]);self.assertEqual(result['carbs'],[])
        self.assertTrue(previous['boluses'][0]['details']['predecessor'])
        self.assertEqual(previous['boluses'][0]['details']['clock_status'],'device_local_unresolved')
    def test_latest_delivery_start_wins_over_later_extended_completion(self):
        self.dose('2026-10-28T14:00:00','2026-10-28T21:00:00',3,bid=1)
        self.dose('2026-10-28T20:00:00','2026-10-28T20:01:00',.5,bid=2)
        last=self.load()['predecessors']['boluses']
        self.assertEqual([p['value'] for p in last],[.5]);self.assertEqual(last[0]['time'],'2026-10-28T20:00:00')
    def test_last_carbs_do_not_require_a_completed_delivery(self):
        self.dose('2026-10-28T20:00:00','2026-10-28T20:01:00',1)
        self.request('2026-10-28T23:30:00',25,bid=2);self.request('2026-10-28T23:40:00',10,bid=3)
        previous=self.load()['predecessors']
        self.assertEqual(previous['boluses'][0]['time'],'2026-10-28T20:00:00')
        self.assertEqual(previous['carbs'][0]['value'],10)
        self.assertEqual(previous['carbs'][0]['details']['delivery_confirmation'],'not_linked')
    def test_started_bolus_alone_is_not_a_delivery(self):
        self.api(280,'2026-10-28T23:00:00',{'bolusId':1,'bolusDeliveryStatus':1,'deliveredTotal':0})
        self.assertEqual(self.load()['predecessors']['boluses'],[])
    def test_future_starts_and_future_carbs_are_excluded(self):
        self.dose('2026-10-29T02:00:00','2026-10-29T02:01:00',5)
        self.request('2026-10-29T01:59:00',35)
        self.assertEqual(self.load()['predecessors'],{'boluses':[],'carbs':[]})
    def test_exact_cutoff_belongs_to_visible_series_not_predecessor(self):
        self.request(START,25);self.dose(START,'2026-10-29T00:02:00',1)
        result=self.load();self.assertEqual(result['predecessors'],{'boluses':[],'carbs':[]})
        self.assertEqual(len(result['boluses']),1);self.assertEqual(len(result['carbs']),1)
    def test_csv_only_predecessor_preserves_zero_dose(self):
        self.csv('Bolo','2026-09-03T07:00:00',0)
        previous=self.load()['predecessors']
        self.assertEqual(previous['boluses'][0]['source'],'csv_bolus')
        self.assertEqual(previous['boluses'][0]['value'],0)
        self.assertEqual(previous['carbs'][0]['value'],40)
    def test_api_csv_delivery_conflict_has_one_dose_with_evidence(self):
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',3)
        rid=self.csv('Bolo','2026-10-20T12:00:00',4)
        result=self.load();last=result['predecessors']['boluses']
        self.assertEqual(len(last),1);self.assertEqual(last[0]['value'],3)
        self.assertEqual(last[0]['details']['csv_record_id'],rid)
        self.assertEqual(last[0]['details']['source_conflict'],{'api_delivered_units':3,'csv_delivered_units':4})
        self.assertTrue(result['warnings'])
    def test_near_csv_carbs_remain_one_api_request(self):
        self.request('2026-10-20T12:00:00',40)
        rid=self.csv('Bolo','2026-10-20T12:01:00',3)
        last=self.load()['predecessors']['carbs']
        self.assertEqual(len(last),1);self.assertEqual(last[0]['source'],'api_bolus_request')
        self.assertEqual(last[0]['details']['csv_record_id'],rid)
    def test_same_wall_time_different_doses_are_not_chosen_silently(self):
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',.5,bid=1)
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',1.5,bid=2)
        last=self.load()['predecessors']['boluses']
        self.assertEqual(len(last),2);self.assertEqual({p['value'] for p in last},{.5,1.5})
    def test_carbohydrate_revisions_keep_global_revision_metadata(self):
        self.request('2026-10-20T12:00:00',20,identity='same')
        self.request('2026-10-20T12:00:00',30,identity='same')
        last=self.load()['predecessors']['carbs']
        self.assertEqual(len(last),2);self.assertEqual({p['value'] for p in last},{20,30})
        self.assertTrue(all(p['details']['revision_count']==2 for p in last))
        self.assertTrue(all(len(p['details']['revision_ids'])==2 for p in last))
    def test_clock_change_between_old_value_and_window_is_explicit(self):
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',.05)
        self.api(13,'2026-10-25T03:00:00',{'timePrior':100,'timeAfter':200})
        last=self.load()['predecessors']['boluses'][0]
        self.assertEqual(last['time'],'2026-10-20T12:00:00')
        self.assertTrue(last['details']['clock_change_between'])
    def test_other_pump_cannot_replace_previous(self):
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',1)
        self.request('2026-10-20T11:59:00',25)
        self.cgm(serial='PUMP2')
        self.dose('2026-10-28T22:00:00','2026-10-28T22:02:00',7,serial='PUMP2')
        self.request('2026-10-28T21:59:00',75,serial='PUMP2')
        previous=self.load(pump_serial='PUMP1')['predecessors']
        self.assertEqual(previous['boluses'][0]['value'],1);self.assertEqual(previous['carbs'][0]['value'],25)
    def test_budget_never_presents_a_partial_latest_group_as_complete(self):
        self.request('2026-10-20T12:00:00',20)
        self.request('2026-10-20T12:00:00',30,bid=2)
        with patch('tandem.last_events.MAX_PREDECESSOR_ROWS',1):result=self.load()
        self.assertTrue(result['predecessor_truncated'])
        self.assertEqual(result['predecessor_source_rows_loaded'],1)
        self.assertEqual(result['predecessors'],{'boluses':[],'carbs':[]})
        self.assertTrue(any('Consulta previa limitada' in text for text in result['warnings']))
    def test_started_before_cutoff_completed_after_uses_existing_start_semantics(self):
        self.dose('2026-10-28T23:55:00','2026-10-29T00:20:00',1.5)
        result=self.load();last=result['predecessors']['boluses']
        self.assertEqual(len(last),1);self.assertEqual(last[0]['time'],'2026-10-28T23:55:00')
        self.assertEqual(last[0]['details']['completed_at'],'2026-10-29T00:20:00')
        self.assertEqual(result['boluses'],[])
    def test_future_request_does_not_absorb_previous_csv_carbs(self):
        rid=self.csv('Bolo','2026-10-28T23:59:00',1)
        self.request('2026-10-29T00:01:00',40)
        last=self.load()['predecessors']['carbs']
        self.assertEqual(len(last),1);self.assertEqual(last[0]['source'],'csv_carbohydrates')
        self.assertEqual(last[0]['id'],rid)
    def test_reads_do_not_change_source_rows_or_add_old_markers(self):
        self.request('2026-10-20T12:00:00',25)
        self.dose('2026-10-20T12:01:00','2026-10-20T12:02:00',2)
        before=self.c.execute('SELECT count(*) FROM api_events').fetchone()[0]
        result=self.load()
        self.assertEqual(self.c.execute('SELECT count(*) FROM api_events').fetchone()[0],before)
        self.assertEqual(result['events'],[]);self.assertEqual(result['clock_changes'],[])
        self.assertGreater(result['predecessor_source_rows_loaded'],0)
    def test_zero_carbohydrate_input_does_not_replace_last_positive_entry(self):
        self.request('2026-10-20T12:00:00',25)
        self.request('2026-10-28T23:59:00',0,bid=2)
        last=self.load()['predecessors']['carbs']
        self.assertEqual(len(last),1);self.assertEqual(last[0]['value'],25)

    def test_csv_carbohydrates_survive_api_dose_association_without_request(self):
        self.dose('2026-10-20T12:00:00','2026-10-20T12:02:00',3)
        rid=self.csv('Bolo','2026-10-20T12:00:00',3)
        result=self.load();previous=result['predecessors']
        self.assertEqual(len(previous['boluses']),1)
        self.assertEqual(previous['boluses'][0]['source'],'api_bolus_completed')
        self.assertEqual(len(previous['carbs']),1)
        self.assertEqual(previous['carbs'][0]['source'],'csv_carbohydrates')
        self.assertEqual(previous['carbs'][0]['value'],40)
        self.assertEqual(previous['carbs'][0]['id'],rid)

if __name__=='__main__':unittest.main()
