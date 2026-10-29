"""Credentials in Windows Credential Manager, scoped to the current Windows user.

No passwords, cookies or tokens are written to application files. Python string
objects cannot be reliably wiped; secrets live in process memory while in use.
"""
from __future__ import annotations
import ctypes
import getpass
import os
from ctypes import wintypes

TARGET = 'TandemLocal:EU'
CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2  # Survives logon; accessible only to the same user.
ERROR_NOT_FOUND = 1168

class CredentialError(RuntimeError):
    pass

class CREDENTIALW(ctypes.Structure):
    _fields_ = [('Flags',wintypes.DWORD),('Type',wintypes.DWORD),('TargetName',wintypes.LPWSTR),
        ('Comment',wintypes.LPWSTR),('LastWritten',wintypes.FILETIME),('CredentialBlobSize',wintypes.DWORD),
        ('CredentialBlob',ctypes.POINTER(ctypes.c_ubyte)),('Persist',wintypes.DWORD),
        ('AttributeCount',wintypes.DWORD),('Attributes',ctypes.c_void_p),
        ('TargetAlias',wintypes.LPWSTR),('UserName',wintypes.LPWSTR)]


def _api():
    if os.name != 'nt':
        raise CredentialError('El almacenamiento seguro requiere Windows Credential Manager')
    api = ctypes.WinDLL('Advapi32.dll', use_last_error=True)
    api.CredReadW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.POINTER(ctypes.POINTER(CREDENTIALW))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW),wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api


def load_credentials():
    api = _api()
    pointer = ctypes.POINTER(CREDENTIALW)()
    if not api.CredReadW(TARGET,CRED_TYPE_GENERIC,0,ctypes.byref(pointer)):
        if ctypes.get_last_error() == ERROR_NOT_FOUND: return None
        raise CredentialError('No se pudo acceder al almacén seguro de Windows')
    try:
        credential = pointer.contents
        if credential.CredentialBlobSize > 2560 or credential.CredentialBlobSize % 2:
            raise CredentialError('Formato de credenciales no válido; vuelva a configurarlas')
        email = credential.UserName
        password = ctypes.string_at(credential.CredentialBlob,credential.CredentialBlobSize).decode('utf-16-le')
        if not email or not password:
            raise CredentialError('Credenciales incompletas; vuelva a configurarlas')
        return email,password
    finally:
        if pointer:
            if pointer.contents.CredentialBlob:
                ctypes.memset(pointer.contents.CredentialBlob,0,pointer.contents.CredentialBlobSize)
            api.CredFree(pointer)


def save_credentials(email,password):
    email = str(email).strip()
    if not email or '@' not in email or not password or '\0' in email or '\0' in password:
        raise CredentialError('Introduzca un correo y una contraseña válidos')
    raw = password.encode('utf-16-le')
    if len(raw) > 2560:
        raise CredentialError('La contraseña supera el tamaño permitido por Windows')
    api = _api()
    buffer = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
    credential = CREDENTIALW(Type=CRED_TYPE_GENERIC,TargetName=TARGET,
        Comment='Acceso de lectura a Tandem Source Europa',CredentialBlobSize=len(raw),
        CredentialBlob=ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)),
        Persist=CRED_PERSIST_LOCAL_MACHINE,UserName=email)
    try:
        if not api.CredWriteW(ctypes.byref(credential),0):
            raise CredentialError('Windows no pudo guardar las credenciales')
    finally:
        ctypes.memset(buffer,0,len(raw))


def delete_credentials():
    api = _api()
    if not api.CredDeleteW(TARGET,CRED_TYPE_GENERIC,0) and ctypes.get_last_error()!=ERROR_NOT_FOUND:
        raise CredentialError('Windows no pudo retirar las credenciales guardadas')


def has_credentials():
    return load_credentials() is not None


def configure_credentials(gui=False):
    if gui: return configure_interactive()
    email = input('Correo de Tandem Source EU: ').strip()
    password = getpass.getpass('Contraseña (no se muestra): ')
    save_credentials(email,password)
    return True


def _dialog_class():
    """Load Qt only when the graphical credential form is used."""
    from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox,
        QFormLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout)

    class CredentialDialog(QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.saved = False
            self.setWindowTitle('Acceso a Tandem Source Europa')
            self.setMinimumWidth(430)
            self.setModal(True)
            layout = QVBoxLayout(self)
            layout.setContentsMargins(24, 24, 24, 24)
            layout.setSpacing(16)
            title = QLabel('Acceso a Tandem Source', self)
            title.setObjectName('dialogTitle')
            layout.addWidget(title)
            description = QLabel('El acceso se guarda en el almacén seguro de Windows.', self)
            description.setWordWrap(True)
            layout.addWidget(description)
            form = QFormLayout()
            form.setSpacing(12)
            self.email_entry = QLineEdit(self)
            self.email_entry.setObjectName('credentialEmail')
            self.email_entry.setPlaceholderText('Correo de la cuenta')
            self.password_entry = QLineEdit(self)
            self.password_entry.setObjectName('credentialPassword')
            self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)
            self.password_entry.setMaxLength(1280)
            form.addRow('Correo', self.email_entry)
            form.addRow('Contraseña', self.password_entry)
            layout.addLayout(form)
            self.reveal = QCheckBox('Mostrar contraseña', self)
            self.reveal.setObjectName('revealPassword')
            self.reveal.toggled.connect(self._toggle_password)
            layout.addWidget(self.reveal)
            self.buttons = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel,
                parent=self)
            self.buttons.button(QDialogButtonBox.StandardButton.Save).setText('Guardar acceso')
            self.buttons.button(QDialogButtonBox.StandardButton.Save).setObjectName('primaryButton')
            self.buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
            self.buttons.accepted.connect(self.submit)
            self.buttons.rejected.connect(self.reject)
            layout.addWidget(self.buttons)
            self.email_entry.setFocus()

        def _toggle_password(self, visible):
            self.password_entry.setEchoMode(
                QLineEdit.EchoMode.Normal if visible else QLineEdit.EchoMode.Password)

        def submit(self):
            try:
                save_credentials(self.email_entry.text(), self.password_entry.text())
            except Exception:
                # Backend exceptions may include input in future implementations.
                # Keep the fields for correction, but show only a fixed message.
                QMessageBox.warning(self, 'No se ha guardado',
                    'No se pudo guardar el acceso. Comprueba el correo, la contraseña '
                    'y el acceso al almacén seguro de Windows.')
                return
            self.saved = True
            self.accept()

        def done(self, result):
            # Covers save, Cancel, Escape and the window close button.
            self.password_entry.clear()
            self.reveal.setChecked(False)
            super().done(result)

    return CredentialDialog


def __getattr__(name):
    if name == 'CredentialDialog':
        dialog = _dialog_class()
        globals()[name] = dialog
        return dialog
    raise AttributeError(name)


def configure_interactive(parent=None):
    """Qt modal form; call from the application's main thread."""
    from PySide6.QtWidgets import QApplication, QDialog
    global _qt_application
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        _qt_application = app  # Keep the application alive for standalone usage.
    elif not isinstance(app, QApplication):
        raise CredentialError('La aplicación gráfica de Qt no está disponible')
    dialog_type = globals().get('CredentialDialog') or __getattr__('CredentialDialog')
    dialog = dialog_type(parent)
    return dialog.exec() == QDialog.DialogCode.Accepted and dialog.saved
