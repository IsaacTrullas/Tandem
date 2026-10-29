import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import gc,time,unittest,weakref
from unittest.mock import patch
from datetime import datetime,timedelta
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPointF
from PySide6.QtTest import QTest
from tandem.app import ensure_fonts
from tandem.timeline_widget import TimelineWidget,wall,iso

APP=QApplication.instance() or QApplication([])
ensure_fonts()
START=wall('2026-10-29T00:00:00')
def point(x,value,kind='cgm',**details):
    return {'x':x,'time':iso(x),'value':value,'unit':'mg/dL' if kind in ('cgm','bg') else 'U',
            'source':'synthetic','id':int(x),'details':{'kind':kind,**details}}
def bundle(start=START):
    data={key:[] for key in ('glucose','boluses','carbs','basal','events','clock_changes')}
    data.update(glucose=[point(start,100),point(start+300,110)],warnings=[])
    context={'start':iso(start),'end':iso(start+86400),'timelines':{},'observed_iob':[],'warnings':[]}
    return {'data':data,'context':context,'view_start':start,'view_width':86400,'cache_start':start,'cache_end':start+86400}
def settle(widget):
    end=time.monotonic()+10
    while widget.busy and time.monotonic()<end:QTest.qWait(10)
    if widget.busy:raise AssertionError('Timeline worker did not finish')

class TimelineWidgetTests(unittest.TestCase):
    def setUp(self):self.w=TimelineWidget('unused.sqlite');self.w.resize(1200,720);self.w.show();APP.processEvents()
    def tearDown(self):settle(self.w);self.w.close();self.w.deleteLater();APP.processEvents()
    def test_mouse_crosshair_updates_observed_values_and_context(self):
        b=bundle();self.w.current_start=START;self.w.render(b)
        p=self.w.plots[0].getViewBox().mapViewToScene(QPointF(START+300,110))
        with patch('tandem.timeline_widget.context_at',return_value={'profile':{'value':'Programa prueba','time':iso(START)},'iob':{'value':1.2,'unit':'U','time':iso(START+250)}}):
            self.w._mouse_move((p,))
        self.assertAlmostEqual(self.w.last_hover,START+300,places=2)
        self.assertIn('110 mg/dL',self.w.values['glucose'].text())
        self.assertIn('Programa prueba',self.w.values['profile'].text());self.assertIn('1.2 U',self.w.values['iob'].text())
        self.w.frozen=True;self.w._mouse_move((self.w.plots[0].getViewBox().mapViewToScene(QPointF(START,100)),))
        self.assertAlmostEqual(self.w.last_hover,START+300,places=2)
    def test_navigation_uses_current_window_and_clamps_week(self):
        self.w.bounds={'first':'2026-10-01T00:00:00','last':'2026-11-01T00:00:00'}
        with patch.object(self.w,'_run') as run:
            self.w.request(START,3600);self.assertEqual(self.w.current_width,3600)
            self.w.shift(-1);self.assertEqual(self.w.current_start,START-3600)
            self.w.request(START,9999999);self.assertEqual(self.w.current_width,7*86400)
    def test_pending_pan_keeps_only_latest_request_and_margin_is_bounded(self):
        self.w.busy=True;self.w.request(START,3600);self.w.request(START+3600,3600)
        self.assertEqual(self.w.pending,(START+3600,3600));self.w.busy=False
        with patch('tandem.timeline_widget.load_timeline',return_value=bundle()['data']) as load,patch('tandem.timeline_widget.load_context',return_value=bundle()['context']),patch.object(self.w,'_run') as run:
            self.w.request(START,86400);work=run.call_args.args[0];r=work()
            self.assertLessEqual(r['cache_end']-r['cache_start'],86400+7200)
            self.assertEqual(load.call_count,1)
    def test_replacing_window_releases_old_series(self):
        class Marker:pass
        b=bundle();marker=Marker();ref=weakref.ref(marker);b['data']['glucose'][0]['marker']=marker
        self.w.current_start=START;self.w.render(b);del b,marker
        self.w.render(bundle(START+86400));gc.collect()
        self.assertIsNone(ref());self.assertEqual(len(self.w.point_lists['glucose'][0]),2)
    def test_duplicate_wall_times_and_high_low_are_explicit(self):
        b=bundle();b['data']['glucose'].append(point(START,140))
        self.w.current_start=START;self.w.render(b)
        self.assertIn('Ambiguo',self.w.point_text(self.w.nearest('glucose',START,30)))
        self.assertIn('ALTA',self.w.point_text(point(START,None,qualifier='high')))
    def test_basal_gaps_do_not_interpolate_and_missing_profile_is_not_zero(self):
        import numpy as np
        b=bundle();b['data']['basal']=[point(START,.5,'basal',profile_rate=.4),point(START+3600,.8,'basal')]
        self.w.current_start=START;self.w.render(b)
        commanded=self.w.plots[2].listDataItems()[0];profile=self.w.plots[2].listDataItems()[1]
        self.assertTrue(np.isnan(commanded.yData).any());self.assertTrue(np.isnan(profile.yData[-1]))

if __name__=='__main__':unittest.main()
