"""Synthetic Qt form tests: no real credential store is read or written."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QTimer, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit
from tandem.credentials import CredentialDialog, configure_interactive


class QtCredentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = CredentialDialog()
        self.dialog.email_entry.setText('synthetic@example.invalid')
        self.dialog.password_entry.setText('Synthetic-test-only')

    def tearDown(self):
        self.dialog.reject()
        self.dialog.deleteLater()
        self.app.processEvents()

    def test_toggle_keeps_text_and_starts_hidden(self):
        field = self.dialog.password_entry
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
        self.assertFalse(self.dialog.reveal.isChecked())
        self.dialog.reveal.setChecked(True)
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
        self.assertEqual(field.text(), 'Synthetic-test-only')
        self.dialog.reveal.setChecked(False)
        self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
        self.assertEqual(field.text(), 'Synthetic-test-only')

    def test_success_saves_exact_input_and_clears_secret(self):
        self.dialog.reveal.setChecked(True)
        with patch('tandem.credentials.save_credentials') as save:
            self.dialog.submit()
        save.assert_called_once_with('synthetic@example.invalid', 'Synthetic-test-only')
        self.assertTrue(self.dialog.saved)
        self.assertEqual(self.dialog.result(), QDialog.DialogCode.Accepted)
        self.assertEqual(self.dialog.password_entry.text(), '')
        self.assertFalse(self.dialog.reveal.isChecked())

    def test_cancel_does_not_save_and_clears_secret(self):
        with patch('tandem.credentials.save_credentials') as save:
            self.dialog.reject()
        save.assert_not_called()
        self.assertFalse(self.dialog.saved)
        self.assertEqual(self.dialog.password_entry.text(), '')
        self.assertEqual(self.dialog.result(), QDialog.DialogCode.Rejected)

    def test_error_keeps_input_and_never_displays_exception(self):
        with patch('tandem.credentials.save_credentials', side_effect=RuntimeError('SENSITIVE-EXCEPTION')), \
             patch('PySide6.QtWidgets.QMessageBox.warning') as warning:
            self.dialog.submit()
        self.assertFalse(self.dialog.saved)
        self.assertEqual(self.dialog.password_entry.text(), 'Synthetic-test-only')
        self.assertNotIn('SENSITIVE-EXCEPTION', str(warning.call_args))
        self.assertNotIn('Synthetic-test-only', str(warning.call_args))

    def test_escape_clears_password(self):
        self.dialog.show()
        self.app.processEvents()
        QTest.keyClick(self.dialog, Qt.Key.Key_Escape)
        self.assertEqual(self.dialog.password_entry.text(), '')
        self.assertFalse(self.dialog.saved)

    def test_modal_wrapper_uses_existing_qapplication_and_returns_saved(self):
        def submit_active():
            active = self.app.activeModalWidget()
            active.email_entry.setText('synthetic@example.invalid')
            active.password_entry.setText('Synthetic-test-only')
            active.submit()
        with patch('tandem.credentials.save_credentials') as save:
            QTimer.singleShot(0, submit_active)
            result = configure_interactive()
        self.assertTrue(result)
        save.assert_called_once_with('synthetic@example.invalid', 'Synthetic-test-only')

    def test_does_not_prefill_or_read_saved_password(self):
        with patch('tandem.credentials.load_credentials') as load:
            empty = CredentialDialog()
        load.assert_not_called()
        self.assertEqual(empty.email_entry.text(), '')
        self.assertEqual(empty.password_entry.text(), '')
        empty.reject()
        empty.deleteLater()


if __name__ == '__main__':
    unittest.main()
