"""Local desktop control panel. All Tk calls stay on the main thread."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .db import DEFAULT_DB
from .reader import Reader


def import_manifest(database, manifest):
    from .collector import writer_lock
    with writer_lock(database):
        return _import_manifest(database, manifest)


def _import_manifest(database, manifest):
    from .db import backup, connect
    from .sync import accept_downloads
    from .pdf import run_ocr
    from .visual import expand
    from .cli import status
    from .collector import reconcile, audit_api
    database = Path(database)
    conn = connect(database)
    try:
        loaded = accept_downloads(conn, manifest, database.parent / 'archive', database.parent / 'backups')
        ocr = run_ocr(conn)
        visual = expand(conn)
        reconcile(conn)
        report = status(conn, True)
        report['api_audit'] = audit_api(conn)
        failures = {k: v for k, v in report.items() if
                    ('error' in k or 'missing' in k or 'unmatched' in k or 'unscaled' in k or
                     'conflicts' in k or 'unexpanded' in k or k in ('raw_rows_without_record', 'quarantined_files')) and v}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        audit = database.parent / 'auditorias' / ('app_' + stamp + '.json')
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        api_failures = any(report['api_audit'].get(k) for k in ('payload_hash_errors', 'event_hash_errors', 'events_without_source'))
        if report.get('integrity_check') != 'ok' or failures or visual.get('errors') or ocr.get('errors') or api_failures:
            raise RuntimeError('La importación requiere revisión de la auditoría')
        final = backup(conn, database.parent / 'backups' / ('app_' + stamp + '.sqlite'))
        return {'windows': loaded['windows'], 'new_raw_rows': loaded['new_raw_rows'],
                'audit': str(audit), 'backup': final, 'status': 'complete'}
    finally:
        conn.close()


class Application:
    def __init__(self, root, database):
        self.root, self.database = root, Path(database).resolve()
        self.busy = False
        self.messages = queue.Queue()
        self.actions = []
        root.title('Tandem Local · Archivo de datos')
        root.geometry('980x730')
        root.minsize(800, 590)
        root.protocol('WM_DELETE_WINDOW', self.close)
        style = ttk.Style(root)
        style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'))
        style.configure('TButton', padding=(10, 7))
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text='Tandem Local', style='Title.TLabel').pack(anchor='w')
        ttk.Label(frame, text='Recopilación, cruce de fuentes y acceso para otros programas').pack(anchor='w', pady=(3, 14))
        self.database_label = ttk.Label(frame, text=str(self.database), foreground='#536171')
        self.database_label.pack(anchor='w', pady=(0, 14))
        bar = ttk.Frame(frame)
        bar.pack(fill='x')
        for title, command in [('Configurar acceso', self.credentials), ('Recopilar API', self.collect),
                               ('Importar CSV/PDF', self.manifest), ('Actualizar vista', self.refresh)]:
            button = ttk.Button(bar, text=title, command=command)
            button.pack(side='left', padx=(0, 8))
            self.actions.append(button)
        self.phase = tk.StringVar(value='Preparado')
        ttk.Label(frame, textvariable=self.phase).pack(anchor='w', pady=(14, 4))
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(fill='x')
        self.summary = tk.Text(frame, height=12, wrap='word', font=('Segoe UI', 10),
                               relief='flat', padx=10, pady=10, state='disabled')
        self.summary.pack(fill='both', expand=True, pady=(12, 8))
        export = ttk.LabelFrame(frame, text='Exportar para otro programa', padding=12)
        export.pack(fill='x', pady=(4, 8))
        self.dataset = tk.StringVar()
        self.datasets = ttk.Combobox(export, textvariable=self.dataset, state='readonly', width=23)
        self.datasets.grid(row=0, column=0, padx=(0, 12), sticky='w')
        ttk.Label(export, text='Desde (opcional)').grid(row=0, column=1, sticky='w')
        self.since = ttk.Entry(export, width=13)
        self.since.grid(row=0, column=2, padx=(5, 12))
        ttk.Label(export, text='Hasta').grid(row=0, column=3, sticky='w')
        self.until = ttk.Entry(export, width=13)
        self.until.grid(row=0, column=4, padx=(5, 12))
        button = ttk.Button(export, text='Guardar JSONL', command=self.export)
        button.grid(row=0, column=5, sticky='e')
        self.actions.append(button)
        ttk.Label(export, text='Fechas: AAAA-MM-DD. Sin fechas se exporta todo el conjunto. Se conservan procedencia y revisión.',
                  foreground='#536171').grid(row=1, column=0, columnspan=6, sticky='w', pady=(8, 0))
        ttk.Label(frame, text='Los datos gráficos son evidencia revisable. Las fuentes solapadas no son dosis adicionales.',
                  foreground='#536171', wraplength=900).pack(anchor='w')
        self.refresh()
        root.after(150, self.poll)

    def show_summary(self, text):
        self.summary.configure(state='normal')
        self.summary.delete('1.0', 'end')
        self.summary.insert('1.0', text)
        self.summary.configure(state='disabled')

    def refresh(self):
        if not self.database.exists():
            self.show_summary('Base todavía no creada. Configure el acceso y recopile los datos, o importe un manifiesto de archivos oficiales.')
            return
        try:
            with Reader(self.database) as reader:
                names = reader.datasets()
                self.datasets['values'] = names
                if self.dataset.get() not in names and names:
                    self.dataset.set(names[0])
                conn = reader._conn
                tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
                lines = []
                if 'records' in tables:
                    row = conn.execute('SELECT count(*),min(local_timestamp),max(local_timestamp) FROM records').fetchone()
                    lines += [f'Registros CSV: {row[0]:,}', f'Rango del reloj de la bomba: {row[1] or "—"} → {row[2] or "—"}']
                for table, label in [('pdf_pages', 'Páginas PDF'), ('api_events', 'Eventos API'),
                                     ('api_snapshots', 'Respuestas originales API'), ('source_links', 'Enlaces entre fuentes')]:
                    if table in tables:
                        lines.append(f'{label}: {conn.execute("SELECT count(*) FROM " + table).fetchone()[0]:,}')
                if 'api_events' in tables:
                    row = conn.execute('SELECT min(local_timestamp),max(local_timestamp) FROM api_events').fetchone()
                    lines.append(f'Rango API del reloj de la bomba: {row[0] or "—"} → {row[1] or "—"}')
                    unknown = conn.execute("SELECT count(*) FROM api_events WHERE decode_status NOT IN ('decoded','classified')").fetchone()[0]
                    lines.append(f'Eventos API conservados sin interpretar: {unknown:,}')
                if 'v_pending_review' in tables:
                    lines.append(f'Evidencias pendientes de revisión: {conn.execute("SELECT count(*) FROM v_pending_review").fetchone()[0]:,}')
                if 'api_runs' in tables:
                    run = conn.execute('SELECT * FROM api_runs ORDER BY id DESC LIMIT 1').fetchone()
                    if run:
                        run = dict(run)
                        lines.append('Última ejecución API: ' + str(run.get('status', 'sin estado')))
                        lines.append('Inicio de ejecución: ' + str(run.get('started_at', '—')))
                        if run.get('error_code'):
                            lines.append('Diagnóstico de ejecución: ' + str(run['error_code']))
                    else:
                        lines.append('API: pendiente de primera conexión y descarga verificadas.')
                else:
                    lines.append('API: pendiente de inicialización.')
                lines += ['', 'Los cortes de CSV/PDF y API se comprueban por separado. Un rango de fechas no garantiza ausencia de huecos.']
                self.show_summary('\n'.join(lines))
        except (sqlite3.Error, ValueError, OSError):
            self.show_summary('No se ha podido leer la base. Compruebe que existe y corresponde a esta aplicación.')

    def credentials(self):
        if self.busy:
            return
        try:
            from .credentials import configure_interactive
            saved = configure_interactive(parent=self.root)
            self.phase.set('Acceso guardado; la conexión se comprobará al recopilar.' if saved else 'Configuración cancelada.')
        except Exception as exc:
            messagebox.showerror('Acceso', 'No se ha podido guardar el acceso (' + type(exc).__name__ + ').', parent=self.root)

    def start(self, title, work):
        if self.busy:
            return
        self.busy = True
        for action in self.actions:
            action.configure(state='disabled')
        self.phase.set(title)
        self.progress.start(15)
        def run():
            try:
                self.messages.put(('done', work()))
            except Exception as exc:
                # An arbitrary transport exception can contain headers or body.
                # Display only the class; API details live in the sanitized run log.
                self.messages.put(('error', type(exc).__name__))
        threading.Thread(target=run, name='tandem-local-worker', daemon=False).start()

    def collect(self):
        try:
            from .credentials import has_credentials
            if not has_credentials():
                messagebox.showinfo('Acceso pendiente', 'Use «Configurar acceso» para guardar las credenciales en Windows antes de recopilar.', parent=self.root)
                return
        except Exception as exc:
            messagebox.showerror('Acceso', 'No se ha podido consultar el acceso guardado (' + type(exc).__name__ + ').', parent=self.root)
            return
        def work():
            from .collector import collect
            return collect(self.database)
        self.start('Recopilando API y cruzando fuentes…', work)

    def manifest(self):
        path = filedialog.askopenfilename(parent=self.root, title='Manifiesto de descarga CSV + PDF',
                                          filetypes=[('Manifiesto JSON', '*.json')])
        if path:
            self.start('Importando archivos, extrayendo PDF y verificando…', lambda: import_manifest(self.database, path))

    def export(self):
        dataset, since, until = self.dataset.get(), self.since.get().strip() or None, self.until.get().strip() or None
        if not dataset:
            return
        path = filedialog.asksaveasfilename(parent=self.root, title='Crear exportación JSONL', defaultextension='.jsonl',
                                           initialfile=dataset + '.jsonl', filetypes=[('JSON Lines', '*.jsonl')])
        if not path:
            return
        def work():
            with Reader(self.database) as reader:
                return reader.export_jsonl(dataset, path, since=since, until=until)
        self.start('Exportando una copia coherente de los datos…', work)

    def poll(self):
        try:
            kind, result = self.messages.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            self.progress.stop()
            for action in self.actions:
                action.configure(state='normal')
            if kind == 'error':
                self.phase.set('Operación incompleta: ' + result)
                messagebox.showerror('Operación incompleta',
                    'La operación no ha terminado (' + result + '). Los originales recibidos se conservan. '
                    'Compruebe el estado de las ejecuciones y el acceso antes de reintentar.', parent=self.root)
            else:
                status = result.get('status', 'complete') if isinstance(result, dict) else 'complete'
                self.phase.set('Operación finalizada: ' + str(status))
            self.refresh()
        self.root.after(150, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Operación en curso', 'Espere a que termine la operación antes de cerrar la aplicación.', parent=self.root)
            return
        self.root.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description='Aplicación local de archivo Tandem')
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    launch(args.db)


def launch(dbpath=DEFAULT_DB):
    root = tk.Tk()
    Application(root, dbpath)
    root.mainloop()


if __name__ == '__main__':
    main()
