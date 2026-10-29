import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest,sqlite3,tempfile,json
from pathlib import Path
from copy import deepcopy
from tandem.basal_comparison import regions
from tandem.presentation_details import bolus_lines,sensor_lines,basal_lines,extended_span,load_pdf_summary,alert_glucose_context
from tandem.alert_details import alert_details
from tandem.alert_audit import audit
import test_timeline_data as fixtures
from test_event_hover_widget import APP,bundle,point,START
from tandem.timeline_widget import TimelineWidget

class PresentationTests(unittest.TestCase):
    def test_regions_conserve_rates_exclude_gaps_missing_and_clocks(self):
        rows=[point(START,1,profile_rate=.5),point(START+300,0,profile_rate=.5),point(START+600,.5,profile_rate=.5),point(START+2000,1)]
        original=deepcopy(rows);r=regions(rows)
        self.assertEqual([p[-1] for p in r],['above','below'])
        self.assertEqual(len(regions(rows,[{'x':START+100}])),1);self.assertEqual(rows,original)
    def test_bolus_source_requested_and_components_are_separate(self):
        p=point(START,2,properties={'bolusSource':7,'requestedNow':2000,'requestedLater':1000},phases=[{'code':66,'time':'2026-10-29T00:00:00','properties':{'foodBolusSize':2,'correctionBolusSize':1}}])
        text='\n'.join(bolus_lines(p));self.assertIn('Algoritmo',text);self.assertIn('extendida',text.lower());self.assertIn('Corrección solicitada: 1 U',text)
    def test_sensor_fields_retain_source_units(self):
        text='\n'.join(sensor_lines(point(START,100,properties={'rate':-2,'rssi':-60},labels={})))
        self.assertIn('rate original: -2',text);self.assertIn('escala pendiente',text);self.assertIn('-60 dBm',text)
        self.assertIn('2 mg/dL/min','\n'.join(sensor_lines(point(START+300,110),point(START,100))))
        bg=point(START,140,kind='bg',properties={'bgEntryType':0,'cgmCalibration':1})
        self.assertIn('Uso para calibración registrado: sí','\n'.join(sensor_lines(bg)))
    def test_basal_components_not_added_as_doses(self):
        text='\n'.join(basal_lines(point(START,.2,profile_rate=.5,measures={'algorithmRate':{'value':.2,'unit':'U/h'}})))
        self.assertIn('-0,3 U/h',text);self.assertIn('Tasa del algoritmo: 0,2 U/h',text)
    def test_extended_requires_recorded_endpoints_not_requested_duration(self):
        self.assertIsNone(extended_span(point(START,1,properties={'extendedDurationRequested':60})))
        p=point(START,1,phases=[{'code':59,'time':'2026-10-29T01:00:00'},{'code':21,'time':'2026-10-29T02:00:00'}])
        self.assertEqual(extended_span(p),('2026-10-29T01:00:00','2026-10-29T02:00:00'))
    def test_official_alert50_and_predictive51_names(self):
        for identifier,word in ((50,'glucosa alta'),(51,'predicción')):
            text='\n'.join(alert_details({'event_code':4,'properties':{'alertId':identifier},'labels':{}}))
            self.assertIn(word,text)
    def test_cleared_not_shown_as_active(self):
        text='\n'.join(alert_details({'event_code':370,'properties':{'dalertId':9},'labels':{}}))
        self.assertIn('Desactivación registrada',text);self.assertNotIn('Alerta activada',text)
    def test_alert_context_uses_prior_cgm_not_future_and_keeps_original(self):
        events=[point(START+300,None,event_code=4)];original=deepcopy(events)
        samples=[point(START,230,kind='cgm'),point(START+301,280,kind='cgm')]
        out=alert_glucose_context(events,samples)
        self.assertEqual(out[0]['details']['prior_glucose']['value'],230)
        self.assertEqual(events,original)
        self.assertNotIn('prior_glucose',alert_glucose_context(events,samples,[{'x':START+100}])[0]['details'])
    def test_audit_does_not_use_future_glucose_and_preserves_rows(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'db';c=sqlite3.connect(p)
            c.execute('CREATE TABLE api_events(id INTEGER,pump_serial TEXT,local_timestamp TEXT,event_code INTEGER,values_json TEXT,device_id TEXT,identity_key TEXT,kind TEXT,unit TEXT,value REAL)')
            c.execute('INSERT INTO api_events VALUES(1,?,?,?,?,?,?,?,?,?)',('P','2026-10-29T01:00:00',4,json.dumps({'properties':{'alertId':50},'labels':{'alertId':'aaAlert_TZ_HYPER_LIGHT'}}),'D','a','alert',None,None))
            c.execute('INSERT INTO api_events VALUES(2,?,?,?,?,?,?,?,?,?)',('P','2026-10-29T01:01:00',399,json.dumps({'measurement_local_timestamp':'2026-10-29T01:01:00'}),'D','b','cgm','mg/dL',250));c.commit();c.close()
            r=audit(p,Path(d)/'out');self.assertEqual(r['events'],1);self.assertEqual(r['summary'][0]['missing'],1)
    def test_widget_baseline_label_fill_and_sections(self):
        w=TimelineWidget('unused.sqlite');w.resize(1200,820);w.show();APP.processEvents()
        b=bundle();b['data']['basal']=[point(START,.2,profile_rate=.5),point(START+300,.8,profile_rate=.5),point(START+600,.8,profile_rate=.5)]
        w.current_start=START;w.render(b);APP.processEvents()
        self.assertFalse(hasattr(w,'profile_label'));self.assertEqual(len(w.basal_regions),2)
        self.assertEqual(w.plots[2].listDataItems()[0].opts['stepMode'],'right')
        self.assertEqual(set(w.extra_views),{'bolus','basal','sensor','events','summary'})
        w.debounce.stop();w.close();w.deleteLater();APP.processEvents()
    def test_pdf_summary_uses_overlapping_period_and_limits_fields(self):
        c=sqlite3.connect(':memory:')
        try:
            c.executescript('CREATE TABLE artifacts(id,filename,period_start,period_end);CREATE TABLE pdf_pages(id,artifact_id,page_number);CREATE TABLE report_fields(page_id,section,label,value_text,review_status,scope,row_index);')
            c.execute("INSERT INTO artifacts VALUES(1,'past.pdf','2026-10-01','2026-10-27')");c.execute('INSERT INTO pdf_pages VALUES(1,1,2)')
            c.executemany("INSERT INTO report_fields VALUES(1,'MCG','Media','150','source_text','summary_period',?)",[(i,) for i in range(122)])
            tables={'report_fields','pdf_pages','artifacts'}
            self.assertEqual(load_pdf_summary(c,tables,'2026-10-29','2026-10-30'),{})
            summary=load_pdf_summary(c,tables,'2026-10-26','2026-10-27')
            self.assertEqual(summary['filename'],'past.pdf');self.assertEqual(len(summary['fields']),120);self.assertTrue(summary['limited'])
        finally:c.close()

class ExpandedDataTests(unittest.TestCase):
    def test_api_details_and_lifecycle_loaded(self):
        fixture=fixtures.TimelineDataTests();fixture.setUp()
        try:
            fixture.cgm();fixture.api(370,'2026-10-29T01:10:00',{'dalertId':9,'sensorType':3})
            fixture.api(34,'2026-10-29T01:20:00',{})
            fixture.api(280,'2026-10-29T02:00:00',{'bolusId':1,'bolusSource':7,'bolusDeliveryStatus':0,'deliveredTotal':2000})
            fixture.api(66,'2026-10-29T02:00:00',{'bolusId':1,'foodBolusSize':1,'correctionBolusSize':1})
            result=fixture.load();self.assertTrue(result['glucose'][0]['details']['properties'])
            self.assertEqual({e['details']['event_code'] for e in result['events']},{34,370})
            self.assertEqual(result['boluses'][0]['details']['phases'][0]['code'],66)
        finally:fixture.tearDown()

if __name__=='__main__':unittest.main()
