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
from tandem.plot_symbols import COLORS,symbol
from tandem.bolus_display import MARKED_BOLUS_LABEL

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
        self.assertIn('110 mg/dL',self.w.values['glucose'].accessibleName())
        self.assertIn('Programa prueba',self.w.values['profile'].text());self.assertIn('1,2 U',self.w.values['iob'].accessibleName())
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
    def test_mode_lane_and_external_legend_remain_readable_and_bounded(self):
        b=bundle();b['data']['glucose'].append(point(START+23*3600,120))
        b['context']['timelines']={'mode':[{'x':START-3600,'value':'sleep','source':'API','id':1},
            {'x':START+6*3600,'value':'normal','source':'API','id':2},
            {'x':START+10*3600,'value':'exercise','source':'API','id':3},
            {'x':START+12*3600,'value':'normal','source':'API','id':4}]}
        self.w.current_start=START;self.w.render(b)
        modes={s['mode'] for s in self.w.mode_segments}
        self.assertIn('sleep',modes);self.assertIn('exercise',modes)
        self.assertGreaterEqual(self.w.mode_lane.minimumHeight(),58)
        self.assertEqual(len(self.w.legend_entries),11)
        self.assertTrue(all(plot.legend is None for plot in self.w.plots))
        self.assertTrue(all(s['end']<=START+23*3600 for s in self.w.mode_segments))
    def test_provenance_time_visible_without_expanding_and_warning_not_hidden(self):
        b=bundle();b['data']['warnings']=['Datos limitados: reduzca la ventana.'];self.w.current_start=START;self.w.render(b)
        with patch('tandem.timeline_widget.context_at',return_value={
            'profile':{'value':'Programa prueba','time':iso(START-86400)},
            'iob':{'value':1.2,'unit':'U','time':iso(START+250)}}):self.w.hover_at(START+300)
        self.assertIn('obs.',self.w.values['profile'].text());self.assertIn('28/10',self.w.values['profile'].text())
        self.assertIn('00:04:10',self.w.time_labels['iob'].text())
        self.assertFalse(self.w.alert.isHidden());self.assertTrue(self.w.detail.isHidden())
    def test_metric_units_do_not_wrap_and_mode_icon_text_groups_fit(self):
        b=bundle();b['data']['glucose'].append(point(START+23*3600,120))
        b['context']['timelines']={'mode':[{'x':START,'value':'normal','id':1},
            {'x':START+10*3600,'value':'exercise','id':2},{'x':START+13*3600,'value':'normal','id':3}]}
        self.w.current_start=START;self.w.render(b);APP.processEvents();self.w._layout_mode_labels()
        self.w.set_value('glucose','168 mg/dL\n2026-10-29T10:00:00')
        value=self.w.values['glucose'];self.assertFalse(value.wordWrap());self.assertEqual(value.accessibleName(),'168 mg/dL')
        self.assertIn('font-size:10pt',value.text())
        for group in self.w.mode_label_meta:
            self.assertGreaterEqual(group['group_left'],group['start'])
            self.assertLessEqual(group['group_right'],group['end'])
    def test_reload_preserves_viewport_and_pump(self):
        self.w.current_start=START;self.w.current_width=3600;self.w.pump.addItem('Bomba P1','P1');self.w.initialized=True
        with patch.object(self.w,'activate'):self.w.reload()
        self.assertEqual(self.w._preserve_view,(START,3600,'P1'))
        class Worker:
            def deleteLater(self):pass
        self.w.worker=Worker();self.w._error=None;self.w._kind='bounds'
        self.w._result={'first':'2026-10-01T00:00:00','last':'2026-10-30T00:00:00','devices':['P1']}
        with patch.object(self.w,'request') as request:self.w._finished()
        request.assert_called_once_with(START,3600)
    def test_old_clock_predecessor_does_not_create_permanent_warning(self):
        b=bundle();b['context']['clock_changes']=[{'x':START-86400}]
        self.w.current_start=START;self.w.render(b)
        with patch('tandem.timeline_widget.context_at',return_value={'warnings':['Hay cambios de reloj; las observaciones posteriores restauran el contexto.']}):
            self.w.hover_at(START+300)
        self.assertTrue(self.w.alert.isHidden())
        b['context']['clock_changes'].append({'x':START+60})
        with patch('tandem.timeline_widget.context_at',return_value={'warnings':['Hay cambios de reloj.']}):self.w.hover_at(START+300)
        self.assertFalse(self.w.alert.isHidden())

    def test_event_guides_are_shared_per_panel_and_replaced_with_window(self):
        b=bundle();b['data']['boluses']=[point(START+3600,1,'bolus')]
        b['data']['carbs']=[point(START+3600,20,'carbs')]
        b['data']['events']=[point(START+7200,None,'mode',label='Cambio de modo',event_code=229)]
        self.w.current_start=START;self.w.render(b)
        self.assertEqual(len(self.w.event_guides),5)
        self.assertTrue(all(g.times==(START+3600,START+7200) for g in self.w.event_guides))
        self.assertEqual(len(self.w.event_times),2)
        self.w.render(bundle(START+86400))
        self.assertTrue(all(g.times==() for g in self.w.event_guides))
        self.assertEqual(self.w.plots[3].getAxis('bottom').event_times,())

    def test_event_time_labels_align_with_guides_and_follow_zoom(self):
        b=bundle();event_x=START+4*3600+123
        b['data']['boluses']=[point(event_x,1,'bolus')]
        self.w.current_start=START;self.w.render(b);APP.processEvents();self.w.grab()
        axis=self.w.plots[3].getAxis('bottom');self.assertEqual(len(axis.event_labels),1)
        label=axis.event_labels[0];self.assertEqual(label['text'],'04:02')
        actual=axis.mapToScene(QPointF(label['axis_x'],0)).x()
        expected=self.w.plots[3].getViewBox().mapViewToScene(QPointF(event_x,0)).x()
        self.assertAlmostEqual(actual,expected,places=4)
        self.w.plots[0].setXRange(START+3*3600,START+5*3600,padding=0)
        APP.processEvents();self.w.grab()
        self.assertEqual(axis.event_labels[0]['text'],'04:02:03')
        self.assertLessEqual(axis.event_labels[0]['rect'].bottom(),axis.height())
        class Hover:
            def __init__(self,x,exiting=False):self.x=x;self.exiting=exiting
            def isExit(self):return self.exiting
            def scenePos(self):return self_view.mapViewToScene(QPointF(self.x,0))
        self_view=self.w.plots[3].getViewBox()
        axis.hoverEvent(Hover(event_x));self.assertIn('04:02:03',axis.toolTip())
        axis.hoverEvent(Hover(event_x+1800));self.assertEqual(axis.toolTip(),axis.HELP)
        axis.hoverEvent(Hover(event_x));axis.hoverEvent(Hover(event_x,True))
        self.assertEqual(axis.toolTip(),axis.HELP)

    def test_005_bolus_uses_distinct_marker_without_changing_dose_or_time(self):
        from copy import deepcopy
        b=bundle();b['data']['boluses']=[point(START+3600,.05,'bolus'),point(START+7200,.051,'bolus')]
        b['context']['observed_iob']=[point(START+3600,.05,'iob')]
        original=deepcopy(b['data']);self.w.current_start=START;self.w.render(b)
        APP.processEvents();self.w._pad_bolus_axis();self.w.grab()
        series=self.w.plots[1].listDataItems()
        marked=next(item for item in series if item.name()==MARKED_BOLUS_LABEL)
        regular=next(item for item in series if item.name()=='Bolos')
        self.assertEqual(list(marked.xData),[START+3600]);self.assertEqual(list(marked.yData),[.05])
        self.assertEqual(list(regular.yData),[.051])
        self.assertEqual(marked.opts['symbolBrush'],COLORS['bolus_005'])
        self.assertGreater(marked.zValue(),next(item for item in series if item.name()=='Activa observada').zValue())
        vb=self.w.plots[1].getViewBox();center=vb.mapViewToScene(QPointF(START+3600,.05))
        self.assertGreaterEqual(vb.sceneBoundingRect().bottom()-center.y(),11)
        self.assertTrue(all(value>=0 for _,ticks in self.w.plots[1].getAxis('left').tickValues(*vb.viewRange()[1],100) for value in ticks))
        self.assertEqual(b['data'],original)
        self.assertEqual(symbol('bolus_005'),symbol('bolus'))
        self.assertEqual(len(self.w.event_times),2)
        self.assertIn(MARKED_BOLUS_LABEL,self.w.event_times[0]['labels'])

    def test_005_bolus_inspector_restores_normal_color_and_handles_ambiguity(self):
        b=bundle();b['data']['boluses']=[point(START+3600,.05,'bolus'),point(START+7200,.5,'bolus')]
        self.w.current_start=START;self.w.render(b)
        self.w.hover_at(START+3600)
        self.assertEqual(self.w.values['bolus'].accessibleName(),'0,05 U')
        self.assertIn(COLORS['bolus_005'],self.w.values['bolus'].styleSheet())
        self.assertEqual(self.w.metric_captions['bolus'].text(),'Último bolo')
        self.assertIn('resaltado por dosis',self.w.values['bolus'].toolTip())
        self.assertIn(MARKED_BOLUS_LABEL,self.w.detail.text())
        self.w.hover_at(START+7200)
        self.assertIn(COLORS['bolus'],self.w.values['bolus'].styleSheet())
        self.assertEqual(self.w.metric_captions['bolus'].text(),'Último bolo')
        self.w.hover_at(START+12000)
        self.assertIn(COLORS['bolus'],self.w.values['bolus'].styleSheet())
        b['data']['boluses'].append(point(START+3600,.1,'bolus'))
        self.w.render(b);self.w.hover_at(START+3600)
        self.assertIn('Ambiguo',self.w.values['bolus'].accessibleName())
        self.assertIn(COLORS['bolus'],self.w.values['bolus'].styleSheet())

if __name__=='__main__':unittest.main()
