import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from copy import deepcopy
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from tandem.app import ensure_fonts
from tandem.timeline_widget import TimelineWidget,wall,iso
from tandem.inspector_values import previous_observation,elapsed_label

APP=QApplication.instance() or QApplication([])
ensure_fonts();START=wall('2026-10-29T00:00:00')
def point(x,value,unit='U',**details):
    return {'x':x,'time':iso(x),'value':value,'unit':unit,'details':details,'source':'synthetic','id':x}
def bundle():
    data={key:[] for key in ('glucose','boluses','carbs','basal','events','clock_changes')}
    data['glucose']=[point(START,110,'mg/dL',kind='cgm')];data['warnings']=[]
    return {'data':data,'context':{'start':iso(START),'end':iso(START+86400),'timelines':{},'observed_iob':[],'warnings':[]},
        'view_start':START,'view_width':86400,'cache_start':START,'cache_end':START+86400}

class InspectorValueTests(unittest.TestCase):
    def test_previous_never_uses_a_future_value_and_keeps_zero(self):
        points=[point(START,0),point(START+60,.05)];xs=[p['x'] for p in points];before=deepcopy(points)
        self.assertIsNone(previous_observation(points,xs,START-1))
        self.assertEqual(previous_observation(points,xs,START+59)['value'],0)
        self.assertEqual(previous_observation(points,xs,START+60)['value'],.05)
        self.assertEqual(points,before)
    def test_previous_keeps_conflicting_time_and_revision_ambiguity(self):
        for points in ([point(START,.05),point(START,.1)],[point(START,.05,revision_count=2)]):
            result=previous_observation(points,[START]*len(points),START+60)
            self.assertTrue(result['details']['ambiguous']);self.assertIsNone(result['value'])
    def test_elapsed_labels_and_clock_barriers(self):
        p=point(START,1)
        for age,label in ((0,'En este instante'),(30,'Hace 30 s'),(300,'Hace 5 min'),(3900,'Hace 1 h 5 min'),(90000,'Hace 1 d 1 h')):
            self.assertEqual(elapsed_label(p,START+age),label)
        self.assertEqual(elapsed_label(p,START+300,[{'x':START+60}]),'Reloj modificado')
        self.assertEqual(elapsed_label(point(START,1,clock_change_between=True),START+300),'Reloj modificado')
        self.assertEqual(elapsed_label(p,START+300,(),[(START-10,START+10)]),'Reloj modificado')

class InspectorWidgetTests(unittest.TestCase):
    def setUp(self):self.w=TimelineWidget('unused.sqlite');self.w.resize(1200,820);self.w.show();APP.processEvents();self.w.current_start=START
    def tearDown(self):self.w.debounce.stop();self.w.close();self.w.deleteLater();APP.processEvents()
    def test_cards_keep_last_values_away_from_events_and_include_predecessors(self):
        b=bundle();b['data']['predecessors']={'boluses':[point(START-86400,.05)],'carbs':[point(START-3600,20,'g')]}
        b['data']['boluses']=[point(START+3600,1)]
        self.w.render(b)
        with patch('tandem.timeline_widget.load_timeline') as load,patch('tandem.timeline_widget.load_context') as context:
            self.w.hover_at(START+1800)
            self.assertEqual(self.w.values['bolus'].accessibleName(),'0,05 U')
            self.assertEqual(self.w.values['carbs'].accessibleName(),'20 g')
            self.assertIn('28/10 00:00:00',self.w.time_labels['bolus'].text())
            self.assertIn('Hace 1 d',self.w.age_labels['bolus'].text())
            self.w.hover_at(START+7200)
            self.assertEqual(self.w.values['bolus'].accessibleName(),'1 U')
            self.assertEqual(self.w.age_labels['bolus'].text(),'Hace 1 h')
            self.w.hover_at(START+1800)
            self.assertEqual(self.w.values['bolus'].accessibleName(),'0,05 U')
            load.assert_not_called();context.assert_not_called()
        self.assertEqual(self.w.point_lists['boluses'][0],b['data']['boluses'])
        self.assertEqual(self.w.event_times[0]['x'],START+3600)
    def test_missing_prior_is_distinct_from_future_and_zero(self):
        b=bundle();b['data']['carbs']=[point(START+1000,0,'g')];self.w.render(b)
        self.w.hover_at(START);self.assertEqual(self.w.values['carbs'].accessibleName(),'Sin registro')
        self.w.hover_at(START+1000);self.assertEqual(self.w.values['carbs'].accessibleName(),'0 g')
    def test_clock_changes_and_limited_lookup_do_not_claim_elapsed_time(self):
        b=bundle();b['data']['predecessors']={'boluses':[point(START-3600,.5,clock_change_between=True)],'carbs':[]}
        self.w.render(b);self.w.hover_at(START+60)
        self.assertEqual(self.w.age_labels['bolus'].text(),'Reloj modificado')
        b['data']['predecessor_truncated']=True;self.w.render(b)
        self.assertIn('consulta limitada',self.w.age_labels['bolus'].text())
    def test_alert_full_technical_details_are_available_in_provenance(self):
        b=bundle();b['data']['events']=[point(START+60,None,'',event_code=4,label='Alerta',
            properties={'alertId':48,'param1':0,'param2':7},labels={'alertId':'aaAlert_CGM_NO_READINGS'})]
        self.w.render(b);self.w.hover_at(START+60)
        self.assertIn('aaAlert_CGM_NO_READINGS',self.w.detail.text())
        self.assertIn('param2',self.w.detail.text());self.assertIn('7',self.w.detail.text())
        b['data']['events']=[point(START+60,None,'',event_code=69,label='Perfil',properties={'profileId':2})]
        self.w.render(b);self.w.hover_at(START+60)
        self.assertIn('profileId',self.w.detail.text());self.assertIn('evento 69',self.w.detail.text())

if __name__=='__main__':unittest.main()
