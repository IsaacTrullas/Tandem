"""Bounded-window Qt timeline. Only the displayed window and a small margin are retained."""
from __future__ import annotations
from bisect import bisect_left,bisect_right
from datetime import datetime,timedelta
from html import escape
import math,json
import pyqtgraph as pg
from PySide6.QtCore import Qt,QDate,QTimer,QThread,Signal,Slot,QSize,QRect,QPoint,QLocale,QRectF,QPointF,QEvent
from PySide6.QtGui import QFont,QFontMetrics
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,QPushButton,QDateEdit,
    QComboBox,QSplitter,QScrollArea,QGroupBox,QFormLayout,QProgressBar,QFrame,QToolButton,QLayout,QSizePolicy,QApplication)
from .timeline_data import load_timeline,timeline_bounds
from .pump_context import load_context,context_at
from .plot_symbols import symbol,icon,COLORS
from .mode_segments import derive_mode_segments
from .event_guides import collect_event_times,place_event_labels,EventGuideItem,GUIDE_COLOR
from .bolus_display import is_005_bolus,MARKED_BOLUS_LABEL
from .event_hover import format_messages
from .inspector_values import previous_observation,elapsed_label

EPOCH=datetime(1970,1,1)
def wall(value):return (datetime.fromisoformat(value)-EPOCH).total_seconds()
def iso(value):return (EPOCH+timedelta(seconds=value)).isoformat(timespec='seconds')
def day_start(value):return datetime.fromisoformat(value).replace(hour=0,minute=0,second=0,microsecond=0).isoformat()

class WallAxis(pg.AxisItem):
    def tickValues(self,minVal,maxVal,size):
        target=(maxVal-minVal)/max(2,size/95)
        spacing=next((v for v in (60,300,600,900,1800,3600,7200,10800,21600,43200,86400,172800,604800) if v>=target),604800)
        start=math.ceil(minVal/spacing)*spacing
        return [(spacing,list(range(int(start),int(maxVal)+1,spacing)))]
    def tickStrings(self,values,scale,spacing):
        fmt='%d/%m\n%H:%M' if spacing>=86400 else '%H:%M'
        return [(EPOCH+timedelta(seconds=v)).strftime(fmt) for v in values]

class InsulinAxis(pg.AxisItem):
    def tickValues(self,minVal,maxVal,size):
        # Space below zero is reserved for the marker footprint, not a dose.
        return [(step,[v for v in values if v>=0])
                for step,values in super().tickValues(minVal,maxVal,size)]

class EventTimeAxis(WallAxis):
    """Keep the ordinary scale, with two staggered rows of exact event times."""
    HELP='Horas de los eventos. Acerca el gráfico para separar las horas cercanas; pasa el ratón para ver los segundos.'
    def __init__(self,**kwargs):
        self.event_times=();self.event_labels=[]
        super().__init__(**kwargs)
        self.setHeight(88);self.setAcceptHoverEvents(True)
        self.setToolTip(self.HELP)
    def set_events(self,events):
        self.event_times=events;self.event_labels=[];self.picture=None;self.setToolTip(self.HELP);self.update()
    def drawPicture(self,painter,axisSpec,tickSpecs,textSpecs):
        super().drawPicture(painter,axisSpec,tickSpecs,textSpecs)
        self.event_labels=[]
        view=self.linkedView()
        if not view or not self.event_times:return
        start,end=self.range
        left=self.mapFromScene(view.mapViewToScene(QPointF(start,0))).x()
        right=self.mapFromScene(view.mapViewToScene(QPointF(end,0))).x()
        font=QFont('Segoe UI',9);metrics=QFontMetrics(font)
        labels=place_event_labels(self.event_times,start,end,right-left,metrics.horizontalAdvance)
        row_top=max([rect.bottom() for rect,flags,text in textSpecs]+[19])+10
        painter.save();painter.setFont(font)
        # A faint continuation connects each label to its guide through the axis.
        for label in labels:
            x=left+label['center'];top=row_top+label['row']*20
            painter.setPen(pg.mkPen(GUIDE_COLOR,width=.8))
            painter.drawLine(QPointF(x,row_top-7),QPointF(x,top))
            rect=QRectF(left+label['left'],top,label['right']-label['left'],18)
            painter.fillRect(rect,pg.mkBrush(255,255,255,245));painter.setPen(pg.mkPen('#637a90'))
            painter.drawText(rect,int(Qt.AlignmentFlag.AlignCenter),label['text'])
            self.event_labels.append({**label,'rect':rect,'axis_x':x})
        painter.restore()
    def hoverEvent(self,event):
        if event.isExit():self.setToolTip(self.HELP);return
        view=self.linkedView()
        if not view or not self.event_times:return
        x=view.mapSceneToView(event.scenePos()).x();start,end=self.range
        tolerance=(end-start)*8/max(1,view.width())
        nearby=sorted((e for e in self.event_times if abs(e['x']-x)<=tolerance),key=lambda e:abs(e['x']-x))[:12]
        if nearby:
            self.setToolTip('\n\n'.join((EPOCH+timedelta(seconds=e['x'])).strftime('%d/%m/%Y %H:%M:%S')+' · '+', '.join(e['labels']) for e in nearby))
        else:self.setToolTip(self.HELP)

class FlowLayout(QLayout):
    def __init__(self,parent=None,margin=0,hspacing=12,vspacing=3):
        super().__init__(parent);self.items=[];self.hs=hspacing;self.vs=vspacing;self.setContentsMargins(margin,margin,margin,margin)
    def addItem(self,item):self.items.append(item)
    def count(self):return len(self.items)
    def itemAt(self,index):return self.items[index] if 0<=index<len(self.items) else None
    def takeAt(self,index):return self.items.pop(index) if 0<=index<len(self.items) else None
    def expandingDirections(self):return Qt.Orientation(0)
    def hasHeightForWidth(self):return True
    def heightForWidth(self,width):return self._arrange(QRect(0,0,width,0),False)
    def setGeometry(self,rect):super().setGeometry(rect);self._arrange(rect,True)
    def sizeHint(self):return self.minimumSize()
    def minimumSize(self):
        size=QSize()
        for item in self.items:size=size.expandedTo(item.minimumSize())
        l,t,r,b=self.getContentsMargins();return size+QSize(l+r,t+b)
    def _arrange(self,rect,apply):
        l,t,r,b=self.getContentsMargins();x=rect.x()+l;y=rect.y()+t;height=0;right=rect.right()-r
        for item in self.items:
            size=item.sizeHint()
            if x+size.width()>right and height:x=rect.x()+l;y+=height+self.vs;height=0
            if apply:item.setGeometry(QRect(QPoint(x,y),size))
            x+=size.width()+self.hs;height=max(height,size.height())
        return y+height+b-rect.y()

class Loader(QThread):
    result=Signal(object);failed=Signal(str)
    def __init__(self,work,parent):super().__init__(parent);self.work=work
    def run(self):
        try:self.result.emit(self.work())
        except Exception as exc:self.failed.emit(type(exc).__name__)
        finally:self.work=None

