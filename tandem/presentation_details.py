"""Bounded source detail formatting; no treatment calculations or inferred settings."""
from datetime import datetime
from bisect import bisect_left,bisect_right
import json,math
ORIGINS={0:'Botón de bomba',1:'Pantalla de bomba',5:'Remoto',7:'Algoritmo',8:'Bluetooth',9:'Modo comida próxima',11:'Bluetooth con recomendación AID'}
def alert_glucose_context(events,glucose,clocks=()):
    samples=sorted((p for p in glucose if p.get('details',{}).get('kind','cgm')=='cgm'),key=lambda p:p['x']);xs=[p['x'] for p in samples];output=[]
    for event in events:
        copy=dict(event);copy['details']=dict(event.get('details',{}));output.append(copy)
        if copy['details'].get('event_code') not in (4,5,369):continue
        i=bisect_right(xs,event['x'])-1
        if i<0 or event['x']-xs[i]>600:continue
        sample=samples[i];group=samples[bisect_left(xs,xs[i]):i+1]
        if sample.get('value') is None or len({s.get('value') for s in group})>1 or (sample.get('details',{}).get('revision_count') or 0)>1 or any(sample['x']<=c['x']<=event['x'] for c in clocks):continue
        copy['details']['prior_glucose']={'value':sample['value'],'time':sample['time'],'age_seconds':event['x']-sample['x'],'source':sample.get('source'),'id':sample.get('id')}
    return output
def fmt(value,unit=''):
    if value is None:return 'No disponible'
    if isinstance(value,(int,float)) and not isinstance(value,bool):value=f'{value:.3f}'.rstrip('0').rstrip('.').replace('.',',')
    return str(value)+(' '+unit if unit else '')
def origin(point):
    return ORIGINS.get(point.get('details',{}).get('properties',{}).get('bolusSource'),'Origen no identificado')
def bolus_lines(point):
    if not point:return ['Sin registro anterior']
    d=point.get('details',{});csv=d.get('csv_values',d);props=d.get('properties',{});lines=['Origen: '+origin(point)]
    if props.get('bolusType') is not None:lines.append('Tipo: '+str(d.get('labels',{}).get('bolusType',props['bolusType'])))
    lines.append('Dosis total registrada: '+fmt(point.get('value'),'U'))
    requested=d.get('start_properties') or props
    for key,label in (('requestedNow','Solicitada inmediata'),('requestedLater','Solicitada extendida'),('correction','Corrección solicitada')):
        if isinstance(requested.get(key),(int,float)) and not isinstance(requested[key],bool):lines.append(label+': '+fmt(requested[key]*.001,'U'))
    if 'extendedDurationRequested' in props and props['extendedDurationRequested']:
        lines.append('Duración solicitada: '+fmt(props['extendedDurationRequested'],'min'))
    for key,label,unit in (('food_units','Alimento CSV','U'),('correction_units','Corrección CSV','U'),('extended_units','Extendida CSV','U'),('completion_status','Finalización CSV',''),('extended_status','Estado extendido CSV',''),('duration_minutes','Duración CSV','min')):
        if csv.get(key) is not None:lines.append(label+': '+fmt(csv[key],unit))
    phases=d.get('phases',[])
    for code in (65,66,20,21,59):
        group=[p for p in phases if p['code']==code]
        if len(group)>1:lines.append(f'Evento {code}: varias asociaciones posibles');continue
        if not group:continue
        phase=group[0];p=phase.get('properties',{});lines.append(f"Evento {code} · {phase['time']}")
        for field,label,unit in (('foodBolusSize','Alimento solicitado','U'),('correctionBolusSize','Corrección solicitada','U'),('totalBolusSize','Total solicitado','U'),('insulinRequested','Solicitado del componente','U'),('insulinDelivered','Entregado del componente','U'),('completionStatus','Estado final',''),('userOverride','Modificación del usuario',''),('declinedCorrection','Corrección rechazada','')):
            if field in p:lines.append(label+': '+fmt(phase.get('labels',{}).get(field,p[field]),unit))
    lines.append('Componentes y total se muestran por separado; no se suman de nuevo.')
    return lines
