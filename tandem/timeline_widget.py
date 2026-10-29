"""Bounded-window Qt timeline. Only the displayed window and a small margin are retained."""
from __future__ import annotations
from bisect import bisect_left,bisect_right
from datetime import datetime,timedelta
from html import escape
import math
import pyqtgraph as pg
from PySide6.QtCore import Qt,QDate,QTimer,QThread,Signal,Slot
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QDateEdit,
    QComboBox,QSplitter,QScrollArea,QGroupBox,QFormLayout,QProgressBar)
from .timeline_data import load_timeline,timeline_bounds
from .pump_context import load_context,context_at

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
        self.bounds=None;self.bundle=None;self.pending=None;self.frozen=False;self._drawing=False;self._reload_after=False
        self.current_start=None;self.current_width=86400;self.last_hover=None
        layout=QVBoxLayout(self);layout.setContentsMargins(14,14,14,12);layout.setSpacing(8)
        tools=QHBoxLayout()
        self.previous=QPushButton('Anterior');self.previous.clicked.connect(lambda:self.shift(-1))
        self.next=QPushButton('Siguiente');self.next.clicked.connect(lambda:self.shift(1))
        self.date=QDateEdit();self.date.setCalendarPopup(True);self.date.setDisplayFormat('dd/MM/yyyy');self.date.setDate(QDate.currentDate())
        self.window=QComboBox()
        for label,hours in (('3 horas',3),('6 horas',6),('12 horas',12),('24 horas',24),('48 horas',48),('7 días',168)):self.window.addItem(label,hours*3600)
        self.window.setCurrentIndex(3)
        self.pump=QComboBox();self.pump.setMinimumWidth(110)
        self.go=QPushButton('Ver');self.go.clicked.connect(self.go_to_date)
        self.latest=QPushButton('Último día');self.latest.clicked.connect(self.go_latest)
        self.unfreeze=QPushButton('Seguir ratón');self.unfreeze.clicked.connect(self.follow_mouse)
        for w in (self.previous,self.date,self.window,self.next,self.pump,self.go,self.latest,self.unfreeze):tools.addWidget(w)
        tools.addStretch();layout.addLayout(tools)
        hint=QLabel('Arrastra para desplazarte · Rueda para acercar · Clic para fijar. Horas de la bomba. Fondo azul: sueño; beige: ejercicio.');hint.setObjectName('muted');hint.setWordWrap(True);layout.addWidget(hint)
        self.loading=QProgressBar();self.loading.setTextVisible(False);self.loading.setMaximumHeight(4);self.loading.setRange(0,1);self.loading.setValue(0);layout.addWidget(self.loading)
        self.range_label=QLabel('Abre esta pestaña para consultar el histórico.');self.range_label.setObjectName('muted');layout.addWidget(self.range_label)
        split=QSplitter(Qt.Orientation.Horizontal);layout.addWidget(split,1)
        self.canvas=pg.GraphicsLayoutWidget();self.canvas.setBackground('w');split.addWidget(self.canvas);self.plots=[]
        labels=(('Glucosa','mg/dL'),('Bolos / activa','U'),('Basal','U/h'),('Carbohidratos','g'))
        for row,(label,units) in enumerate(labels):
            plot=self.canvas.addPlot(row=row,col=0,axisItems={'bottom':WallAxis(orientation='bottom')})
            plot.setLabel('left',label,units=units);plot.showGrid(x=True,y=True,alpha=0.12);plot.setMenuEnabled(False)
            plot.getAxis('left').setWidth(92);plot.getViewBox().setMouseEnabled(x=True,y=False)
            plot.setClipToView(True);plot.addLegend(offset=(8,4),labelTextColor='#415870',labelTextSize='8pt')
            if row:plot.setXLink(self.plots[0])
            if row<3:plot.hideAxis('bottom')
            else:plot.getAxis('bottom').setHeight(38)
            self.canvas.ci.layout.setRowStretchFactor(row,4 if row==0 else 2);self.plots.append(plot)
        self.crosshairs=[]
        for plot in self.plots:
            line=pg.InfiniteLine(angle=90,movable=False,pen=pg.mkPen('#58778b',width=1,style=Qt.PenStyle.DashLine));plot.addItem(line,ignoreBounds=True);line.hide();self.crosshairs.append(line)
        self.tooltip=pg.TextItem(anchor=(0,0),color='#173d50',fill=(255,255,255,235),border='#bdcedd');self.plots[0].addItem(self.tooltip,ignoreBounds=True);self.tooltip.hide()
        self.proxy=pg.SignalProxy(self.canvas.scene().sigMouseMoved,rateLimit=30,slot=self._mouse_move)
        self.canvas.scene().sigMouseClicked.connect(self._click)
        self.plots[0].getViewBox().sigXRangeChanged.connect(self._range_changed)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(350);self.debounce.timeout.connect(self._load_view_range)
        panel=QWidget();sidebar=QVBoxLayout(panel);sidebar.setContentsMargins(12,0,8,0)
        self.instant=QLabel('Pasa el ratón sobre el gráfico');self.instant.setWordWrap(True);self.instant.setStyleSheet('font-weight:700;font-size:12pt');sidebar.addWidget(self.instant)
        self.values={}
        for title,fields in (('Valores observados',(('glucose','Glucosa'),('iob','Insulina activa'),('bolus','Bolo cercano'),('carbs','Carbohidratos cercanos'))),
                             ('Bomba en este instante',(('profile','Programa / perfil'),('basal_profile','Basal del perfil'),('carb_ratio','Ratio de carbohidratos'),('sensitivity','Sensibilidad'),('target','Objetivo'),('mode','Modo')))):
            box=QGroupBox(title);form=QVBoxLayout(box)
            for key,label in fields:
                cap=QLabel(label);cap.setObjectName('muted');value=QLabel('—');value.setTextFormat(Qt.TextFormat.PlainText);value.setWordWrap(True)
                value.setMinimumHeight(40);form.addWidget(cap);form.addWidget(value);self.values[key]=value
            sidebar.addWidget(box)
        self.detail=QLabel('');self.detail.setWordWrap(True);self.detail.setTextFormat(Qt.TextFormat.PlainText);self.detail.setObjectName('muted');sidebar.addWidget(self.detail);sidebar.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(panel);scroll.setMinimumWidth(270);scroll.setMaximumWidth(390);scroll.setFrameShape(QScrollArea.Shape.NoFrame);split.addWidget(scroll);split.setSizes([850,300])
        self.controls=(self.previous,self.next,self.date,self.window,self.pump,self.go,self.latest)

    def activate(self):
        if not self.initialized and not self.busy:
            self.initialized=True;self._run(lambda:timeline_bounds(self.database),'bounds')
    def _run(self,work,kind):
        if self.busy:return False
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
            if self.bounds.get('last'):self.go_latest()
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
        if self.bounds and self.bounds.get('last'):self.window.setCurrentIndex(3);self.request(day_start(self.bounds['last']),86400)
    def go_to_date(self):self.request(self.date.date().toString('yyyy-MM-dd')+'T00:00:00',self.window.currentData())
    def shift(self,direction):
        if self.current_start is not None:self.request(self.current_start+direction*self.current_width,self.current_width)
    def follow_mouse(self):self.frozen=False;self.unfreeze.setText('Seguir ratón')
    def reload(self):
        if self.busy:self._reload_after=True;return
        self.bundle=None;self.initialized=False
        if self.isVisible():self.activate()
    def _range_changed(self,*_):
        if not self._drawing and self.bundle:self.debounce.start()
    def _load_view_range(self):
        if not self.bundle:return
        left,right=self.plots[0].viewRange()[0]
        if right-left>self.MAX_WINDOW:
            self.request(left,self.MAX_WINDOW);return
        if left<self.bundle['cache_start'] or right>self.bundle['cache_end']:self.request(left,right-left)
        else:
            self.current_start=left;self.current_width=right-left;self._range_text()
    def _range_text(self):
        self.range_label.setText(iso(self.current_start).replace('T',' ')+'  →  '+iso(self.current_start+self.current_width).replace('T',' '))

    def render(self,bundle):
        self.bundle=bundle;self.frozen=False;self._drawing=True
        for p in self.plots:p.clear();p.legend.clear()
        self.crosshairs=[]
        for p in self.plots:
            line=pg.InfiniteLine(angle=90,movable=False,pen=pg.mkPen('#58778b',style=Qt.PenStyle.DashLine));p.addItem(line,ignoreBounds=True);self.crosshairs.append(line)
        data=bundle['data'];context=bundle['context'];self.point_lists={}
        observed_points=[p['x'] for key in ('glucose','boluses','carbs','basal','events') for p in data.get(key,[])]+[p['x'] for p in context.get('observed_iob',[])]
        observed_end=max(observed_points,default=bundle['cache_start'])
        modes=context.get('timelines',{}).get('mode',[])
        for index,observation in enumerate(modes):
            if observation.get('value') not in ('sleep','exercise'):continue
            a=max(observation['x'],bundle['cache_start']);b=min(modes[index+1]['x'] if index+1<len(modes) else observed_end,bundle['cache_end'],observed_end)
            for change in context.get('clock_changes',[]):
                if a<change['x']<b:b=change['x']
            if a>=b:continue
            color=(105,136,195,24) if observation['value']=='sleep' else (211,156,89,26)
            region=pg.LinearRegionItem((a,b),movable=False,brush=color,pen=pg.mkPen(None));region.setZValue(-20);self.plots[0].addItem(region)
        for key in ('glucose','boluses','carbs','basal','events'):
            points=sorted(data.get(key,[]),key=lambda p:p['x']);self.point_lists[key]=(points,[p['x'] for p in points])
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
            self.plots[0].plot(x,y,pen=pg.mkPen('#168f78',width=2),symbol='o',symbolSize=3,symbolBrush='#168f78',symbolPen=None,connect='finite',name='Glucosa')
            self.plots[0].setYRange(max(0,min(yv for yv in y if math.isfinite(yv))-25),max(yv for yv in y if math.isfinite(yv))+25)
        else:self.plots[0].setYRange(40,300)
        for p in glucose:
            if p.get('value') is None and p.get('details',{}).get('qualifier') in ('high','low'):
                high=p['details']['qualifier']=='high';mark=pg.TextItem('ALTA' if high else 'BAJA',color='#b26540',anchor=(.5,0 if high else 1))
                mark.setPos(p['x'],self.plots[0].viewRange()[1][1 if high else 0]);self.plots[0].addItem(mark,ignoreBounds=True)
        bg=[p for p in self.point_lists['glucose'][0] if p.get('details',{}).get('kind')=='bg' and p.get('value') is not None]
        if bg:self.plots[0].plot([p['x'] for p in bg],[p['value'] for p in bg],pen=None,symbol='d',symbolSize=8,symbolBrush='#597bb5',symbolPen=None,name='Glucemia introducida')
        boluses=[p for p in self.point_lists['boluses'][0] if p.get('value') is not None]
        if boluses:self._stems(self.plots[1],boluses,'#2876b8','Bolos','t')
        iobs=[p for p in context.get('observed_iob',[]) if p.get('value') is not None]
        if iobs:self.plots[1].plot([p['x'] for p in iobs],[p['value'] for p in iobs],pen=None,symbol='o',symbolSize=4,symbolPen=None,symbolBrush='#9268b0',name='Activa observada')
        self.plots[1].setYRange(0,max([p['value'] for p in boluses+iobs]+[1])*1.2)
        basal=[p for p in self.point_lists['basal'][0] if p.get('value') is not None]
        if basal:
            bx=[];by=[];profile=[];previous=None
            for p in basal:
                boundary=any(previous is not None and previous<=c['x']<=p['x'] for c in data.get('clock_changes',[]))
                if previous is not None and (p['x']-previous>720 or p['x']<=previous or boundary):bx.append(float('nan'));by.append(float('nan'));profile.append(float('nan'))
                rate=p.get('details',{}).get('profile_rate')
                bx.append(p['x']);by.append(p['value']);profile.append(rate if rate is not None else float('nan'));previous=p['x']
            self.plots[2].plot(bx,by,pen=pg.mkPen('#2876b8',width=1.5),stepMode='left',name='Tasa indicada')
            self.plots[2].plot(bx,profile,pen=pg.mkPen('#5cabb5',width=1,style=Qt.PenStyle.DashLine),stepMode='left',name='Perfil observado')
        self.plots[2].setYRange(0,max([p['value'] for p in basal]+[1])*1.15)
        carbs=[p for p in self.point_lists['carbs'][0] if p.get('value') is not None]
        if carbs:self._stems(self.plots[3],carbs,'#e49335','Carbohidratos','d')
        self.plots[3].setYRange(0,max([p['value'] for p in carbs]+[20])*1.2)
        for event in data.get('clock_changes',[]):
            for p in self.plots:p.addItem(pg.InfiniteLine(pos=event['x'],angle=90,pen=pg.mkPen('#d6a432',style=Qt.PenStyle.DashLine)),ignoreBounds=True)
        for e in data.get('events',[]):
            color='#b77564' if e.get('details',{}).get('kind') in ('alarm','alert','cgm_alert','suspend') else '#4866a1'
            mark=pg.ScatterPlotItem([e['x']],[self.plots[0].viewRange()[1][1]],symbol='d',size=6,brush=color,pen=None);self.plots[0].addItem(mark,ignoreBounds=True)
        self.tooltip=pg.TextItem(anchor=(0,0),color='#173d50',fill=(255,255,255,235),border='#bdcedd');self.plots[0].addItem(self.tooltip,ignoreBounds=True)
        self.plots[0].setXRange(bundle['view_start'],bundle['view_start']+bundle['view_width'],padding=0)
        self._drawing=False;self._range_text()
        warnings=data.get('warnings',[])+context.get('warnings',[])
        self.detail.setText('\n'.join(dict.fromkeys(warnings)))
        self.hover_at(bundle['view_start']+bundle['view_width']/2)

    @staticmethod
    def _stems(plot,points,color,name,symbol):
        x=[];y=[]
        for p in points:x.extend((p['x'],p['x'],float('nan')));y.extend((0,p['value'],float('nan')))
        plot.plot(x,y,pen=pg.mkPen(color,width=2),connect='finite')
        plot.plot([p['x'] for p in points],[p['value'] for p in points],pen=None,symbol=symbol,symbolSize=9,symbolBrush=color,symbolPen=None,name=name)
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
        if self.frozen or self.busy or not self.bundle:return
        pos=event[0]
        for plot in self.plots:
            vb=plot.getViewBox()
            if vb.sceneBoundingRect().contains(pos):self.hover_at(vb.mapSceneToView(pos).x());return
    def _click(self,event):
        if event.button()==Qt.MouseButton.LeftButton and self.bundle:
            self.frozen=not self.frozen;self.unfreeze.setText('Instante fijado' if self.frozen else 'Seguir ratón')
    def hover_at(self,x):
        if not self.bundle:return
        self.last_hover=x;stamp=iso(x);self.instant.setText(stamp.replace('T',' '))
        for line in self.crosshairs:line.setPos(x)
        ctx=context_at(self.bundle['context'],stamp);glucose=self.nearest('glucose',x,300)
        tolerance=min(300,max(45,self.current_width/100))
        bolus=self.nearest('boluses',x,tolerance);carbs=self.nearest('carbs',x,tolerance)
        self.set_value('glucose',self.point_text(glucose));self.set_value('bolus',self.point_text(bolus));self.set_value('carbs',self.point_text(carbs))
        for key in ('profile','basal_profile','carb_ratio','sensitivity','target','iob','mode'):
            observation=ctx.get(key) or {};value=observation.get('value');unit=observation.get('unit') or ''
            label='Sin dato confirmado' if value is None else (f'{value:.3f}'.rstrip('0').rstrip('.') if isinstance(value,(int,float)) else str(value))+' '+unit
            if key=='mode' and value is not None:label={'normal':'Normal','sleep':'Sueño','exercise':'Ejercicio','eating_soon':'Comida próxima'}.get(str(value),str(value))
            if key=='iob' and value is None and observation.get('last_observed_value') is not None:
                label+='\nÚltima lectura: '+str(observation['last_observed_value'])+' U'
            if observation.get('time'):label+='\nObservado '+str(observation['time']).replace('T',' ')
            self.set_value(key,label.strip())
        lines=[stamp.replace('T',' ')]
        for name,key in (('Glucosa','glucose'),('Activa','iob'),('Bolo cercano','bolus'),('Carbohidratos','carbs')):
            lines.append(name+': '+self.values[key].text().split('\n')[0])
        self.tooltip.setText('\n'.join(lines));self.tooltip.setAnchor((1 if x>sum(self.plots[0].viewRange()[0])/2 else 0,0));self.tooltip.setPos(x,self.plots[0].viewRange()[1][1]);self.tooltip.show()
        extra=[]
        for p in (glucose,bolus,carbs):
            if p:extra.append(str(p.get('source',''))+' · '+p['time'])
        event=self.nearest('events',x,tolerance)
        if event:extra.insert(0,event.get('details',{}).get('label','Evento')+' · '+event['time'])
        warnings=self.bundle['data'].get('warnings',[])+ctx.get('warnings',[])
        self.detail.setText('\n'.join(dict.fromkeys(warnings+extra)))
    def set_value(self,key,text):
        label=self.values[key];label.setText(text);label.setMinimumHeight(max(36,(text.count('\n')+1)*label.fontMetrics().lineSpacing()+6))
    @staticmethod
    def point_text(point):
        if not point:return 'Sin observación cercana'
        details=point.get('details',{})
        if details.get('ambiguous'):return 'Ambiguo · '+', '.join(details.get('alternatives',[]))+'\n'+point['time']
        if point.get('value') is None:
            return {'high':'ALTA · sin valor numérico','low':'BAJA · sin valor numérico'}.get(details.get('qualifier'),'Sin valor numérico')+'\n'+point['time']
        v=point['value'];text=f'{v:.3f}'.rstrip('0').rstrip('.') if isinstance(v,(int,float)) else str(v)
        return text+' '+str(point.get('unit',''))+'\n'+point['time'].replace('T',' ')
