"""Small, source-faithful messages for observations in the loaded chart window."""
from datetime import datetime,timedelta
from html import escape
import math
from .bolus_display import is_005_bolus,MARKED_BOLUS_LABEL
from .presentation_details import bolus_lines,sensor_lines,basal_lines
from .alert_details import alert_details

EPOCH=datetime(1970,1,1)
MODES={0:'Estándar',1:'Sueño',2:'Ejercicio',3:'Comida próxima'}
TITLES={'glucose':'Glucosa del sensor','bg':'Glucemia introducida','bolus':'Bolo',
        'carbs':'Carbohidratos','iob':'Insulina activa observada',
        'basal':'Tasa basal indicada','basal_profile':'Basal del perfil observada'}

def timestamp(value):
    if isinstance(value,(float,int)):value=(EPOCH+timedelta(seconds=value)).isoformat()
    try:return datetime.fromisoformat(value).strftime('%d/%m/%Y %H:%M:%S')
    except (ValueError,TypeError):return str(value or 'Hora no disponible')

def quantity(value,unit=''):
    if isinstance(value,bool) or value is None:return None
    if isinstance(value,(float,int)):
        if not math.isfinite(value):return None
        value=f'{value:.3f}'.rstrip('0').rstrip('.').replace('.',',')
    return str(value)+(' '+str(unit) if unit else '')

def message(kind,point):
    """Return plain title/body, preserving zeros, missing values and ambiguity."""
    if kind=='mode':
        body=['Observado · '+timestamp(point['observed_start'])]
        if point.get('confirmed_end'):body.append('Fin registrado · '+timestamp(point['end']))
        else:body.append('Sin fin confirmado en este tramo')
        if point.get('uncertain'):body.append('Modo no confirmado · revisar evidencia')
        return 'Modo · '+point['label'],body
    details=point.get('details',{})
    if kind=='glucose' and details.get('kind')=='bg':kind='bg'
    title=TITLES.get(kind,details.get('label') or 'Evento')
    if kind=='bg' and details.get('properties',{}).get('cgmCalibration')==1:title='Glucemia usada para calibración'
    if kind=='bolus' and is_005_bolus(point):title=MARKED_BOLUS_LABEL
    value=details.get('profile_rate') if kind=='basal_profile' else point.get('value')
    if kind=='event' and details.get('event_code')==229:
        value=MODES.get(details.get('properties',{}).get('currentUserMode'))
    body=[];formatted=quantity(value,point.get('unit',''))
    if details.get('ambiguous'):
        body.append('Observación ambigua')
        if details.get('alternatives'):body.append('Valores registrados: '+', '.join(map(str,details['alternatives'])))
    elif formatted is not None:body.append(formatted)
    elif details.get('qualifier') in ('high','low'):
        body.append('ALTA · sin valor numérico' if details['qualifier']=='high' else 'BAJA · sin valor numérico')
    body.append(timestamp(point.get('time')))
    if kind=='bolus' and bolus_lines(point)[0]!='Origen: Origen no identificado':body.extend(bolus_lines(point)[:1])
    if kind in ('glucose','bg'):body.extend(sensor_lines(point)[1:])
    if kind=='basal':body.extend(basal_lines(point)[1:])
    if kind=='event':body.extend(alert_details(details))
    if kind=='event' and details.get('prior_glucose'):
        observed=details['prior_glucose'];body.append('Glucosa previa: '+str(quantity(observed['value'],'mg/dL'))+' · '+timestamp(observed['time']))
        body.append('Lectura '+str(int(observed['age_seconds']))+' s anterior; asociación temporal, sin inferir la causa.')
    if kind=='event' and details.get('event_code')==447:
        p=details.get('properties',{});body.extend(label+': '+str(p[key])+unit for key,label,unit in (('sessionDuration','Duración registrada',' días'),('sessionStopReason','Motivo de fin (código)',''),('stopSessionCode','Código de parada','')) if key in p)
    if kind=='event':
        for key,m in details.get('measures',{}).items():body.append(key+': '+str(quantity(m.get('value'),m.get('unit',''))))
    if kind=='carbs' and details.get('timestamp_meaning')=='bolus_request_not_actual_meal_time':
        body.append('Hora de solicitud del bolo')
    if (details.get('revision_count') or 0)>1 or len(details.get('revision_ids') or ())>1:
        body.append('Varias revisiones de la observación')
    conflict=details.get('source_conflict')
    if conflict:
        body.append('Diferencia entre fuentes')
        for key,label in (('api_delivered_units','API'),('csv_delivered_units','CSV')):
            if key in conflict:body.append(label+' · '+str(quantity(conflict[key],'U')))
    return title,body

def format_messages(entries,limit=6):
    """Escape source text for Qt rich text; never combine doses or quantities."""
    html=[];plain=[]
    for kind,point in entries[:limit]:
        title,body=message(kind,point)
        html.append('<b>'+escape(title)+'</b><br>'+'<br>'.join(escape(line) for line in body))
        plain.append('\n'.join([title]+body))
    if len(entries)>limit:
        note=f'{len(entries)-limit} observaciones más · acerca el gráfico'
        html.append(escape(note));plain.append(note)
    return '<br><br>'.join(html),'\n\n'.join(plain)
