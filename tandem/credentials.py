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


def configure_interactive(parent=None):
    """Modal dialog; call from the Tk main thread. Returns whether saved."""
    import tkinter as tk
    from tkinter import ttk,messagebox
    own_root = parent is None
    root = tk.Tk() if own_root else parent
    if own_root: root.withdraw()
    dialog = tk.Toplevel(root)
    dialog.title('Acceso a Tandem Source Europa')
    dialog.resizable(False,False)
    if not own_root: dialog.transient(root)
    panel = ttk.Frame(dialog,padding=20);panel.grid()
    ttk.Label(panel,text='Guardar acceso en el almacén seguro de Windows').grid(row=0,column=0,columnspan=2,pady=(0,14))
    ttk.Label(panel,text='Correo').grid(row=1,column=0,sticky='w',padx=(0,10))
    email = ttk.Entry(panel,width=42);email.grid(row=1,column=1,pady=5)
    ttk.Label(panel,text='Contraseña').grid(row=2,column=0,sticky='w',padx=(0,10))
    password = ttk.Entry(panel,width=42,show='•');password.grid(row=2,column=1,pady=5)
    saved = [False]
    def close():
        password.delete(0,tk.END)
        dialog.destroy()
    def submit():
        try:save_credentials(email.get(),password.get())
        except CredentialError as exc:
            messagebox.showerror('No se ha guardado',str(exc),parent=dialog);return
        saved[0] = True
        close()
    ttk.Button(panel,text='Cancelar',command=close).grid(row=3,column=0,pady=(15,0))
    ttk.Button(panel,text='Guardar acceso',command=submit).grid(row=3,column=1,sticky='e',pady=(15,0))
    dialog.protocol('WM_DELETE_WINDOW',close)
    email.focus_set();dialog.grab_set();root.wait_window(dialog)
    if own_root:root.destroy()
    return saved[0]
