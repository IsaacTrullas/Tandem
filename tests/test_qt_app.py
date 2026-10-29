import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,time,threading,unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtGui import QCloseEvent
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from tandem.app import Application,TableModel
from tandem.db import connect

APP=QApplication.instance() or QApplication([])
def settle(window):
    stop=time.monotonic()+10
    while window.busy and time.monotonic()<stop:QTest.qWait(10)
    if window.busy:raise AssertionError('Worker did not finish')

class QtAppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/'demo.sqlite'
        c=connect(self.path)
        with c:
            for i in range(205):
                c.execute('INSERT INTO records(fingerprint,occurrence,kind,pump_serial,local_timestamp,local_date,values_json) VALUES(?,?,?,?,?,?,?)',
                  (str(i),0,'MCG','TEST','2026-10-29T00:00:00','2026-10-29','{}'))
                c.execute('INSERT INTO glucose_readings(record_id,origin,glucose_mg_dl) VALUES(?,?,?)',(i+1,'sensor',100+i%20))
        c.close();self.window=Application(self.path,auto_refresh=False)
    def tearDown(self):
        settle(self.window);self.window.close();self.window.deleteLater();APP.processEvents();self.temp.cleanup()
    def test_dashboard_and_readonly_pagination(self):
        before=self.path.read_bytes();self.window.refresh();settle(self.window)
        self.assertEqual(self.window.metrics['records'].text(),'205')
        self.window.datasets.setCurrentIndex(self.window.datasets.findData('glucose'))
        self.window.preview();settle(self.window);self.assertEqual(self.window.model.rowCount(),100)
        self.assertTrue(self.window.next_button.isEnabled())
        first=self.window.model.rows[0]['id']
        self.window.preview_page(100);settle(self.window);self.assertNotEqual(self.window.model.rows[0]['id'],first)
        self.window.preview_page(200);settle(self.window);self.assertEqual(self.window.model.rowCount(),5)
        self.assertFalse(self.window.next_button.isEnabled());self.assertEqual(before,self.path.read_bytes())
        self.window.since.setText('2026-10-30');self.assertEqual(self.window.model.rowCount(),0)
    def test_worker_disables_actions_prevents_close_and_delivers_on_gui_thread(self):
        release=threading.Event();caller=threading.get_ident();observed=[]
        self.window.start('Trabajo de prueba',lambda:(release.wait(2),threading.get_ident())[1],lambda result:observed.append((result,threading.get_ident())))
        self.assertFalse(self.window.collect_button.isEnabled());self.assertFalse(self.window.start('Segundo',lambda:None))
        event=QCloseEvent()
        with patch.object(QMessageBox,'information'):self.window.closeEvent(event)
        self.assertFalse(event.isAccepted());release.set();settle(self.window)
        self.assertNotEqual(observed[0][0],caller);self.assertEqual(observed[0][1],caller)
        self.assertTrue(self.window.collect_button.isEnabled())
    def test_errors_are_sanitized_and_worker_can_be_reused(self):
        def fail():raise RuntimeError('SECRET')
        with patch.object(QMessageBox,'warning') as warning:
            self.window.start('Prueba',fail);settle(self.window)
            self.assertNotIn('SECRET',str(warning.call_args));self.assertEqual(self.window.last_error,'RuntimeError')
        self.window.start('Otra',lambda:123);settle(self.window);self.assertEqual(self.window.last_result,123)
    def test_failed_collection_refreshes_run_diagnostic(self):
        def failed():
            c=connect(self.path)
            with c:c.execute("INSERT INTO api_runs(started_at,status,error_code) VALUES('2026-10-29T10:00:00Z','failed','authentication_required')")
            c.close();raise RuntimeError('SECRET')
        with patch.object(QMessageBox,'warning'):
            self.window.start('Descarga',failed,refresh_on_error=True);settle(self.window)
        self.assertIn('Incompleta',self.window.run_summary.text())
        self.assertIn('Revisa el acceso guardado',self.window.run_summary.text())
        self.assertEqual(self.window.badge.text(),'Archivo local')
    def test_export_uses_current_dataset_and_filters_and_keeps_all_pages(self):
        self.window.refresh();settle(self.window)
        self.window.datasets.setCurrentIndex(self.window.datasets.findData('glucose'))
        self.window.since.setText('2026-10-29');self.window.until.setText('2026-10-29')
        destination=Path(self.temp.name)/'result.jsonl'
        with patch('tandem.app.QFileDialog.getSaveFileName',return_value=(str(destination),'')):
            self.window.export();settle(self.window)
        self.assertEqual(self.window.last_result['records'],205)
        self.assertEqual(len(destination.read_text(encoding='utf-8').splitlines()),207)
    def test_missing_database_not_created(self):
        missing=Path(self.temp.name)/'missing.sqlite';window=Application(missing,auto_refresh=False)
        window.refresh();settle(window);self.assertFalse(missing.exists());self.assertEqual(window.badge.text(),'Base pendiente');window.close()

if __name__=='__main__':unittest.main()