def sensor_lines(point,previous=None,clocks=()):
    if not point:return ['Sin lectura próxima']
    d=point.get('details',{});p=d.get('properties',{});labels=d.get('labels',{});lines=['Medición: '+point['time']]
    if d.get('kind')=='bg':
        if p.get('bgEntryType') in (0,1):lines.append('Entrada: '+{0:'manual mediante teclado',1:'valor tomado del MCG'}[p['bgEntryType']])
        if p.get('cgmCalibration') in (0,1):lines.append('Uso para calibración registrado: '+('sí' if p['cgmCalibration']==1 else 'no'))
    if 'rate' in p:lines.append('rate original: '+str(p['rate'])+' · escala pendiente de validar')
    if previous and previous.get('value') is not None and point.get('value') is not None and 0<point['x']-previous['x']<=600 and not any(previous['x']<c['x']<=point['x'] for c in clocks):
        if not any((v.get('details',{}).get('revision_count') or 0)>1 for v in (point,previous)):
            lines.append('Cambio medio entre lecturas: '+fmt((point['value']-previous['value'])*60/(point['x']-previous['x']),'mg/dL/min'))
    for key,label,unit in (('rssi','Señal recibida','dBm'),('algorithmState','Estado del sensor',''),('glucoseValueStatus','Estado de lectura','')):
        if key in p:lines.append(label+': '+fmt(labels.get(key,p[key]),unit))
    if d.get('log_time'):lines.append('Registro en bomba: '+d['log_time'])
    return lines
def basal_lines(point):
    if not point:return ['Sin tasa reciente observada']
    d=point.get('details',{});p=d.get('properties',{});lines=['Observación: '+point['time'],'Tasa indicada: '+fmt(point.get('value'),'U/h'),'Perfil: '+fmt(d.get('profile_rate'),'U/h')]
    if d.get('profile_rate') is not None:lines.append('Diferencia frente al perfil: '+fmt(point['value']-d['profile_rate'],'U/h'))
    for key,label in (('algorithmRate','Tasa del algoritmo'),('tempRate','Tasa temporal')):
        m=d.get('measures',{}).get(key)
        if m:lines.append(label+': '+fmt(m['value'],m['unit']))
    if 'commandedRateSource' in p:lines.append('Origen: '+str(d.get('labels',{}).get('commandedRateSource',p['commandedRateSource'])))
    lines.append('Son tasas indicadas; no cantidades de insulina suministrada.')
    return lines
def extended_span(point):
    d=point.get('details',{});csv=d.get('csv_values',d)
    a,b=csv.get('extended_start_local'),csv.get('extended_end_local')
    if not (a and b):
        starts=[p['time'] for p in d.get('phases',[]) if p['code']==59]
        ends=[p['time'] for p in d.get('phases',[]) if p['code']==21]
        if len(starts)!=1 or len(ends)!=1:return None
        a,b=starts[0],ends[0]
    try:
        start,end=datetime.fromisoformat(a),datetime.fromisoformat(b)
        if start.tzinfo or end.tzinfo or end<=start:return None
        return a,b
    except (ValueError,TypeError):return None

def load_pdf_summary(conn,tables,start,end):
    if not {'report_fields','pdf_pages','artifacts'}<=tables:return {}
    row=conn.execute('''SELECT a.id,a.filename,a.period_start,a.period_end FROM artifacts a
        WHERE a.period_start<=? AND a.period_end>=? AND EXISTS
        (SELECT 1 FROM pdf_pages p WHERE p.artifact_id=a.id)
        ORDER BY a.period_end DESC,a.id DESC LIMIT 1''',(end[:10],start[:10])).fetchone()
    if not row:return {}
    result=dict(artifact_id=row[0],filename=row[1],start=row[2],end=row[3])
    fields=list(conn.execute('''SELECT f.section,f.label,f.value_text,f.review_status,p.page_number
        FROM report_fields f JOIN pdf_pages p ON p.id=f.page_id WHERE p.artifact_id=?
        AND f.scope='summary_period' ORDER BY f.section,f.row_index LIMIT 121''',(row[0],)))
    result['fields']=[dict(section=r[0],label=r[1],value=r[2],review_status=r[3],page=r[4]) for r in fields[:120]]
    result['limited']=len(fields)>120
    if 'report_metrics' in tables:
        metrics=list(conn.execute('''SELECT m.metric_key,m.value,m.unit,m.qualifier,m.review_status,p.page_number
            FROM report_metrics m JOIN pdf_pages p ON p.id=m.page_id WHERE p.artifact_id=? ORDER BY m.id LIMIT 41''',(row[0],)))
        result['metrics']=[dict(key=r[0],value=r[1],unit=r[2],qualifier=r[3],review_status=r[4],page=r[5]) for r in metrics[:40]]
        result['limited']=result['limited'] or len(metrics)>40
    return result