class TimelineWidget(QWidget):
    busyChanged=Signal(bool)
    MAX_WINDOW=7*86400
    def __init__(self,database,parent=None):
        super().__init__(parent);self.database=database;self.worker=None;self.initialized=False;self.busy=False
        self.bounds=None;self.bundle=None;self.pending=None;self.frozen=False;self._drawing=False;self._reload_after=False;self._preserve_view=None
        self.current_start=None;self.current_width=86400;self.last_hover=None
        layout=QVBoxLayout(self);layout.setContentsMargins(4,0,4,0);layout.setSpacing(10)
        toolbar=QFrame();toolbar.setObjectName('timelineToolbar');tools=QHBoxLayout(toolbar);tools.setContentsMargins(0,0,0,0);tools.setSpacing(8)
        self.previous=QPushButton('Anterior');self.previous.setToolTip('Retroceder una ventana');self.previous.clicked.connect(lambda:self.shift(-1))
        self.next=QPushButton('Siguiente');self.next.setToolTip('Avanzar una ventana');self.next.clicked.connect(lambda:self.shift(1))
        self.date=QDateEdit();self.date.setCalendarPopup(True);self.date.setLocale(QLocale(QLocale.Language.Spanish,QLocale.Country.Spain));self.date.setDisplayFormat('ddd d MMM yyyy');self.date.setMinimumWidth(180);self.date.setDate(QDate.currentDate())
        self.window=QComboBox()
        for label,hours in (('3 horas',3),('6 horas',6),('12 horas',12),('24 horas',24),('48 horas',48),('7 días',168)):self.window.addItem(label,hours*3600)
        self.window.setCurrentIndex(3);self.window.activated.connect(lambda _index:self.request(self.current_start,self.window.currentData()) if self.current_start is not None else None);self.window.setToolTip('Periodo visible; pulsa Ver para aplicar')
        self.pump=QComboBox();self.pump.setMinimumWidth(145);self.pump.setToolTip('Bomba del histórico')
        self.go=QPushButton('Ver');self.go.setObjectName('primary');self.go.clicked.connect(self.go_to_date)
        self.latest=QPushButton('Más reciente');self.latest.clicked.connect(self.go_latest)
        self.unfreeze=QPushButton('Fijar instante');self.unfreeze.setCheckable(True);self.unfreeze.clicked.connect(self._toggle_pin)
        for w in (self.previous,self.date,self.next,self.window,self.go):tools.addWidget(w)
        tools.addStretch();tools.addWidget(self.pump);tools.addWidget(self.latest);tools.addWidget(self.unfreeze);layout.addWidget(toolbar)
        self.legend=QFrame();self.legend.setObjectName('timelineLegend');legend_layout=FlowLayout(self.legend,0,14,4)
        self.legend_entries=[]
        for name,label in (('glucose','Glucosa'),('bg','Glucemia introducida'),('bolus','Bolo'),('bolus_005','Bolo 0,05 U'),('iob','Insulina activa'),('basal','Basal'),('profile','Perfil programado'),('carbs','Carbohidratos'),('sleep','Sueño'),('exercise','Ejercicio'),('alert','Eventos')):
            chip=QWidget();row=QHBoxLayout(chip);row.setContentsMargins(0,1,0,1);row.setSpacing(6)
            pictogram=QLabel();pictogram.setPixmap(icon(name,22).pixmap(22,22));pictogram.setFixedSize(22,22)
            text=QLabel(label);text.setStyleSheet('font-size:10.5pt;color:#344c65;');row.addWidget(pictogram);row.addWidget(text);legend_layout.addWidget(chip);self.legend_entries.append((name,chip))
        layout.addWidget(self.legend)
        info=QHBoxLayout();self.range_label=QLabel('Elige un día para explorar el histórico.');self.range_label.setObjectName('muted');self.range_label.setMinimumWidth(305);info.addWidget(self.range_label);info.addStretch()
        hint=QLabel('Arrastrar: mover  ·  Rueda: zoom  ·  Clic: fijar');hint.setObjectName('muted');info.addWidget(hint);layout.addLayout(info)
        self.loading=QProgressBar();self.loading.setTextVisible(False);self.loading.setFixedHeight(3);self.loading.setRange(0,1);self.loading.setValue(0);layout.addWidget(self.loading)
        self.alert=QLabel('');self.alert.setWordWrap(True);self.alert.setStyleSheet('background:#fff4db;border:1px solid #ead39a;border-radius:6px;padding:7px;color:#725520;font-size:10pt;');self.alert.hide();layout.addWidget(self.alert)
        split=QSplitter(Qt.Orientation.Horizontal);split.setHandleWidth(9);layout.addWidget(split,1)
        self.canvas=pg.GraphicsLayoutWidget();self.canvas.setBackground('w');split.addWidget(self.canvas);self.plots=[]
        self.event_popup=QLabel(self.canvas.viewport());self.event_popup.setTextFormat(Qt.TextFormat.RichText);self.event_popup.setWordWrap(True)
        self.event_popup.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.event_popup.setStyleSheet('QLabel {background:#ffffff;color:#20334a;border:1px solid #bdcedd;border-radius:6px;padding:9px;font-size:10.5pt;}')
        self.event_popup.hide();self.hover_series=[];self._pointer_inside=False;self._hover_plain=''
        self._hover_paths={key:symbol(key) for key in ('bolus','alert','bg','carbs')}
        self.canvas.viewport().installEventFilter(self)
        self.mode_lane=self.canvas.addPlot(row=0,col=0,axisItems={'bottom':WallAxis(orientation='bottom')})
        self.mode_lane.setMaximumHeight(64);self.mode_lane.setMinimumHeight(58);self.mode_lane.setYRange(0,1,padding=0);self.mode_lane.hideAxis('bottom');self.mode_lane.getAxis('left').setWidth(88);self.mode_lane.getAxis('left').setTicks([])
        self.mode_lane.setLabel('left','Modos',**{'color':'#344c65','font-size':'10pt'});self.mode_lane.setMenuEnabled(False);self.mode_lane.getViewBox().setMouseEnabled(x=True,y=False);self.mode_lane.hideButtons()
        self.mode_items=[];self.mode_segments=[];self.mode_labels=[];self.mode_label_meta=[];self.event_markers=[];self.event_guides=[]
        labels=(('Glucosa','mg/dL'),('Insulina','U'),('Basal','U/h'),('Carbohidratos','g'))
        for row,(label,units) in enumerate(labels):
            axes={'bottom':(EventTimeAxis if row==3 else WallAxis)(orientation='bottom')}
            if row==1:axes['left']=InsulinAxis(orientation='left')
            plot=self.canvas.addPlot(row=row+1,col=0,axisItems=axes)
            display_label=label if row<2 else ('Basal<br><span style="font-size:9pt">U/h</span>' if row==2 else 'Hidratos<br><span style="font-size:9pt">g</span>')
            plot.setLabel('left',display_label,units=units if row<2 else None,**{'color':'#344c65','font-size':'10pt'});plot.showGrid(x=True,y=True,alpha=0.16);plot.setMenuEnabled(False);plot.hideButtons()
            plot.getAxis('left').setWidth(88);plot.getViewBox().setMouseEnabled(x=True,y=False);plot.setClipToView(True)
            for edge in ('left','bottom'):
                axis=plot.getAxis(edge);axis.setTextPen(pg.mkPen('#4e6075'));axis.setPen(pg.mkPen('#d5dfe9'));axis.setTickFont(QFont('Segoe UI',10))
            if row:plot.setXLink(self.plots[0])
            if row<3:plot.hideAxis('bottom')
            plot.setLabel('left',display_label,units=units if row<2 else None,**{'color':'#344c65','font-size':'10pt'})
            self.canvas.ci.layout.setRowStretchFactor(row+1,5 if row==0 else 2);self.plots.append(plot)
        self.mode_lane.setXLink(self.plots[0]);self.crosshairs=[]
        for plot in self.plots+[self.mode_lane]:
            line=pg.InfiniteLine(angle=90,movable=False,pen=pg.mkPen('#5b738b',width=1,style=Qt.PenStyle.DashLine));plot.addItem(line,ignoreBounds=True);line.hide();self.crosshairs.append(line)
        self.tooltip=pg.TextItem(anchor=(0,1),color='#173d50',fill=(255,255,255,240),border='#bdcedd');self.tooltip.setFont(QFont('Segoe UI',11));self.plots[0].addItem(self.tooltip,ignoreBounds=True);self.tooltip.hide()
        self.proxy=pg.SignalProxy(self.canvas.scene().sigMouseMoved,rateLimit=30,slot=self._mouse_move);self.canvas.scene().sigMouseClicked.connect(self._click)
        self.plots[0].getViewBox().sigXRangeChanged.connect(self._range_changed)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(350);self.debounce.timeout.connect(self._load_view_range)
        self.mode_relayout=QTimer(self);self.mode_relayout.setSingleShot(True);self.mode_relayout.setInterval(65);self.mode_relayout.timeout.connect(self._layout_mode_labels);self.mode_relayout.timeout.connect(self._position_event_markers)
        self.mode_relayout.timeout.connect(self._pad_bolus_axis)
        panel=QFrame();panel.setObjectName('timelineInspector');sidebar=QVBoxLayout(panel);sidebar.setContentsMargins(14,12,14,12);sidebar.setSpacing(12)
        self.instant=QLabel('Explora un instante');self.instant.setWordWrap(True);self.instant.setStyleSheet('font-weight:700;font-size:13pt;color:#172b42;');sidebar.addWidget(self.instant)
        self.inspector_hint=QLabel('Mueve el cursor o fija una selección.');self.inspector_hint.setWordWrap(True);self.inspector_hint.setObjectName('muted');sidebar.addWidget(self.inspector_hint)
        self.values={};self.observation_times={};self.time_labels={};self.metric_captions={};self.age_labels={}
        grid=QGridLayout();grid.setHorizontalSpacing(10);grid.setVerticalSpacing(10)
        for index,(key,label,pictogram) in enumerate((('glucose','Glucosa','glucose'),('iob','Activa','iob'),('bolus','Último bolo','bolus'),('carbs','Últimos hidratos','carbs'))):
            card=QFrame();card.setObjectName('inspectorMetric');box=QVBoxLayout(card);box.setContentsMargins(10,8,10,8);box.setSpacing(3)
            caption=QLabel(label);caption.setStyleSheet('font-size:10pt;color:#62748a;');box.addWidget(caption);self.metric_captions[key]=caption
            value=QLabel('—');value.setTextFormat(Qt.TextFormat.PlainText);value.setWordWrap(True);value.setStyleSheet('font-size:16pt;font-weight:700;color:'+COLORS[pictogram]+';');box.addWidget(value)
            time_label=QLabel('');time_label.setStyleSheet('font-size:9pt;color:#728398;');box.addWidget(time_label);self.time_labels[key]=time_label
            if key in ('bolus','carbs'):
                age=QLabel('');age.setWordWrap(True);age.setStyleSheet('font-size:9pt;color:#62748a;');age.setToolTip('Tiempo transcurrido según el reloj original de la bomba.');box.addWidget(age);self.age_labels[key]=age
            self.values[key]=value;grid.addWidget(card,index//2,index%2)
        sidebar.addLayout(grid)
        settings=QFrame();settings.setObjectName('pumpSettings');form=QVBoxLayout(settings);form.setContentsMargins(0,0,0,0);form.setSpacing(8)
        heading=QLabel('Perfil y ajustes observados');heading.setStyleSheet('font-size:12pt;font-weight:700;color:#172b42;');form.addWidget(heading)
        for key,label in (('profile','Programa'),('mode','Modo'),('basal_profile','Basal del perfil'),('carb_ratio','Ratio de hidratos'),('sensitivity','Sensibilidad'),('target','Objetivo')):
            row=QHBoxLayout();row.setContentsMargins(0,0,0,0)
            caption=QLabel(label);caption.setStyleSheet('font-size:10pt;color:#62748a;');row.addWidget(caption)
            value=QLabel('—');value.setTextFormat(Qt.TextFormat.PlainText);value.setWordWrap(True);value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter);value.setStyleSheet('font-size:11pt;font-weight:600;color:#233b54;');row.addWidget(value,1);self.values[key]=value;form.addLayout(row)
        sidebar.addWidget(settings)
        self.evidence_toggle=QToolButton();self.evidence_toggle.setText('Ver horas y procedencia');self.evidence_toggle.setCheckable(True);self.evidence_toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly);sidebar.addWidget(self.evidence_toggle)
        self.evidence_toggle.setToolTip('Incluye la descripción del evento y sus parámetros técnicos originales.')
        self.detail=QLabel('');self.detail.setWordWrap(True);self.detail.setTextFormat(Qt.TextFormat.PlainText);self.detail.setStyleSheet('font-size:9.5pt;color:#62748a;');self.detail.hide();self.evidence_toggle.toggled.connect(self.detail.setVisible);sidebar.addWidget(self.detail)
        self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        note=QLabel('Ajustes según la última observación anterior al cursor.');note.setObjectName('muted');note.setWordWrap(True);note.setStyleSheet('font-size:9.5pt;color:#728398;');sidebar.addWidget(note);sidebar.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(panel);scroll.setMinimumWidth(285);scroll.setMaximumWidth(330);scroll.setFrameShape(QScrollArea.Shape.NoFrame);split.addWidget(scroll);split.setSizes([1000,310])
        self.controls=(self.previous,self.next,self.date,self.window,self.pump,self.go,self.latest)

    def activate(self):
        if not self.initialized and not self.busy:
            self.initialized=True;self._run(lambda:timeline_bounds(self.database),'bounds')
    def _run(self,work,kind):
        if self.busy:return False
        self._hide_event_popup()
        self.busy=True;self.busyChanged.emit(True);self.loading.setRange(0,0)
        for c in self.controls:c.setEnabled(False)
        self._result=None;self._error=None;self._kind=kind;self.worker=Loader(work,self)
        self.worker.result.connect(self._receive);self.worker.failed.connect(self._failure);self.worker.finished.connect(self._finished);self.worker.start();return True
    @Slot(object)
    def _receive(self,result):self._result=result
    @Slot(str)
    def _failure(self,error):self._error=error
    @Slot()
    def _finished(self):
        old=self.worker;self.worker=None;self.busy=False;self.busyChanged.emit(False);self.loading.setRange(0,1);self.loading.setValue(0)
        for c in self.controls:c.setEnabled(True)
        if self._error:
            if self._kind=='bounds':self.initialized=False
            self.range_label.setText('No se pudo cargar esta ventana ('+self._error+'). Reduce el periodo o comprueba la base.');self.pending=None
        elif self._kind=='bounds':
            self.bounds=self._result
            self.pump.clear()
            for serial in self.bounds.get('devices',[]):self.pump.addItem('Bomba '+str(serial),str(serial))
            self.pump.setVisible(self.pump.count()>1)
            if self.bounds.get('last') and self._preserve_view:
                start,width,serial=self._preserve_view;self._preserve_view=None
                index=self.pump.findData(serial)
                if index>=0:self.pump.setCurrentIndex(index)
                self.request(start,width)
            elif self.bounds.get('last'):self.go_latest()
            else:self.range_label.setText('No hay lecturas de glucosa en la base.');self.initialized=False
        else:self.render(self._result)
        old.deleteLater()
        if self._reload_after and not self.busy:
            self._reload_after=False;self.reload();return
        if self.pending and not self.busy:
            a,b=self.pending;self.pending=None;self.request(a,b)

    def request(self,start,width=None):
        width=min(self.MAX_WINDOW,max(900,float(width or self.window.currentData() or 86400)))
        if isinstance(start,str):start=wall(start)
        if self.bounds and self.bounds.get('first'):
            ranges=self.bounds.get('device_ranges',{})
            selected=ranges.get(self.pump.currentData(),self.bounds)
            lower=wall(day_start(selected['first']));upper=wall(day_start(selected['last']))+86400
            start=max(lower,min(float(start),max(lower,upper-width)))
        if self.busy:self.pending=(start,width);return
        self.current_start=float(start);self.current_width=width
        dt=EPOCH+timedelta(seconds=start);self.date.setDate(QDate(dt.year,dt.month,dt.day))
        serial=self.pump.currentData()
        # One window only. Context and events are replaced, never appended.
        margin=min(3600,max(300,width*0.05));a=start-margin;b=start+width+margin
        if b-a>self.MAX_WINDOW:a=start;b=start+width
        self.range_label.setText('Cargando '+iso(start).replace('T',' ')+'…')
        def load():return {'data':load_timeline(self.database,iso(a),iso(b),serial),
                           'context':load_context(self.database,iso(a),iso(b),serial),'view_start':start,'view_width':width,'cache_start':a,'cache_end':b}
        self._run(load,'window')
    def go_latest(self):
        self._preserve_view=None
        if self.bounds and self.bounds.get('last'):self.window.setCurrentIndex(3);self.request(day_start(self.bounds['last']),86400)
    def go_to_date(self):self.request(self.date.date().toString('yyyy-MM-dd')+'T00:00:00',self.window.currentData())
    def shift(self,direction):
        if self.current_start is not None:self.request(self.current_start+direction*self.current_width,self.current_width)
    def follow_mouse(self):self.frozen=False;self.unfreeze.setChecked(False);self.unfreeze.setText('Fijar instante');self.inspector_hint.setText('Valores junto al cursor')
    def _toggle_pin(self):
        self.frozen=self.unfreeze.isChecked();self.unfreeze.setText('Instante fijado' if self.frozen else 'Fijar instante');self.inspector_hint.setText('Instante fijado' if self.frozen else 'Valores junto al cursor')
    def reload(self):
        if self.busy:self._reload_after=True;return
        if self.current_start is not None:self._preserve_view=(self.current_start,self.current_width,self.pump.currentData())
        self.bundle=None;self.initialized=False
        if self.isVisible():self.activate()
    def _range_changed(self,*_):
        self._hide_event_popup()
        if not self._drawing and self.bundle:self.debounce.start();self.mode_relayout.start()
    def _load_view_range(self):
        if not self.bundle:return
        left,right=self.plots[0].viewRange()[0]
        if right-left>self.MAX_WINDOW:
            self.request(left,self.MAX_WINDOW);return
        if left<self.bundle['cache_start'] or right>self.bundle['cache_end']:self.request(left,right-left)
        else:
            self.current_start=left;self.current_width=right-left;self._range_text()
    def _range_text(self):
        start=EPOCH+timedelta(seconds=self.current_start);end=EPOCH+timedelta(seconds=self.current_start+self.current_width)
        self.range_label.setText(start.strftime('%d/%m/%Y · %H:%M')+'  —  '+end.strftime('%d/%m/%Y · %H:%M'))
        self.range_label.setMinimumWidth(self.range_label.fontMetrics().horizontalAdvance(self.range_label.text())+4)

    def render(self,bundle):
        self._hide_event_popup();self.hover_series=[]
        self.bundle=bundle;self.frozen=False;self._drawing=True
        for p in self.plots:p.clear()
        self.mode_lane.clear();self.mode_items=[];self.mode_labels=[];self.event_markers=[];self.event_guides=[]
        self.crosshairs=[]
        for p in self.plots+[self.mode_lane]:
            line=pg.InfiniteLine(angle=90,movable=False,pen=pg.mkPen('#58778b',style=Qt.PenStyle.DashLine));p.addItem(line,ignoreBounds=True);self.crosshairs.append(line)
        data=bundle['data'];context=bundle['context'];self.point_lists={}
        observed_points=[p['x'] for key in ('glucose','boluses','carbs','basal','events') for p in data.get(key,[])]+[p['x'] for p in context.get('observed_iob',[])]
        observed_end=max(observed_points,default=bundle['cache_start'])
        self.mode_segments=derive_mode_segments(bundle)
        self._draw_mode_lane(bundle)
        for key in ('glucose','boluses','carbs','basal','events'):
            points=sorted(data.get(key,[]),key=lambda p:p['x']);self.point_lists[key]=(points,[p['x'] for p in points])
        self.last_point_lists={}
        for key in ('boluses','carbs'):
            points=sorted(data.get('predecessors',{}).get(key,[])+data.get(key,[]),key=lambda p:p['x'])
            self.last_point_lists[key]=(points,[p['x'] for p in points])
        for index,key,radius in ((0,'glucose',8),(1,'boluses',12),(2,'basal',6),(3,'carbs',11)):
            self._register_hover(self.plots[index],{'boluses':'bolus'}.get(key,key),data.get(key,[]),radius)
        self._register_hover(self.plots[2],'basal_profile',data.get('basal',[]),6)
        self._register_hover(self.plots[1],'iob',context.get('observed_iob',[]),7)
        glucose=[p for p in self.point_lists['glucose'][0] if p.get('details',{}).get('kind','cgm')=='cgm']
        numeric_glucose=[p for p in glucose if p.get('value') is not None]
        if numeric_glucose:
            x=[];y=[];previous=None
            for p in glucose:
                if p.get('value') is None:
                    x.append(float('nan'));y.append(float('nan'));previous=None;continue
                clock_boundary=any(previous is not None and previous<=c['x']<=p['x'] for c in data.get('clock_changes',[]))
                if previous and (p['x']-previous>720 or p['x']<=previous or clock_boundary):x.append(float('nan'));y.append(float('nan'))
                x.append(p['x']);y.append(p['value']);previous=p['x']
            self.plots[0].plot(x,y,pen=pg.mkPen('#168f78',width=2.4),symbol='o',symbolSize=4,symbolBrush='#168f78',symbolPen=None,connect='finite',name='Glucosa')
            self.plots[0].setYRange(max(0,min(yv for yv in y if math.isfinite(yv))-25),max(yv for yv in y if math.isfinite(yv))+25)
        else:self.plots[0].setYRange(40,300)
        all_glucose=[p['value'] for p in self.point_lists['glucose'][0] if isinstance(p.get('value'),(int,float)) and math.isfinite(p['value'])]
        if all_glucose:self.plots[0].setYRange(max(0,min(all_glucose)-25),max(all_glucose)+25)
        for p in glucose:
            if p.get('value') is None and p.get('details',{}).get('qualifier') in ('high','low'):
                high=p['details']['qualifier']=='high';mark=pg.TextItem('ALTA' if high else 'BAJA',color='#b26540',anchor=(.5,0 if high else 1))
                mark.setPos(p['x'],self.plots[0].viewRange()[1][1 if high else 0]);self.plots[0].addItem(mark,ignoreBounds=True)
        bg=[p for p in self.point_lists['glucose'][0] if p.get('details',{}).get('kind')=='bg' and p.get('value') is not None]
        if bg:self.plots[0].plot([p['x'] for p in bg],[p['value'] for p in bg],pen=None,symbol=symbol('bg'),symbolSize=12,symbolBrush='#597bb5',symbolPen=None,name='Glucemia introducida')
        boluses=[p for p in self.point_lists['boluses'][0] if p.get('value') is not None]
        regular=[p for p in boluses if not is_005_bolus(p)]
        marked=[p for p in boluses if is_005_bolus(p)]
        if regular:self._stems(self.plots[1],regular,COLORS['bolus'],'Bolos',symbol('bolus'))
        iobs=[p for p in context.get('observed_iob',[]) if p.get('value') is not None]
        if iobs:self.plots[1].plot([p['x'] for p in iobs],[p['value'] for p in iobs],pen=None,symbol='o',symbolSize=6,symbolPen=None,symbolBrush=COLORS['iob'],name='Activa observada')
        if marked:
            self._stems(self.plots[1],marked,COLORS['bolus_005'],MARKED_BOLUS_LABEL,symbol('bolus_005'),marker_size=20,marker_pen=pg.mkPen('white',width=1),z=10)
        self.bolus_ceiling=max([p['value'] for p in boluses+iobs]+[1])*1.2
        self.has_marked_bolus=bool(marked)
        self._pad_bolus_axis()
        basal=[p for p in self.point_lists['basal'][0] if p.get('value') is not None]
        if basal:
            bx=[];by=[];profile=[];previous=None
            for p in basal:
                boundary=any(previous is not None and previous<=c['x']<=p['x'] for c in data.get('clock_changes',[]))
                if previous is not None and (p['x']-previous>720 or p['x']<=previous or boundary):bx.append(float('nan'));by.append(float('nan'));profile.append(float('nan'))
                rate=p.get('details',{}).get('profile_rate')
                bx.append(p['x']);by.append(p['value']);profile.append(rate if rate is not None else float('nan'));previous=p['x']
            self.plots[2].plot(bx,by,pen=pg.mkPen('#2876b8',width=1.8),stepMode='left',name='Tasa indicada')
            self.plots[2].plot(bx,profile,pen=pg.mkPen('#5cabb5',width=1,style=Qt.PenStyle.DashLine),stepMode='left',name='Perfil observado')
        self.plots[2].setYRange(0,max([p['value'] for p in basal]+[1])*1.15)
        carbs=[p for p in self.point_lists['carbs'][0] if p.get('value') is not None]
        if carbs:self._stems(self.plots[3],carbs,COLORS['carbs'],'Carbohidratos',symbol('carbs'))
        self.plots[3].setYRange(0,max([p['value'] for p in carbs]+[20])*1.2)
        self.event_times=collect_event_times(data)
        times=tuple(e['x'] for e in self.event_times)
        for p in self.plots+[self.mode_lane]:
            guide=EventGuideItem(times)
            if p is self.mode_lane:guide.setZValue(1)
            p.addItem(guide,ignoreBounds=True);self.event_guides.append(guide)
        self.plots[3].getAxis('bottom').set_events(self.event_times)
        discrete=sorted(data.get('events',[])+data.get('clock_changes',[]),key=lambda p:p['x'])
        self._register_hover(self.plots[0],'event',discrete,10)
        for e in discrete:
            color='#b38c32' if e.get('details',{}).get('event_code') in (13,14) else '#b77564' if e.get('details',{}).get('kind') in ('alarm','alert','cgm_alert','suspend') else '#4866a1'
            ymin,ymax=self.plots[0].viewRange()[1];pixels=max(80,self.plots[0].getViewBox().sceneBoundingRect().height());inside=ymax-(ymax-ymin)*11/pixels
            mark=pg.ScatterPlotItem([e['x']],[inside],symbol=symbol('alert'),size=13,brush=color,pen=None);self.plots[0].addItem(mark,ignoreBounds=True);self.event_markers.append((mark,e['x']))
            self.hover_event_y=inside
        self.tooltip=pg.TextItem(anchor=(0,1),color='#173d50',fill=(255,255,255,240),border='#bdcedd');self.tooltip.setFont(QFont('Segoe UI',11));self.plots[0].addItem(self.tooltip,ignoreBounds=True)
        self.plots[0].setXRange(bundle['view_start'],bundle['view_start']+bundle['view_width'],padding=0)
        self._drawing=False;self._range_text();self.mode_relayout.start()
        warnings=data.get('warnings',[])+context.get('warnings',[])
        self.detail.setText('\n'.join(dict.fromkeys(warnings)))
        self.hover_at(bundle['view_start']+bundle['view_width']/2)

    @staticmethod
    def _stems(plot,points,color,name,symbol,marker_size=18,marker_pen=None,z=0):
        x=[];y=[]
        for p in points:x.extend((p['x'],p['x'],float('nan')));y.extend((0,p['value'],float('nan')))
        stem=plot.plot(x,y,pen=pg.mkPen(color,width=2),connect='finite');stem.setZValue(z)
        marker=plot.plot([p['x'] for p in points],[p['value'] for p in points],pen=None,symbol=symbol,symbolSize=marker_size,symbolBrush=color,symbolPen=marker_pen,name=name);marker.setZValue(z)
    def _pad_bolus_axis(self):
        if not hasattr(self,'bolus_ceiling'):return
        if self.has_marked_bolus:
            height=max(30,self.plots[1].getViewBox().height())
            bottom=-self.bolus_ceiling*13/(height-13)
            self.plots[1].setYRange(bottom,self.bolus_ceiling,padding=0)
        else:self.plots[1].setYRange(0,self.bolus_ceiling)
    def nearest(self,key,x,tolerance):
        points,xs=self.point_lists.get(key,([],[]));i=bisect_left(xs,x);indexes=range(max(0,i-1),min(len(points),i+2))
        nearest=min((points[k] for k in indexes),key=lambda p:abs(p['x']-x),default=None)
        if not nearest or abs(nearest['x']-x)>tolerance:return None
        group=points[bisect_left(xs,nearest['x']):bisect_right(xs,nearest['x'])]
        variants=nearest.get('details',{}).get('revision_ids',[]);revision_count=max(len(variants),nearest.get('details',{}).get('revision_count',0))
        if len(group)>1 or revision_count>1:
            nearest=dict(nearest);nearest['details']=dict(nearest.get('details',{}));nearest['details']['observation_count']=max(len(group),revision_count)
            values={p.get('value') for p in group}
            if len(values)>1 or revision_count>1:
                nearest['details']['ambiguous']=True;nearest['details']['alternatives']=sorted(str(v) for v in values);nearest['value']=None
        return nearest
    def _mouse_move(self,event):
        if self.busy or not self.bundle:self._hide_event_popup();return
        pos=event[0]
        for plot in self.plots+[self.mode_lane]:
            vb=plot.getViewBox()
            if vb.sceneBoundingRect().contains(pos):
                if not self.frozen:self.hover_at(vb.mapSceneToView(pos).x())
                if self._pointer_inside and QApplication.mouseButtons()==Qt.MouseButton.NoButton:self._show_event_popup(plot,pos)
                else:self._hide_event_popup()
                return
        self._hide_event_popup()

    def _register_hover(self,plot,kind,points,radius):
        points=sorted(points,key=lambda p:p['x'])
        self.hover_series.append((plot,kind,points,[p['x'] for p in points],radius))
    def _hover_hits(self,plot,pos):
        vb=plot.getViewBox();local=vb.mapSceneToView(pos)
        if plot is self.mode_lane:
            if .16<=local.y()<=.88:
                return [('mode',s) for s in self.mode_segments if s['start']<=local.x()<s['end']]
            return []
        left,right=vb.viewRange()[0];tolerance=(right-left)*14/max(1,vb.sceneBoundingRect().width());hits=[]
        for owner,kind,points,xs,radius in self.hover_series:
            if owner is not plot:continue
            for point in points[bisect_left(xs,local.x()-tolerance):bisect_right(xs,local.x()+tolerance)]:
                value=point.get('details',{}).get('profile_rate') if kind=='basal_profile' else point.get('value')
                if kind=='event':value=getattr(self,'hover_event_y',None)
                if kind=='glucose' and value is None:
                    qualifier=point.get('details',{}).get('qualifier')
                    if qualifier in ('high','low'):value=vb.viewRange()[1][1 if qualifier=='high' else 0]
                if not isinstance(value,(int,float)) or not math.isfinite(value):continue
                center=vb.mapViewToScene(QPointF(point['x'],value));distance=math.hypot(pos.x()-center.x(),pos.y()-center.y())
                if distance<=radius:
                    priority=0;shape=None;size=1
                    if kind=='bolus':shape='bolus';size=20 if is_005_bolus(point) else 18
                    elif kind=='event':shape='alert';size=13
                    elif kind=='carbs':shape='carbs';size=18
                    elif kind=='glucose' and point.get('details',{}).get('kind')=='bg':shape='bg';size=12
                    if shape and self._hover_paths[shape].contains(QPointF((pos.x()-center.x())/size,(pos.y()-center.y())/size)):
                        priority=20 if kind=='event' or (kind=='bolus' and is_005_bolus(point)) else 5 if kind!='bolus' else 2
                    elif kind=='iob' and distance<=3:priority=5
                    hits.append((priority,distance,kind,point))
        return [(kind,point) for _,_,kind,point in sorted(hits,key=lambda hit:(-hit[0],hit[1]))]
    def _show_event_popup(self,plot,pos):
        hits=self._hover_hits(plot,pos)
        if not hits:self._hide_event_popup();return
        # A wide day view can stack many IOB points near a bolus. Identify the
        # nearest marker, retaining all conflicting records at its exact time.
        target_kind,target=hits[0]
        if target_kind!='mode':
            hits=[(kind,p) for owner,kind,points,xs,radius in self.hover_series
                  if owner is plot and kind==target_kind
                  for p in points[bisect_left(xs,target['x']):bisect_right(xs,target['x'])]]
            hits.sort(key=lambda hit:hit[1] is not target)
        viewport=self.canvas.viewport();metrics=self.event_popup.fontMetrics()
        max_height=max(40,viewport.height()-16)
        for limit in range(min(6,len(hits)),0,-1):
            html,plain=format_messages(hits,limit);self.event_popup.setText(html)
            width=min(360,max(180,max((metrics.horizontalAdvance(line) for line in plain.splitlines()),default=0)+24),max(60,viewport.width()-16))
            self.event_popup.setFixedWidth(width);height=self.event_popup.heightForWidth(width)
            if height<=max_height:break
        self._hover_plain=plain;self.event_popup.setAccessibleName(plain)
        self.event_popup.resize(width,min(height,max_height))
        cursor=self.canvas.mapFromScene(pos);height=self.event_popup.height()
        x=cursor.x()+16 if cursor.x()+16+width<viewport.width() else cursor.x()-width-16
        y=cursor.y()+16 if cursor.y()+16+height<viewport.height() else cursor.y()-height-16
        self.event_popup.move(max(4,min(x,viewport.width()-width-4)),max(4,min(y,viewport.height()-height-4)))
        self.tooltip.hide();self.event_popup.show();self.event_popup.raise_()
    def _hide_event_popup(self):
        self.event_popup.hide();self._hover_plain=''
    def eventFilter(self,watched,event):
        if hasattr(self,'canvas') and watched is self.canvas.viewport():
            if event.type()==QEvent.Type.Enter:self._pointer_inside=True
            elif event.type() in (QEvent.Type.Leave,QEvent.Type.Hide):
                self._pointer_inside=False;self._hide_event_popup()
        return super().eventFilter(watched,event)
    def hideEvent(self,event):
        if hasattr(self,'event_popup'):self._hide_event_popup();self._pointer_inside=False
        super().hideEvent(event)
    def _click(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.bundle:
            self.frozen=not self.frozen;self.unfreeze.setChecked(self.frozen);self.unfreeze.setText('Instante fijado' if self.frozen else 'Fijar instante');self.inspector_hint.setText('Instante fijado' if self.frozen else 'Valores junto al cursor')
    def hover_at(self,x):
        if not self.bundle:return
        self.last_hover=x;stamp=iso(x);cursor_dt=datetime.fromisoformat(stamp);self.instant.setText(self.date.locale().toString(QDate(cursor_dt.year,cursor_dt.month,cursor_dt.day),'d MMM')+' · '+cursor_dt.strftime('%H:%M:%S'))
        self.inspector_hint.setText('Instante fijado' if self.frozen else 'Valores junto al cursor')
        for line in self.crosshairs:line.setPos(x)
        ctx=context_at(self.bundle['context'],stamp);glucose=self.nearest('glucose',x,300)
        tolerance=min(300,max(45,self.current_width/100))
        bolus=previous_observation(*self.last_point_lists['boluses'],x)
        carbs=previous_observation(*self.last_point_lists['carbs'],x)
        marked=is_005_bolus(bolus)
        self.values['bolus'].setStyleSheet('font-size:16pt;font-weight:700;color:'+COLORS['bolus_005' if marked else 'bolus']+';')
        self.set_value('glucose',self.point_text(glucose))
        self._set_last_value('bolus',bolus,x);self._set_last_value('carbs',carbs,x)
        for key in ('profile','basal_profile','carb_ratio','sensitivity','target','iob','mode'):
            observation=ctx.get(key) or {};value=observation.get('value');unit=observation.get('unit') or ''
            label='Sin dato confirmado' if value is None else (f'{value:.3f}'.rstrip('0').rstrip('.').replace('.',',') if isinstance(value,(int,float)) else str(value))+' '+unit
            if key=='mode' and value is not None:label={'normal':'Normal','sleep':'Sueño','exercise':'Ejercicio','eating_soon':'Comida próxima'}.get(str(value),str(value))
            if key=='iob' and value is None and observation.get('last_observed_value') is not None:
                label+='\nÚltima lectura: '+str(observation['last_observed_value'])+' U'
            if observation.get('time'):label+='\nObservado '+str(observation['time']).replace('T',' ')
            self.set_value(key,label.strip())
        self.tooltip.hide()
        extra=[]
        for p in (glucose,bolus,carbs):
            if p:extra.append(str(p.get('source',''))+' · '+p['time'])
        event=self.nearest('events',x,tolerance)
        if event:extra.insert(0,event.get('details',{}).get('label','Evento')+' · '+event['time'])
        if event:
            from .alert_details import alert_details
            event_details=event.get('details',{});technical=alert_details(event_details,technical=True)
            if not technical:
                technical=['Datos técnicos · evento '+str(event_details.get('event_code','no indicado'))]
                technical.extend(key+'='+json.dumps(event_details[key],ensure_ascii=False,separators=(',',':'))
                                 for key in ('properties','labels','state_transitions') if key in event_details)
            extra.extend(technical)
        warnings=self.bundle['data'].get('warnings',[])+ctx.get('warnings',[])
        details=[]
        for key,label in (('glucose','Glucosa'),('iob','Activa'),('bolus','Bolo'),('carbs','Hidratos'),('profile','Programa'),('basal_profile','Basal'),('carb_ratio','Ratio'),('sensitivity','Sensibilidad'),('target','Objetivo'),('mode','Modo')):
            full=self.observation_times.get(key,'')
            if '\n' in full:details.append(label+': '+full.replace('\n',' · '))
        self.detail.setText('\n'.join(dict.fromkeys(warnings+extra+details)))
        clock_changes=self.bundle['context'].get('clock_changes',[])
        visible_clock=any(self.current_start<=p['x']<=self.current_start+self.current_width for p in clock_changes)
        clock_barrier=max((p['x'] for p in clock_changes if p['x']<=x),default=float('-inf'))
        affected_clock=any(isinstance(v,dict) and 'invalidated' in v.get('method','') and v.get('x',float('inf'))<=clock_barrier for v in ctx.values())
        ambiguous_clock=any(a<=x<=b for a,b in self.bundle['context'].get('ambiguous_clock_ranges',[]))
        critical=self.bundle['data'].get('warnings',[])+[w for w in ctx.get('warnings',[]) if any(word in w.lower() for word in ('reloj','revis','ambigu'))]
        if not (visible_clock or affected_clock or ambiguous_clock):critical=[w for w in critical if 'reloj' not in w.lower()]
        self._set_warnings(critical)
    def _set_last_value(self,key,point,x):
        if point is None:
            self.set_value(key,'Sin registro')
            self.values[key].setToolTip('No hay un registro anterior disponible hasta este instante.')
            self.time_labels[key].setText('anterior disponible');self.age_labels[key].setText('');return
        text=self.point_text(point)
        if point.get('details',{}).get('ambiguous'):
            text='Ambiguo\n'+text
        if key=='bolus' and is_005_bolus(point):text=text.replace('\n','\n'+MARKED_BOLUS_LABEL+' · resaltado por dosis\n',1)
        clocks=self.bundle['data'].get('clock_changes',[])+self.bundle['context'].get('clock_changes',[])
        age=elapsed_label(point,x,clocks,self.bundle['context'].get('ambiguous_clock_ranges',[]))
        if self.bundle['data'].get('truncated') or self.bundle['data'].get('predecessor_truncated'):
            age='Registro disponible · consulta limitada'
        self.set_value(key,text);self.age_labels[key].setText(age)
        dt=datetime.fromisoformat(point['time']);cursor=EPOCH+timedelta(seconds=x)
        self.time_labels[key].setText(dt.strftime('%H:%M:%S' if dt.date()==cursor.date() else '%d/%m %H:%M:%S'))
        self.values[key].setToolTip(text+'\n'+age)
    def set_value(self,key,text):
        self.observation_times[key]=text;label=self.values[key];parts=text.split('\n');main=parts[0]
        if main=='Sin observación cercana':main='Sin dato cercano'
        if main=='Sin dato confirmado':main='No disponible'
        label.setToolTip(text);label.setMinimumHeight(0)
        if key not in ('glucose','iob','bolus','carbs'):
            date_text=''
            if len(parts)>1:
                source_time=parts[-1].replace('Observado ','')
                try:
                    dt=datetime.fromisoformat(source_time);cursor=EPOCH+timedelta(seconds=self.last_hover or 0)
                    date_text='obs. '+dt.strftime('%H:%M' if dt.date()==cursor.date() else '%d/%m %H:%M')
                except ValueError:date_text=source_time
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText('<b>'+escape(main)+'</b>'+('<br><span style="font-size:9pt;font-weight:400;color:#728398;">'+escape(date_text)+'</span>' if date_text else ''))
        else:
            label.setAccessibleName(main)
            label.setTextFormat(Qt.TextFormat.RichText);label.setWordWrap(False);label.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Preferred)
            pieces=main.split(' ',1)
            numeric=bool(pieces and any(c.isdigit() for c in pieces[0]))
            if numeric:
                label.setText('<span style="font-size:20pt;font-weight:700;">'+escape(pieces[0])+'</span>'+(' <span style="font-size:10pt;font-weight:500;">'+escape(pieces[1])+'</span>' if len(pieces)>1 else ''))
            else:label.setText('<span style="font-size:10.5pt;color:#728398;">'+escape(main)+'</span>')
        if key in ('glucose','iob','bolus','carbs'):
            time_label=self.time_labels[key]
            if len(parts)>1:
                source_time=parts[-1].replace('Observado ','')
                try:
                    dt=datetime.fromisoformat(source_time);cursor=EPOCH+timedelta(seconds=self.last_hover or 0)
                    time_label.setText('obs. '+dt.strftime('%H:%M:%S' if dt.date()==cursor.date() else '%d/%m %H:%M'))
                except ValueError:time_label.setText(source_time)
            else:time_label.setText('')
    def _set_warnings(self,critical):
        critical=list(dict.fromkeys(critical));self.alert.setToolTip('\n'.join(critical))
        titles=[]
        joined=' '.join(critical).lower()
        if any(w in joined for w in ('difier','difer','fuentes')):titles.append('Diferencias entre fuentes')
        if 'reloj' in joined:titles.append('Cambios de reloj')
        if any(w in joined for w in ('limitad','denso','reduc')):titles.append('Datos limitados: reduce el periodo')
        if any(w in joined for w in ('ambigu','revis')):titles.append('Observaciones ambiguas')
        if critical and not titles:titles.append('Observaciones para revisar')
        self.alert.setText(' · '.join(titles)+' · Ver horas y procedencia' if titles else '')
        self.alert.setVisible(bool(critical))
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'event_popup'):self._hide_event_popup()
        if hasattr(self,'mode_relayout') and self.bundle:self.mode_relayout.start()
    def _draw_mode_lane(self,bundle):
        self.mode_lane.setYRange(0,1,padding=0)
        a=bundle['view_start'];b=a+bundle['view_width']
        baseline=pg.BarGraphItem(x0=[a],x1=[b],y0=.16,y1=.88,brush='#f2f5f9',pen=pg.mkPen('#e2e8f0'))
        self.mode_lane.addItem(baseline);self.mode_items.append(baseline)
        palette={'sleep':('#dbe5f8','#91a8d0'),'exercise':('#ffebc8','#d7af72'),'normal':('#edf2f7','#d3dce6'),'unknown':('#f3f4f6','#dce1e7')}
        for segment in self.mode_segments:
            if segment['mode'] not in palette:continue
            fill,border=palette[segment['mode']]
            bar=pg.BarGraphItem(x0=[segment['start']],x1=[segment['end']],y0=.16,y1=.88,brush=fill,pen=pg.mkPen(border,width=1.2))
            self.mode_lane.addItem(bar);self.mode_items.append(bar)
        self._layout_mode_labels()
    def _layout_mode_labels(self):
        if not self.bundle:return
        for item in self.mode_labels:self.mode_lane.removeItem(item)
        self.mode_labels=[];self.mode_label_meta=[]
        a,b=self.plots[0].viewRange()[0];width=max(1,self.mode_lane.getViewBox().sceneBoundingRect().width());per_pixel=(b-a)/width
        if per_pixel<=0:return
        font=QFont('Segoe UI',10);font.setBold(True);metrics=QFontMetrics(font)
        for segment in self.mode_segments:
            mode=segment['mode'];left=max(a,segment['start']);right=min(b,segment['end'])
            if right<=left:continue
            pixels=(right-left)/per_pixel
            if pixels<26:continue
            icon_width=21 if mode in ('sleep','exercise') else 0;gap=7 if icon_width else 0
            label=segment['label'];padding=14
            long_label=label
            if segment.get('confirmed_end') and not segment.get('uncertain') and not segment.get('clipped_start') and not segment.get('clipped_end'):
                minutes=int((segment['end']-segment['start'])/60)
                long_label+=' · '+(f'{minutes//60} h {minutes%60:02d} min' if minutes>=60 else f'{minutes} min')
            if metrics.horizontalAdvance(long_label)+icon_width+gap+padding<=pixels:label=long_label
            elif metrics.horizontalAdvance(label)+icon_width+gap+padding>pixels:label='';gap=0
            text_width=metrics.horizontalAdvance(label)+4 if label else 0
            group_width=icon_width+gap+text_width;center=(left+right)/2;group_left=center-group_width*per_pixel/2
            ink={'sleep':'#294b7e','exercise':'#855a1f','normal':'#65758a','unknown':'#798593'}.get(mode,'#65758a')
            if label:
                text=pg.TextItem(label,color=ink,anchor=(0,.5));text.setFont(font);text.setPos(group_left+(icon_width+gap)*per_pixel,.52)
                self.mode_lane.addItem(text);self.mode_labels.append(text)
            if icon_width:
                mark=pg.ScatterPlotItem([group_left+icon_width*per_pixel/2],[.52],symbol=symbol(mode),size=icon_width,brush=COLORS[mode],pen=None)
                self.mode_lane.addItem(mark);self.mode_labels.append(mark)
            self.mode_label_meta.append({'start':left,'end':right,'label':label,'group_left':group_left,'group_right':group_left+group_width*per_pixel,'icon_width':icon_width,'text_width':text_width})
    def _position_event_markers(self):
        if not self.event_markers:return
        ymin,ymax=self.plots[0].viewRange()[1];pixels=max(1,self.plots[0].getViewBox().sceneBoundingRect().height())
        inside=ymax-(ymax-ymin)*12/pixels
        self.hover_event_y=inside
        for item,x in self.event_markers:item.setData([x],[inside])
    @staticmethod
    def point_text(point):
        if not point:return 'Sin observación cercana'
        details=point.get('details',{})
        if details.get('ambiguous'):return 'Ambiguo · '+', '.join(details.get('alternatives',[]))+'\n'+point['time']
        if point.get('value') is None:
            return {'high':'ALTA · sin valor numérico','low':'BAJA · sin valor numérico'}.get(details.get('qualifier'),'Sin valor numérico')+'\n'+point['time']
        v=point['value'];text=f'{v:.3f}'.rstrip('0').rstrip('.').replace('.',',') if isinstance(v,(int,float)) else str(v)
        return text+' '+str(point.get('unit',''))+'\n'+point['time'].replace('T',' ')
