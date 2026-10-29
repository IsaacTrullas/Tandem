"""Qt desktop application. Workers own database connections; widgets stay on the GUI thread."""
from __future__ import annotations
import argparse,json,sys,os
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from PySide6.QtCore import Qt,QAbstractTableModel,QModelIndex,QThread,Signal,Slot
from PySide6.QtGui import QFont,QCloseEvent,QFontDatabase
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,
    QLabel,QPushButton,QTabWidget,QFrame,QTableView,QHeaderView,QAbstractItemView,QComboBox,
    QLineEdit,QFileDialog,QMessageBox,QProgressBar,QGroupBox,QScrollArea)
from .db import DEFAULT_DB
from .reader import Reader
from .services import import_manifest,load_dashboard
from .timeline_widget import TimelineWidget
from . import __version__

DATASET_NAMES={
 'glucose':'Glucosa · CSV','boluses':'Bolos · CSV','carbohydrates':'Carbohidratos · CSV',
 'api_measurements':'Mediciones de glucosa · API','api_state_transitions':'Cambios de modo · API',
 'api_events':'Todos los eventos · API','states':'Estados del gráfico · PDF','report_fields':'Campos del informe · PDF',
 'source_links':'Coincidencias entre fuentes','api_runs':'Descargas · API','api_snapshots':'Ajustes y bombas · API',
 'records':'Registros originales · CSV','basal_doses':'Basal detallada · CSV','basal_hourly':'Basal horaria · CSV',
 'profiles':'Perfiles · PDF','profile_segments':'Franjas de perfil · PDF','visual_series':'Series gráficas · PDF',
 'quantitative_layers':'Capas del gráfico · PDF','report_metrics':'Resumen del informe · PDF',
 'clock_observations':'Cambios de reloj · CSV'}
HEADERS={'id':'ID','event_id':'Evento','measurement_local_timestamp':'Hora de medición',
 'log_local_timestamp':'Hora de registro','local_timestamp':'Hora de la bomba','local_date':'Fecha',
 'value':'Valor','unit':'Unidad','kind':'Tipo','state':'Modo','action':'Cambio','status':'Estado',
 'started_at':'Inicio (UTC)','finished_at':'Fin (UTC)','error_code':'Diagnóstico',
 'glucose_mg_dl':'Glucosa (mg/dL)','origin':'Origen','review_status':'Revisión','decode_status':'Interpretación'}
STATUS_NAMES={'complete':'Completada','running':'En curso','failed':'Incompleta','interrupted':'Interrumpida'}
STYLE="""
QMainWindow { background:#f3f6fa; }
QWidget { font-family:'Segoe UI'; font-size:10pt; color:#21344a; }
QLabel#title { font-size:24pt; font-weight:700; color:#133b4d; }
QLabel#subtitle,QLabel#muted { color:#62748a; }
QLabel#badge { color:#08766c; background:#dcefeb; border-radius:10px; padding:6px 12px; }
QPushButton { background:white; border:1px solid #ccd6e1; border-radius:7px; padding:9px 15px; font-weight:600; }
QPushButton:hover { background:#eaf1f8; border-color:#9fb3c7; }
QPushButton:disabled { color:#91a0ae; background:#eef1f5; }
QPushButton#primary { background:#107c74; border-color:#107c74; color:white; }
QPushButton#primary:hover { background:#08675f; }
QPushButton#primary:disabled { background:#abc9c5; border-color:#abc9c5; }
QFrame#card { background:white; border:1px solid #dfe6ef; border-radius:10px; }
QLabel#metric { font-size:26pt; font-weight:700; color:#133b4d; }
QTabWidget::pane { border:1px solid #dfe6ef; border-radius:9px; background:white; }
QTabBar::tab { padding:11px 20px; margin-right:5px; color:#607189; border-bottom:3px solid transparent; }
QTabBar::tab:selected { color:#0d766d; border-bottom:3px solid #0d766d; font-weight:600; }
QGroupBox { border:1px solid #dfe6ef; border-radius:9px; margin-top:14px; padding:17px 12px 12px; font-weight:600; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; }
QLineEdit,QComboBox { border:1px solid #ccd6e1; border-radius:5px; padding:7px 9px; background:white; }
QLineEdit:focus,QComboBox:focus { border-color:#107c74; }
QTableView { background:white; alternate-background-color:#f6f9fc; border:1px solid #e2e8ef; gridline-color:#eef2f7; selection-background-color:#dcefeb; selection-color:#163a48; }
QHeaderView::section { background:#edf3f8; border:none; border-bottom:1px solid #d9e2ec; padding:9px; font-weight:600; }
QProgressBar { border:none; background:#dfe8ef; border-radius:3px; max-height:5px; }
QProgressBar::chunk { background:#107c74; border-radius:3px; }
QStatusBar { color:#63758a; background:white; }
"""

