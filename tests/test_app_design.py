import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile,unittest
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from tandem.app import Application,TableModel

APP=QApplication.instance() or QApplication([])

class AppDesignTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.w=Application(Path(self.tmp.name)/'missing.sqlite',auto_refresh=False)
    def tearDown(self):self.w.close();self.w.deleteLater();APP.processEvents();self.tmp.cleanup()
    def test_navigation_controls_select_pages_and_remain_accessible_collapsed(self):
        for index,label,_ in self.w.nav_specs:
            if index==1:continue # Chart reads only when explicitly activated.
            self.w.nav_buttons[index].click();self.assertEqual(self.w.tabs.currentIndex(),index)
        self.w.set_navigation_compact(True)
        for index,label,_ in self.w.nav_specs:
            self.assertEqual(self.w.nav_buttons[index].toolTip(),label)
            self.assertEqual(self.w.nav_buttons[index].accessibleName(),label)
        self.assertEqual(self.w.nav.width(),64)
        self.w.toggle_navigation();self.assertEqual(self.w.nav.width(),190)
    def test_status_text_is_readable_without_losing_source_code(self):
        model=TableModel();model.replace([{'status':'failed','error_code':'authentication_required'}])
        status=model.index(0,0);diagnosis=model.index(0,1)
        self.assertEqual(model.data(status),'Incompleta');self.assertEqual(model.data(diagnosis),'Revisa el acceso guardado')
        self.assertEqual(model.data(diagnosis,Qt.ItemDataRole.ToolTipRole),'authentication_required')
        self.assertEqual(model.rows[0]['error_code'],'authentication_required')
    def test_compact_header_leaves_plot_area_without_large_banner(self):
        self.w.resize(1180,820);self.w.show();APP.processEvents()
        self.assertLess(self.w.tabs.geometry().top(),120)
        self.assertTrue(self.w.tabs.tabBar().isHidden())

if __name__=='__main__':unittest.main()
