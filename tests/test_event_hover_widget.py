import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPointF,QEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from tandem.app import ensure_fonts
from tandem.timeline_widget import TimelineWidget,wall,iso

APP=QApplication.instance() or QApplication([])
ensure_fonts()
START=wall('2026-10-29T00:00:00')

def point(x,value,unit='U',**details):
    return {'x':x,'time':iso(x),'value':value,'unit':unit,'source':'synthetic','id':x,'details':details}

def bundle():
    data={key:[] for key in ('glucose','boluses','carbs','basal','events','clock_changes')}
    data['glucose']=[point(START,100,'mg/dL',kind='cgm'),point(START+23*3600,120,'mg/dL',kind='cgm')]
    data['warnings']=[]
    return {'data':data,'context':{'start':iso(START),'end':iso(START+86400),'timelines':{},'observed_iob':[],'warnings':[]},
            'view_start':START,'view_width':86400,'cache_start':START,'cache_end':START+86400}

class HoverWidgetTests(unittest.TestCase):
    def setUp(self):
        self.w=TimelineWidget('unused.sqlite');self.w.resize(1200,820);self.w.show();APP.processEvents()
    def tearDown(self):
        self.w.debounce.stop();self.w.close();self.w.deleteLater();APP.processEvents()
    def render(self,b):
        self.w.current_start=START;self.w.render(b);APP.processEvents();self.w._position_event_markers();self.w._pad_bolus_axis()
        self.w._pointer_inside=True
    def move(self,plot,x,y):
        pos=plot.getViewBox().mapViewToScene(QPointF(x,y));self.w._mouse_move((pos,));return pos
    def test_popup_requires_both_coordinates_and_preserves_frozen_selection(self):
        b=bundle();b['data']['boluses']=[point(START+3600,1.5)];self.render(b)
        self.w.hover_at(START+300);self.w.frozen=True
        with patch('tandem.timeline_widget.load_timeline') as load,patch('tandem.timeline_widget.load_context') as context:
            self.move(self.w.plots[1],START+3600,1.5)
            self.assertFalse(self.w.event_popup.isHidden());self.assertIn('Bolo',self.w._hover_plain)
            self.assertIn('1,5 U',self.w._hover_plain);self.assertIn('01:00:00',self.w._hover_plain)
            self.assertEqual(self.w.last_hover,START+300)
            load.assert_not_called();context.assert_not_called()
        self.move(self.w.plots[1],START+3600,0)
        self.assertTrue(self.w.event_popup.isHidden())
    def test_small_bolus_coincident_observations_are_not_added_and_popup_fits(self):
        b=bundle();b['data']['boluses']=[point(START+3600,.05),point(START+3600,.051)]
        self.render(b);self.move(self.w.plots[1],START+3600,.05)
        self.assertIn('Bolo de 0,05 U',self.w._hover_plain);self.assertIn('0,051 U',self.w._hover_plain)
        self.assertNotIn('0,101',self.w._hover_plain)
        self.assertTrue(self.w.canvas.viewport().rect().contains(self.w.event_popup.geometry()))
        self.assertFalse(self.w.tooltip.isVisible())
    def test_glucose_bg_iob_carbs_and_basal_show_their_units(self):
        b=bundle();x=START+12*3600
        b['data']['glucose'].append(point(x,150,'mg/dL',kind='bg'))
        b['data']['carbs']=[point(x,25,'g')];b['data']['basal']=[point(x,.4,'U/h',profile_rate=.3)]
        b['context']['observed_iob']=[point(x,.8)]
        self.render(b)
        for plot,value,title,quantity in ((self.w.plots[0],150,'Glucemia introducida','150 mg/dL'),
            (self.w.plots[1],.8,'Insulina activa observada','0,8 U'),
            (self.w.plots[2],.4,'Tasa basal indicada','0,4 U/h'),
            (self.w.plots[3],25,'Carbohidratos','25 g')):
            self.move(plot,x,value);self.assertFalse(self.w.event_popup.isHidden())
            self.assertIn(title,self.w._hover_plain);self.assertIn(quantity,self.w._hover_plain)
    def test_alarm_triangle_hit_follows_actual_position_after_resize(self):
        b=bundle();x=START+12*3600;b['data']['events']=[point(x,None,'',label='Alarma de bomba',event_code=5)]
        self.render(b);self.w.resize(1180,720);APP.processEvents();self.w._position_event_markers()
        marker=self.w.event_markers[0][0];y=marker.getData()[1][0]
        self.move(self.w.plots[0],x,y)
        self.assertFalse(self.w.event_popup.isHidden());self.assertIn('Alarma de bomba',self.w._hover_plain)
        self.assertNotIn('Sin valor',self.w._hover_plain)
    def test_mode_band_hit_uses_observed_start_and_excludes_empty_lane(self):
        b=bundle();b['context']['timelines']={'mode':[{'x':START-3600,'value':'sleep','id':1}]}
        self.render(b);self.move(self.w.mode_lane,START+12*3600,.5)
        self.assertIn('Modo · Sueño',self.w._hover_plain)
        self.assertIn('28/10/2026 23:00:00',self.w._hover_plain)
        self.assertIn('Sin fin confirmado',self.w._hover_plain)
        self.move(self.w.mode_lane,START+12*3600,.02);self.assertTrue(self.w.event_popup.isHidden())
    def test_popup_clears_on_leave_pending_move_range_hide_and_replacement(self):
        b=bundle();x=START+3600;b['data']['boluses']=[point(x,1)]
        self.render(b);pos=self.move(self.w.plots[1],x,1)
        viewport=self.w.canvas.viewport();self.w.eventFilter(viewport,QEvent(QEvent.Type.Leave))
        self.w._mouse_move((pos,));self.assertTrue(self.w.event_popup.isHidden())
        self.w.eventFilter(viewport,QEvent(QEvent.Type.Enter));self.w._mouse_move((pos,))
        self.assertFalse(self.w.event_popup.isHidden())
        self.w.plots[0].setXRange(START+60,START+23*3600,padding=0)
        self.assertTrue(self.w.event_popup.isHidden())
        self.move(self.w.plots[1],x,1);self.w.hide();self.assertTrue(self.w.event_popup.isHidden())
        self.w.show();self.render(bundle())
        self.move(self.w.plots[1],x,1);self.assertTrue(self.w.event_popup.isHidden())

    def test_many_long_overlapping_messages_fit_in_compact_chart(self):
        b=bundle();x=START+3600
        b['data']['boluses']=[point(x,1+i*.001,revision_count=2,
            source_conflict={'api_delivered_units':1+i*.001,'csv_delivered_units':1.2}) for i in range(8)]
        self.w.resize(1180,700);self.render(b);self.move(self.w.plots[1],x,1)
        self.assertFalse(self.w.event_popup.isHidden())
        self.assertTrue(self.w.canvas.viewport().rect().contains(self.w.event_popup.geometry()))
        self.assertIn('observaciones más',self.w._hover_plain)

    def test_dense_iob_neighbours_do_not_expand_the_selected_bolus_message(self):
        b=bundle();x=START+3600;b['data']['boluses']=[point(x,.05)]
        b['context']['observed_iob']=[point(x+offset,.158) for offset in (-34,-15,0,15,34)]
        self.render(b);self.move(self.w.plots[1],x,.05)
        self.assertIn('Bolo de 0,05 U',self.w._hover_plain)
        self.assertNotIn('Insulina activa',self.w._hover_plain)
        self.assertLess(self.w.event_popup.height(),150)

    def test_visible_005_drop_takes_precedence_over_iob_behind_its_tip(self):
        b=bundle();x=START+3600;b['data']['boluses']=[point(x,.05)];self.render(b)
        vb=self.w.plots[1].getViewBox();center=vb.mapViewToScene(QPointF(x,.05))
        tip=QPointF(center.x(),center.y()-7);iob=vb.mapSceneToView(tip).y()
        b['context']['observed_iob']=[point(x,iob)];self.render(b)
        center=vb.mapViewToScene(QPointF(x,.05));tip=QPointF(center.x(),center.y()-7)
        self.w._mouse_move((tip,));self.assertIn('Bolo de 0,05 U',self.w._hover_plain)
        self.assertNotIn('Insulina activa',self.w._hover_plain)

    def test_same_time_conflicting_doses_are_kept_even_when_far_apart_vertically(self):
        b=bundle();x=START+3600;b['data']['boluses']=[point(x,.05),point(x,2.5)]
        self.render(b);self.move(self.w.plots[1],x,.05)
        self.assertIn('0,05 U',self.w._hover_plain);self.assertIn('2,5 U',self.w._hover_plain)
        self.assertNotIn('2,55',self.w._hover_plain)

if __name__=='__main__':unittest.main()