def number(value):return f'{value or 0:,}'.replace(',','.')
def ensure_fonts():
    # Qt's offscreen platform does not enumerate Windows fonts. Register the
    # installed system font in process memory for deterministic local renders.
    if not QFontDatabase.families():
        for name in ('segoeui.ttf','segoeuib.ttf'):
            path=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/name
            if path.is_file():QFontDatabase.addApplicationFont(str(path))
def period(value):
    def fmt(s):return str(s).replace('T',' ')[:19] if s else '—'
    return f"{fmt(value.get('first'))}  →  {fmt(value.get('last'))}"
def execution_time(stamp):
    if not stamp:return '—'
    try:
        parsed=datetime.fromisoformat(stamp)
        if parsed.tzinfo:return parsed.astimezone(ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y %H:%M')+' · Madrid'
    except ValueError:pass
    return stamp

class TableModel(QAbstractTableModel):
    def __init__(self,parent=None):super().__init__(parent);self.rows=[];self.columns=[]
    def replace(self,rows):
        self.beginResetModel();self.rows=rows
        keys=list(rows[0]) if rows else []
        priority=('measurement_local_timestamp','local_timestamp','local_date','glucose_mg_dl','value','unit','kind','state','action','origin','log_local_timestamp')
        self.columns=[k for k in priority if k in keys]+[k for k in keys if k not in priority]
        self.endResetModel()
    def rowCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.rows)
    def columnCount(self,parent=QModelIndex()):return 0 if parent.isValid() else len(self.columns)
    def headerData(self,section,orientation,role=Qt.ItemDataRole.DisplayRole):
        if role!=Qt.ItemDataRole.DisplayRole:return None
        return HEADERS.get(self.columns[section],self.columns[section]) if orientation==Qt.Orientation.Horizontal else str(section+1)
    def data(self,index,role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role not in (Qt.ItemDataRole.DisplayRole,Qt.ItemDataRole.ToolTipRole):return None
        v=self.rows[index.row()].get(self.columns[index.column()])
        if v is None:return '—'
        if isinstance(v,bytes):return f'Imagen / archivo · {len(v):,} bytes'
        if isinstance(v,(dict,list)):v=json.dumps(v,ensure_ascii=False)
        text=str(v)
        return text[:2000] if role==Qt.ItemDataRole.ToolTipRole else text[:180]

class Task(QThread):
    succeeded=Signal(object);failed=Signal(str)
    def __init__(self,work,parent=None):super().__init__(parent);self.work=work
    def run(self):
        try:self.succeeded.emit(self.work())
        except Exception as exc:self.failed.emit(type(exc).__name__)
        finally:self.work=None

class Application(QMainWindow):
    PAGE_SIZE=100
    def __init__(self,database=DEFAULT_DB,*,auto_refresh=True):
        super().__init__();ensure_fonts();self.database=Path(database).resolve();self.task=None;self.busy=False
        self.offset=0;self.has_next=False;self.last_result=None;self.last_error=None
        self.setWindowTitle(f'Tandem Local · Qt · {__version__}');self.resize(1180,820);self.setMinimumSize(940,700)
        self.setStyleSheet(STYLE)
        body=QWidget();self.setCentralWidget(body);layout=QVBoxLayout(body);layout.setContentsMargins(28,24,28,16);layout.setSpacing(16)
        header=QHBoxLayout();titles=QVBoxLayout()
        title=QLabel('Tandem Local');title.setObjectName('title');titles.addWidget(title)
        sub=QLabel('Tu archivo de datos de glucosa y bomba');sub.setObjectName('subtitle');titles.addWidget(sub)
        header.addLayout(titles);header.addStretch()
        self.badge=QLabel('Archivo local');self.badge.setObjectName('badge');header.addWidget(self.badge);layout.addLayout(header)
        actions=QHBoxLayout()
        self.collect_button=QPushButton('Recopilar API');self.collect_button.setObjectName('primary');self.collect_button.clicked.connect(self.collect)
        self.import_button=QPushButton('Importar CSV/PDF');self.import_button.clicked.connect(self.manifest)
        self.credentials_button=QPushButton('Configurar acceso');self.credentials_button.clicked.connect(self.credentials)
        self.refresh_button=QPushButton('Actualizar vista');self.refresh_button.clicked.connect(self.refresh)
        for button in (self.collect_button,self.import_button,self.credentials_button,self.refresh_button):actions.addWidget(button)
        actions.addStretch();layout.addLayout(actions)
        self.phase=QLabel('Preparado');self.phase.setObjectName('muted');layout.addWidget(self.phase)
        self.progress=QProgressBar();self.progress.setTextVisible(False);self.progress.setRange(0,1);self.progress.setValue(0);layout.addWidget(self.progress)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self._overview();self.timeline=TimelineWidget(self.database);self.tabs.addTab(self.timeline,'Gráfico');self._data_tab();self._runs_tab();self.statusBar().showMessage(str(self.database))
        self.tabs.currentChanged.connect(self._tab_changed)
        self._actions=[self.collect_button,self.import_button,self.credentials_button,self.refresh_button,self.preview_button,self.export_button,self.previous_button,self.next_button,self.datasets,self.since,self.until]
        if auto_refresh:self.refresh()

    def _overview(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(22,22,22,22);v.setSpacing(18)
        grid=QGridLayout();self.metrics={}
        for i,(key,label) in enumerate((('api_events','Eventos API'),('records','Registros CSV'),('pdf_pages','Páginas PDF'),('source_links','Enlaces entre fuentes'))):
            card=QFrame();card.setObjectName('card');box=QVBoxLayout(card);box.setContentsMargins(18,17,18,17)
            caption=QLabel(label);caption.setObjectName('muted');value=QLabel('—');value.setObjectName('metric')
            box.addWidget(caption);box.addWidget(value);grid.addWidget(card,0,i);self.metrics[key]=value
        v.addLayout(grid)
        coverage=QGroupBox('Cobertura de las fuentes');fields=QVBoxLayout(coverage);self.api_range=QLabel('API · Pendiente de consultar');self.csv_range=QLabel('CSV · Pendiente de consultar')
        for w in (self.api_range,self.csv_range):w.setWordWrap(True);fields.addWidget(w)
        note=QLabel('Horas según el reloj de la bomba. Los formatos pueden tener fechas de actualización distintas.');note.setWordWrap(True);note.setObjectName('muted');fields.addWidget(note);v.addWidget(coverage)
        state=QGroupBox('Última recopilación');state_box=QVBoxLayout(state)
        self.run_summary=QLabel('Sin ejecuciones consultadas');self.run_summary.setWordWrap(True);state_box.addWidget(self.run_summary)
        self.unknown_label=QLabel('');self.unknown_label.setWordWrap(True);self.unknown_label.setObjectName('muted');state_box.addWidget(self.unknown_label)
        self.review_label=QLabel('');self.review_label.setObjectName('muted');state_box.addWidget(self.review_label);v.addWidget(state)
        coverage.setMinimumHeight(125);state.setMinimumHeight(145)
        v.addStretch();scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(page);self.tabs.addTab(scroll,'Resumen')

    def _data_tab(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(20,20,20,20)
        filters=QHBoxLayout();self.datasets=QComboBox();self.datasets.setMinimumWidth(225);filters.addWidget(self.datasets,1)
        self.since=QLineEdit();self.since.setPlaceholderText('Desde · AAAA-MM-DD');self.since.setMaximumWidth(175)
        self.until=QLineEdit();self.until.setPlaceholderText('Hasta · AAAA-MM-DD');self.until.setMaximumWidth(175)
        filters.addWidget(self.since);filters.addWidget(self.until)
        self.preview_button=QPushButton('Ver datos');self.preview_button.clicked.connect(self.preview)
        self.export_button=QPushButton('Exportar JSONL');self.export_button.clicked.connect(self.export)
        filters.addWidget(self.preview_button);filters.addWidget(self.export_button);v.addLayout(filters)
        self.table,self.model=self._table();v.addWidget(self.table,1)
        pagination=QHBoxLayout();self.previous_button=QPushButton('Anterior');self.next_button=QPushButton('Siguiente')
        self.previous_button.clicked.connect(lambda:self.preview_page(max(0,self.offset-self.PAGE_SIZE)))
        self.next_button.clicked.connect(lambda:self.preview_page(self.offset+self.PAGE_SIZE))
        self.page_label=QLabel('Selecciona una fuente y pulsa «Ver datos».');pagination.addWidget(self.page_label);pagination.addStretch();pagination.addWidget(self.previous_button);pagination.addWidget(self.next_button);v.addLayout(pagination)
        self.previous_button.setEnabled(False);self.next_button.setEnabled(False)
        self.datasets.currentIndexChanged.connect(self.clear_preview);self.since.textChanged.connect(self.clear_preview);self.until.textChanged.connect(self.clear_preview)
        self.tabs.addTab(page,'Datos y exportación')

    def _runs_tab(self):
        page=QWidget();v=QVBoxLayout(page);v.setContentsMargins(20,20,20,20)
        v.addWidget(QLabel('Historial de las últimas 100 ejecuciones. Los intentos incompletos también se conservan.'))
        self.runs_table,self.runs_model=self._table();v.addWidget(self.runs_table,1);self.tabs.addTab(page,'Ejecuciones')

    def _table(self):
        table=QTableView();model=TableModel(table);table.setModel(model);table.setAlternatingRowColors(True);table.setWordWrap(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive);table.horizontalHeader().setDefaultSectionSize(165)
        table.verticalHeader().setDefaultSectionSize(34);return table,model

    def set_busy(self,busy):
        self.busy=busy
        for action in self._actions:action.setEnabled(not busy)
        self.progress.setRange(0,0 if busy else 1)
        if not busy:
            self.progress.setValue(0);self.previous_button.setEnabled(self.offset>0);self.next_button.setEnabled(self.has_next)

    def start(self,title,work,callback=None,*,refresh_on_error=False):
        if self.busy:return False
        self.set_busy(True);self.phase.setText(title);self.last_error=None;self.last_result=None
        self.task=Task(work,self);self._success_callback=callback;self._refresh_on_error=refresh_on_error
        self.task.succeeded.connect(self._succeeded);self.task.failed.connect(self._failed);self.task.finished.connect(self._finished);self.task.start();return True
    @Slot(object)
    def _succeeded(self,result):self.last_result=result
    @Slot(str)
    def _failed(self,error):self.last_error=error
    @Slot()
    def _finished(self):
        task=self.task;self.task=None;self.set_busy(False)
        if self.last_error:
            error=self.last_error
            self.phase.setText('Operación incompleta · '+self.last_error)
            QMessageBox.warning(self,'Operación incompleta','No se ha completado la operación. Comprueba el acceso, las fechas y el diagnóstico de la última ejecución.\n\nCódigo: '+self.last_error)
            if self._refresh_on_error:
                def refreshed(data):
                    self.show_dashboard(data);self.last_error=error;self.phase.setText('Operación incompleta · '+error)
                self.start('Actualizando el diagnóstico local…',lambda:load_dashboard(self.database),refreshed)
        else:
            self.phase.setText('Operación finalizada')
            if self._success_callback:self._success_callback(self.last_result)
        task.deleteLater()

    def refresh(self):return self.start('Consultando el archivo local…',lambda:load_dashboard(self.database),self.show_dashboard)
    def _tab_changed(self,index):
        if self.tabs.widget(index) is self.timeline:self.timeline.activate()
    def show_dashboard(self,data):
        self.dashboard=data
        if data.get('status')=='missing':
            self.badge.setText('Base pendiente');self.run_summary.setText('Configura el acceso y recopila datos, o importa los archivos oficiales.');return
        for key,widget in self.metrics.items():widget.setText(number(data['counts'].get(key)))
        self.api_range.setText('API   '+period(data['api_range']));self.csv_range.setText('CSV   '+period(data['csv_range']))
        run=data.get('last_run');status=run.get('status') if run else None
        self.badge.setText('Última descarga correcta' if status=='complete' else 'Archivo local')
        self.run_summary.setText((STATUS_NAMES.get(status,status or 'Sin descargas')+' · '+execution_time(run.get('finished_at') or run.get('started_at'))+((' · '+run['error_code']) if run.get('error_code') else '')) if run else 'Todavía no se ha realizado una descarga API.')
        self.unknown_label.setText(number(data['unknown_count'])+' eventos conservados sin interpretar. Sus datos originales siguen disponibles.')
        self.review_label.setText(number(data['pending_review'])+' evidencias pendientes de revisión.')
        selected=self.datasets.currentData();self.datasets.blockSignals(True);self.datasets.clear()
        for name in data['datasets']:self.datasets.addItem(DATASET_NAMES.get(name,name),name)
        if selected:self.datasets.setCurrentIndex(max(0,self.datasets.findData(selected)))
        self.datasets.blockSignals(False)
        self.runs_model.replace([{k:r.get(k) for k in ('id','status','started_at','finished_at','error_code')} for r in data['runs']])

    def credentials(self):
        if self.busy:return
        from .credentials import configure_interactive
        try:saved=configure_interactive(self)
        except Exception as exc:
            QMessageBox.warning(self,'Acceso','No se ha podido abrir el acceso guardado ('+type(exc).__name__+').');return
        self.phase.setText('Acceso guardado. La conexión se comprobará al recopilar.' if saved else 'Configuración cancelada.')
    def collect(self):
        from .credentials import has_credentials
        from .collector import collect
        try:available=has_credentials()
        except Exception:available=False
        if not available:
            QMessageBox.information(self,'Acceso pendiente','Configura primero el acceso de Tandem Source Europa.');return
        self.start('Recopilando datos y cruzando fuentes…',lambda:collect(self.database),self.after_update,refresh_on_error=True)
    def after_update(self,result):self.timeline.reload();self.refresh()
    def manifest(self):
        path,_=QFileDialog.getOpenFileName(self,'Manifiesto de descarga CSV y PDF','','Manifiesto JSON (*.json)')
        if path:self.start('Importando archivos y verificando los informes…',lambda:import_manifest(self.database,path),self.after_update,refresh_on_error=True)
    def clear_preview(self,*_):
        self.offset=0;self.has_next=False;self.model.replace([]);self.page_label.setText('Pulsa «Ver datos» para consultar esta selección.')
        self.previous_button.setEnabled(False);self.next_button.setEnabled(False)
    def preview(self):return self.preview_page(0)
    def preview_page(self,offset):
        dataset=self.datasets.currentData()
        if not dataset or self.busy:return False
        since,until=self.since.text().strip() or None,self.until.text().strip() or None
        def work():
            with Reader(self.database) as reader:return {'rows':reader.rows(dataset,since=since,until=until,limit=self.PAGE_SIZE+1,offset=offset),'offset':offset}
        return self.start('Consultando datos…',work,self.show_page)
    def show_page(self,result):
        rows=result['rows'];self.offset=result['offset'];self.has_next=len(rows)>self.PAGE_SIZE;shown=rows[:self.PAGE_SIZE];self.model.replace(shown)
        self.page_label.setText(f'Filas {self.offset+1}–{self.offset+len(shown)}' if shown else 'No hay datos con esta selección.')
        self.previous_button.setEnabled(self.offset>0);self.next_button.setEnabled(self.has_next)
    def export(self):
        dataset=self.datasets.currentData()
        if not dataset or self.busy:return
        path,_=QFileDialog.getSaveFileName(self,'Crear exportación completa',dataset+'.jsonl','JSON Lines (*.jsonl)')
        if not path:return
        since,until=self.since.text().strip() or None,self.until.text().strip() or None
        def work():
            with Reader(self.database) as reader:return reader.export_jsonl(dataset,path,since=since,until=until)
        self.start('Exportando todos los registros seleccionados…',work,lambda r:self.phase.setText('Exportación guardada · '+number(r['records'])+' registros'))
    def closeEvent(self,event:QCloseEvent):
        if self.busy or self.timeline.busy:
            QMessageBox.information(self,'Operación en curso','Espera a que termine la operación antes de cerrar.');event.ignore()
        else:event.accept()

def launch(dbpath=DEFAULT_DB):
    app=QApplication.instance() or QApplication(sys.argv[:1]);app.setApplicationName('Tandem Local');app.setOrganizationName('TandemLocal');app.setStyle('Fusion');app.setFont(QFont('Segoe UI',10))
    window=Application(dbpath)
    screen=app.primaryScreen()
    if screen:
        area=screen.availableGeometry();window.resize(min(1440,max(940,area.width()-60)),min(1020,max(700,area.height()-70)))
    window.show();window.tabs.setCurrentWidget(window.timeline);return app.exec()
def main(argv=None):
    parser=argparse.ArgumentParser(description='Tandem Local · Qt');parser.add_argument('--db',type=Path,default=DEFAULT_DB);return launch(parser.parse_args(argv).db)
if __name__=='__main__':raise SystemExit(main())
