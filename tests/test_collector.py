import json,tempfile,unittest
from pathlib import Path
from tandem.db import connect
from tandem.collector import ingest_pumper,ingest_logs,windows,collect,audit_api,reconcile,writer_lock
from tandem.ingest import ingest_csv,KINDS
import csv,io

DEVICE='11111111-1111-4111-8111-111111111111'
def blob(obj):return json.dumps(obj).encode()
def event(seq=1,value=110,**kw):
    return dict(deviceAssignmentId=DEVICE,eventCode=16,sequenceGroup=1,sequenceNumber=seq,
                pumpDateTime='2026-10-25T02:30:00',estimatedDateTime='2026-10-25T02:30:00Z',eventProperties={'bg':value},**kw)
def body(events,clock=None):return blob({'events':events,'clockChanges':clock or []})
def pump(start='2026-10-01',end='2026-10-28'):
    return {'assignmentId':DEVICE,'serialNumber':'123','availableDataRange':{'start':start,'end':end}}

class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite';self.c=connect(self.path)
        self.run=self.c.execute("INSERT INTO api_runs(started_at,status) VALUES('test','running')").lastrowid;self.c.commit()
    def tearDown(self):self.c.close();self.tmp.cleanup()
    def ingest(self,events,clock=None):return ingest_logs(self.c,self.run,body(events,clock),DEVICE,'123','2026-10-01','2026-10-28')
    def n(self,table):return self.c.execute('SELECT count(*) FROM '+table).fetchone()[0]
    def test_idempotence_provenance_and_revision(self):
        self.ingest([event()]);self.ingest([event()]);self.ingest([event(),event(2)]);self.ingest([event(value=111)])
        self.assertEqual(self.n('api_events'),3);self.assertEqual(self.n('api_event_sources'),4)
        self.assertEqual(audit_api(self.c)['identity_revisions'],1)
        self.assertFalse(audit_api(self.c)['event_hash_errors'])
    def test_repeated_clock_times_keep_sequence_identity(self):
        self.ingest([event(),event(2)]);self.assertEqual(self.n('api_events'),2)
        self.assertEqual(self.c.execute('SELECT clock_status FROM api_events LIMIT 1').fetchone()[0],'device_local_unresolved')
    def test_unknown_and_missing_identity_preserved(self):
        a=event();a['eventCode']=999999;a.pop('sequenceNumber');a.pop('sequenceGroup')
        self.ingest([a,a]);self.assertEqual(self.n('api_events'),2)
        self.assertEqual(audit_api(self.c)['unknown_events'],2)
    def test_bad_response_archived_without_advancing(self):
        a=event();a['deviceAssignmentId']='another-device'
        with self.assertRaises(ValueError):self.ingest([event(),a])
        self.assertEqual(self.n('api_payloads'),1);self.assertEqual(self.n('api_events'),0);self.assertEqual(self.n('api_windows'),0)
    def test_truncation_is_not_success(self):
        with self.assertRaises(ValueError):ingest_logs(self.c,self.run,blob({'events':[],'clockChanges':[],'hasMore':True}),DEVICE,'123','2026-10-01','2026-10-28')
        self.assertEqual(self.n('api_windows'),0)
    def test_full_history_clock_changes_outside_window(self):
        a=event();a.update(eventCode=13,pumpDateTime='2025-01-26T00:00:00')
        self.ingest([], [a]);self.assertEqual(self.n('api_events'),1)
    def test_missing_range_fails_if_uploaded(self):
        a=pump();a['availableDataRange']={};a['lastUploadDate']='2026-10-28'
        with self.assertRaises(ValueError):windows(self.c,a)
    def test_window_gap_not_hidden_by_later_success(self):
        ingest_logs(self.c,self.run,body([]),DEVICE,'123','2026-10-10','2026-10-28')
        self.assertEqual(windows(self.c,pump())[0][0],'2026-10-01')
        self.assertEqual(windows(self.c,pump('2026-01-01','2026-03-31'))[0],('2026-01-01','2026-01-28'))
    def test_snapshot_and_unrecognized_settings_retained(self):
        a=pump();a['settings']={'unknownFuture':123}
        ingest_pumper(self.c,self.run,blob({'pumps':[a],'future':'x'}));self.assertIn('unknownFuture',self.c.execute('SELECT details_json FROM api_snapshots').fetchone()[0])
    def test_reconcile_exact_and_conflicting_values_no_merge(self):
        stream=io.StringIO();w=csv.writer(stream);w.writerow(KINDS['GLUCOSA']);w.writerow(['t:slim','123','bg','2026-10-25T02:30:00','110',''])
        with self.c:ingest_csv(self.c,stream.getvalue().encode(),'g.csv','g.csv',None)
        self.ingest([event(),event(2,120)]);links=reconcile(self.c)
        self.assertEqual(links['same_time_value_candidate'],1);self.assertEqual(links['same_time_value_conflict'],1)
        self.assertEqual(self.n('records'),1);self.assertEqual(self.n('api_events'),2)
    def test_collect_twice_and_backups(self):
        class Fake:
            def get_pumper(self):return blob({'pumps':[pump()]})
            def get_pump_logs(self,*args):return body([event()])
        self.c.close()
        a=collect(self.path,client=Fake(),delay=0);b=collect(self.path,client=Fake(),delay=0)
        self.c=connect(self.path)
        self.assertEqual(a['new_events'],1);self.assertEqual(b['new_events'],0)
        self.assertTrue(Path(a['backup_after']).exists());self.assertEqual(self.n('api_runs'),3)
    def test_failed_run_preserves_prior_window_and_failure(self):
        class Fake:
            def get_pumper(self):return blob({'pumps':[pump('2026-09-01')]})
            def get_pump_logs(self,d,s,e):
                if s=='2026-09-01':return body([])
                raise RuntimeError('SECRET must never persist')
        self.c.close()
        with self.assertRaises(RuntimeError):collect(self.path,client=Fake(),delay=0)
        self.c=connect(self.path)
        row=self.c.execute('SELECT * FROM api_runs ORDER BY id DESC LIMIT 1').fetchone()
        self.assertEqual(row['status'],'failed');self.assertNotIn('SECRET',str(dict(row)));self.assertEqual(self.n('api_windows'),1)
    def test_concurrent_writer_rejected(self):
        with writer_lock(self.path):
            with self.assertRaises(RuntimeError):
                with writer_lock(self.path):pass

    def test_cgm_matches_measurement_time_not_log_time(self):
        from datetime import datetime
        sample='2026-10-25T02:30:00'
        seconds=int((datetime.fromisoformat(sample)-datetime(2008,1,1)).total_seconds())
        e=event();e.update(eventCode=399,pumpDateTime='2026-10-25T02:30:03',eventProperties={
            'egvTimeStamp':seconds,'currentGlucoseDisplayValue':110,'glucoseValueStatus':0})
        stream=io.StringIO();w=csv.writer(stream);w.writerow(KINDS['MCG']);w.writerow(['t:slim','123','sensor',sample,'110'])
        with self.c:ingest_csv(self.c,stream.getvalue().encode(),'c.csv','c.csv',None)
        self.ingest([e]);links=reconcile(self.c)
        self.assertEqual(links['same_time_value_candidate'],1)
        first=self.c.execute('SELECT id FROM source_links').fetchone()[0]
        reconcile(self.c);self.assertEqual(self.c.execute('SELECT id FROM source_links').fetchone()[0],first)
        self.assertEqual(self.c.execute('SELECT local_timestamp FROM api_events').fetchone()[0],'2026-10-25T02:30:03')
        query='SELECT 1 FROM source_links s WHERE NOT EXISTS(SELECT 1 FROM wanted_links w WHERE w.event_id=s.event_id AND w.source_table=s.source_table AND w.source_id=s.source_id AND w.relation=s.relation)'
        plan=[r[3] for r in self.c.execute('EXPLAIN QUERY PLAN '+query)]
        self.assertTrue(any('SEARCH w USING' in p for p in plan),plan)

if __name__=='__main__':unittest.main()
