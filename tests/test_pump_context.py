import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tandem.db import connect,dumps,digest
from tandem.pump_context import load_context,context_at,wall_seconds

class PumpContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'test.sqlite';self.conn=connect(self.db);self.counter=0
    def tearDown(self):self.conn.close();self.temp.cleanup()
    def event(self,code,time,props,serial='TEST',identity=None):
        self.counter+=1
        raw=dumps({'eventCode':code,'pumpDateTime':time,'eventProperties':props})
        self.conn.execute('''INSERT INTO api_events(device_id,pump_serial,identity_key,identity_method,sequence_group,sequence_number,
          event_code,event_name,kind,local_timestamp,local_date,clock_status,unit,value,values_json,decode_status,raw_json,sha256,decoder_version)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
          ('device-'+serial,serial,identity or str(self.counter),'sequence',1,self.counter,code,'test','test',time,time[:10],'device_local_unresolved',None,None,'{}','decoded',raw,digest(raw.encode()),'1.1'));self.conn.commit()
    def context(self,start='2026-10-29T00:00:00',end='2026-10-30T00:00:00',serial='TEST'):
        return load_context(self.db,start,end,serial)
    def test_observed_units_and_iob_not_selected_iob_enum(self):
        self.event(3,'2026-10-29T08:00:00',{'idp':0,'baseBasalRate':.6})
        self.event(64,'2026-10-29T08:01:00',{'bolusId':4,'carbRatio':12500,'iob':1.8})
        self.event(65,'2026-10-29T08:01:01',{'bolusId':4,'isf':80,'targetBg':110,'selectedIob':1})
        self.event(55,'2026-10-29T08:01:02',{'iob':1.8,'selectedIob':1})
        c=self.context();p=context_at(c,'2026-10-29T08:02:00')
        self.assertEqual(p['profile']['profile_id'],0);self.assertEqual(p['basal_profile']['value'],.6)
        self.assertEqual(p['carb_ratio']['value'],12.5);self.assertEqual(p['sensitivity']['value'],80)
        self.assertEqual(p['target']['value'],110);self.assertEqual(p['iob']['value'],1.8)
        self.assertEqual(p['iob']['unit'],'U');self.assertEqual(p['carb_ratio']['method'],'last_observed')
    def test_iob_no_interpolation_and_expires(self):
        self.event(20,'2026-10-29T08:00:00',{'iob':2.2});self.event(20,'2026-10-29T08:20:00',{'iob':1.1})
        c=self.context()
        self.assertEqual(context_at(c,'2026-10-29T08:05:00')['iob']['value'],2.2)
        self.assertIsNone(context_at(c,'2026-10-29T08:15:00')['iob']['value'])
        self.assertEqual(context_at(c,'2026-10-29T08:15:00')['iob']['last_observed_value'],2.2)
        self.assertEqual(context_at(c,'2026-10-29T08:20:00')['iob']['value'],1.1)
    def test_unknown_iob_units_never_used(self):
        self.event(9,'2026-10-29T08:00:00',{'iob':1234})
        c=self.context();self.assertEqual(c['observed_iob'],[]);self.assertIsNone(context_at(c,'2026-10-29T08:01:00')['iob']['value'])
    def test_profile_change_invalidates_previous_program_ratios(self):
        self.event(69,'2026-10-29T07:00:00',{'idp':0,'status':3})
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':10000})
        self.event(69,'2026-10-29T09:00:00',{'idp':2,'status':3})
        c=self.context();self.assertEqual(context_at(c,'2026-10-29T08:30:00')['carb_ratio']['value'],10)
        p=context_at(c,'2026-10-29T09:01:00');self.assertEqual(p['profile']['profile_id'],2);self.assertIsNone(p['carb_ratio']['value'])
    def test_clock_change_invalidates_carry_and_later_observation_restores(self):
        self.event(3,'2026-10-29T07:00:00',{'idp':0,'baseBasalRate':.6})
        self.event(64,'2026-10-29T07:20:00',{'carbRatio':10000})
        self.event(13,'2026-10-29T08:00:00',{})
        self.event(3,'2026-10-29T08:01:00',{'idp':0,'baseBasalRate':.7})
        c=self.context();p=context_at(c,'2026-10-29T08:00:30')
        self.assertIsNone(p['profile']['value']);self.assertIsNone(p['carb_ratio']['value'])
        p=context_at(c,'2026-10-29T08:02:00');self.assertEqual(p['basal_profile']['value'],.7);self.assertIsNone(p['carb_ratio']['value'])
    def test_clock_overlap_does_not_choose_a_branch(self):
        self.event(3,'2026-10-29T02:05:00',{'idp':0,'baseBasalRate':.6})
        self.event(13,'2026-10-29T02:00:00',{'timePrior':3*3600000,'timeAfter':2*3600000})
        p=context_at(self.context(),'2026-10-29T02:30:00');self.assertIsNone(p['basal_profile']['value']);self.assertEqual(p['basal_profile']['method'],'ambiguous_clock_interval')
    def test_latest_snapshot_not_applied_to_past(self):
        with self.conn:
            self.conn.execute("INSERT INTO api_payloads VALUES(1,'h',X'7B7D',2,'2026-10-29')")
            self.conn.execute("INSERT INTO api_snapshots VALUES(1,1,'dev','TEST','2026-10-29',NULL,?)",(json.dumps({'settings':{'basal':99}}),))
        p=context_at(self.context(),'2026-10-29T08:00:00');self.assertIsNone(p['basal_profile']['value']);self.assertIsNone(p['profile']['value'])
    def test_names_come_only_from_observed_messages_not_future(self):
        first={f'name{i}':v for i,v in enumerate(b'Programa')};first.update(idp=0,status=3)
        second={f'name{i+8}':v for i,v in enumerate(b' Uno\0\0\0\0')};second['idp']=0
        self.event(69,'2026-10-29T08:00:00',first);self.event(57,'2026-10-29T08:00:01',second)
        c=self.context();self.assertEqual(context_at(c,'2026-10-29T08:00:00')['profile']['value'],'Programa…')
        self.assertEqual(context_at(c,'2026-10-29T08:00:02')['profile']['value'],'Programa Uno')
    def test_nul_terminated_name_does_not_append_ff_continuation_padding(self):
        first={f'name{i}':v for i,v in enumerate(b'Diari\x00\xff\xff')};first.update(idp=0,status=3)
        second={f'name{i+8}':255 for i in range(8)};second['idp']=0
        self.event(69,'2026-10-29T08:00:00',first);self.event(57,'2026-10-29T08:00:01',second)
        p=context_at(self.context(),'2026-10-29T08:00:02')['profile']
        self.assertEqual(p['value'],'Diari');self.assertTrue(p['name_complete'])
    def test_unproven_high_byte_padding_keeps_only_verified_prefix(self):
        first={f'name{i}':v for i,v in enumerate(b'Partial\xff')};first.update(idp=0,status=3)
        second={f'name{i+8}':v for i,v in enumerate(b'Ignored\0')};second['idp']=0
        self.event(69,'2026-10-29T08:00:00',first);self.event(57,'2026-10-29T08:00:01',second)
        p=context_at(self.context(),'2026-10-29T08:00:02')['profile']
        self.assertEqual(p['value'],'Partial…');self.assertFalse(p['name_complete'])
        self.assertNotIn('\ufffd',p['value'])
    def test_multi_pump_isolation(self):
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':10000},'TEST')
        self.event(64,'2026-10-29T08:01:00',{'carbRatio':20000},'OTHER')
        with self.assertRaises(ValueError):load_context(self.db,'2026-10-29T00:00:00','2026-10-30T00:00:00')
        self.assertEqual(context_at(self.context(),'2026-10-29T08:02:00')['carb_ratio']['value'],10)
    def test_bounded_window_predecessor_and_read_only(self):
        for day in range(1,29):self.event(64,f'2026-10-{day:02}T08:00:00',{'carbRatio':day*1000})
        before=self.db.read_bytes();c=self.context()
        self.assertLessEqual(c['loaded_rows'],2);self.assertEqual(len(c['timelines']['carb_ratio']),1)
        self.assertEqual(context_at(c,'2026-10-29T08:02:00')['carb_ratio']['value'],28)
        with patch('tandem.pump_context.sqlite3.connect',side_effect=AssertionError('hover must not query')):
            context_at(c,'2026-10-29T08:03:00')
        self.assertEqual(before,self.db.read_bytes())
        with self.assertRaises(ValueError):self.context('2026-10-01T00:00:00','2026-10-29T00:00:00')
    def test_revisions_and_same_time_iob_values_are_ambiguous(self):
        self.event(20,'2026-10-29T08:00:00',{'iob':1.2})
        self.event(55,'2026-10-29T08:00:00',{'iob':1.3})
        p=context_at(self.context(),'2026-10-29T08:01:00');self.assertIsNone(p['iob']['value'])
        self.assertEqual(p['iob']['method'],'ambiguous_same_wall_time')
    def test_hover_outside_loaded_window_never_carries(self):
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':10000})
        p=context_at(self.context(),'2026-10-30T09:00:00');self.assertIsNone(p['carb_ratio']['value']);self.assertEqual(p['carb_ratio']['method'],'outside_loaded_window')
    def test_density_limit_fails_instead_of_caching_unbounded_context(self):
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':10000})
        self.event(64,'2026-10-29T08:01:00',{'carbRatio':11000})
        with patch('tandem.pump_context.MAX_CONTEXT_ROWS',1):
            with self.assertRaises(ValueError):self.context()
    def test_revised_identity_never_chosen_as_single_true_value(self):
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':10000},identity='same')
        self.event(64,'2026-10-29T08:00:00',{'carbRatio':12000},identity='same')
        p=context_at(self.context(),'2026-10-29T08:01:00');self.assertIsNone(p['carb_ratio']['value'])
        self.assertEqual(p['carb_ratio']['method'],'ambiguous_source_revision')

if __name__=='__main__':unittest.main()
