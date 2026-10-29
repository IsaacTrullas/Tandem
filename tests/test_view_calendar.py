import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QDate,Qt
from PySide6.QtTest import QTest
from test_event_hover_widget import APP,bundle,START
from tandem.timeline_widget import TimelineWidget,wall

class ViewCalendarTests(unittest.TestCase):
    def setUp(self):
        self.w=TimelineWidget('unused.sqlite');self.w.resize(1200,820);self.w.show();APP.processEvents()
        self.w.current_start=START;self.w.render(bundle());APP.processEvents()
    def tearDown(self):
        self.w.debounce.stop();self.w.close();self.w.deleteLater();APP.processEvents()
    def test_range_opens_calendar_for_visible_date_and_selects_without_changing_width(self):
        self.w.current_start=wall('2026-10-28T12:00:00');self.w.current_width=10800;self.w._range_text()
        self.w.pump.addItem('Bomba P1','P1')
        with patch.object(self.w,'request') as request:
            self.w.range_label.click();APP.processEvents()
            self.assertTrue(self.w.calendar_popup.isVisible())
            self.assertEqual(self.w.view_calendar.selectedDate(),QDate(2026,10,28))
            self.w.view_calendar.clicked.emit(QDate(2026,10,20))
            request.assert_called_once_with('2026-10-20T00:00:00',10800)
            self.assertEqual(self.w.pump.currentData(),'P1');self.assertFalse(self.w.calendar_popup.isVisible())
            self.w.view_calendar.activated.emit(QDate(2026,10,20));self.assertEqual(request.call_count,1)
    def test_date_field_body_opens_and_cancel_does_not_load(self):
        with patch.object(self.w,'request') as request:
            QTest.mouseClick(self.w.date.lineEdit(),Qt.MouseButton.LeftButton);APP.processEvents()
            self.assertTrue(self.w.calendar_popup.isVisible())
            self.w.calendar_popup.reject();request.assert_not_called()
            self.w._choose_view_date();self.w.hide();self.assertFalse(self.w.calendar_popup.isVisible())
    def test_calendar_respects_device_dates_and_is_unavailable_while_busy(self):
        self.w.bounds={'first':'2026-03-16T00:00:00','last':'2026-10-29T14:00:00'}
        self.w.busy=True;self.w._choose_view_date();self.assertIsNone(self.w.calendar_popup)
        self.w.busy=False;self.w._choose_view_date()
        self.assertEqual(self.w.view_calendar.minimumDate(),QDate(2026,3,16))
        self.assertEqual(self.w.view_calendar.maximumDate(),QDate(2026,10,29))

if __name__=='__main__':unittest.main()
