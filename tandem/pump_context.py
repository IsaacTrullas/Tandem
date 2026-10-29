"""Bounded, read-only observations of historical pump settings and reported IOB.

These are observations, never a reconstructed complete settings schedule. Current
settings snapshots are deliberately not used. A naive axis value is wall-clock
seconds for plotting, not UTC. No insulin action curve is calculated.
"""
from __future__ import annotations
from bisect import bisect_right
from contextlib import closing
from datetime import datetime,timedelta
import json,math,sqlite3
from pathlib import Path

EPOCH=datetime(1970,1,1)
MAX_WINDOW_SECONDS=7*86400
MAX_CONTEXT_ROWS=20000
IOB_MAX_AGE_SECONDS=600
FIELDS=('profile','basal_profile','carb_ratio','sensitivity','target','iob','mode')
UNITS={'profile':None,'basal_profile':'U/h','carb_ratio':'g/U','sensitivity':'mg/dL/U','target':'mg/dL','iob':'U','mode':None}
MODES={0:'normal',1:'sleep',2:'exercise',3:'eating_soon'}
IOB_CODES=(16,20,21,55,64,81)  # iob uom=units in event_codes.json; selectedIob is an enum.
WINDOW_CODES=(3,13,14,16,20,21,55,57,64,65,69,81,229,279)

def wall_seconds(value):
    dt=datetime.fromisoformat(value) if isinstance(value,str) else value
    if dt.tzinfo is not None:raise ValueError('Se requiere la hora local de la bomba, sin zona inferida')
    return (dt-EPOCH).total_seconds()

def _numeric(value):
    return isinstance(value,(float,int)) and not isinstance(value,bool) and math.isfinite(value)

def _entry(row,value,unit=None,method='last_observed',**details):
    return {'x':wall_seconds(row['local_timestamp']),'time':row['local_timestamp'],'value':value,
            'unit':unit,'source':f"API · evento {row['event_code']}",'id':row['id'],'method':method,
            'sequence_group':row.get('sequence_group'),'sequence_number':row.get('sequence_number'),
            'device_id':row.get('device_id'),'details':details}

def _ascii_part(props,start,end):
    values=[]
    for n in range(start,end):
        value=props.get('name'+str(n))
        if isinstance(value,str) and len(value)==1:value=ord(value)
        if not isinstance(value,int) or isinstance(value,bool) or not 0<=value<=255:return None,False
        if value==0:return bytes(values).decode('ascii'),True
        # Source metadata declares ASCII. A high/control byte without an earlier
        # NUL is not decoded with replacement characters or presumed a proven
        # terminator (e.g. 0xFF padding). Show only a verified prefix as partial.
        if not 32<=value<=126:return (bytes(values).decode('ascii') if values else None),False
        values.append(value)
    return bytes(values).decode('ascii'),False

def _empty(field,method='unavailable',**extra):
    return {'value':None,'unit':UNITS[field],'time':None,'source':None,'method':method,**extra}

def load_context(dbpath,startISO,endISO,pump_serial=None):
    """Load at most seven days plus one SQL predecessor per required variable.

    Returned arrays are bounded by MAX_CONTEXT_ROWS, with no database queries in
    context_at(). If multiple pumps exist the caller must select one explicitly.
    """
    start,end=wall_seconds(startISO),wall_seconds(endISO)
    if end<start or end-start>MAX_WINDOW_SECONDS:raise ValueError('El contexto admite ventanas de hasta siete días')
    path=Path(dbpath).resolve()
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=30)) as conn:
        conn.row_factory=sqlite3.Row;conn.execute('PRAGMA query_only=ON');conn.execute('BEGIN')
        devices=[r[0] for r in conn.execute('SELECT pump_serial FROM api_events UNION SELECT pump_serial FROM api_snapshots UNION SELECT pump_serial FROM records ORDER BY pump_serial')]
        if pump_serial is None:
            if len(devices)>1:raise ValueError('Seleccione una bomba para consultar sus ajustes')
            pump_serial=devices[0] if devices else None
        if pump_serial is not None and pump_serial not in devices:raise ValueError('Bomba no disponible en el histórico API')
        context={'start':startISO,'end':endISO,'pump_serial':pump_serial,'devices':devices,
                 'timelines':{field:[] for field in FIELDS},'names':{},'clock_changes':[],
                 'profile_changes':[],'ambiguous_clock_ranges':[],'observed_iob':[],
                 'warnings':['Los ajustes son observaciones históricas; no una configuración completa reconstruida.']}
        if pump_serial is None:
            context['_xs']={field:[] for field in FIELDS};return context
        placeholders=','.join('?'*len(WINDOW_CODES))
        # local_date is indexed; the time clause retains sub-day bounds.
        raw_rows=conn.execute(f'''SELECT * FROM api_events WHERE pump_serial=? AND local_date>=? AND local_date<=?
            AND local_timestamp>=? AND local_timestamp<=? AND event_code IN ({placeholders})
            ORDER BY local_timestamp,sequence_group,sequence_number,id LIMIT ?''',
            (pump_serial,startISO[:10],endISO[:10],startISO,endISO,*WINDOW_CODES,MAX_CONTEXT_ROWS+1)).fetchall()
        if len(raw_rows)>MAX_CONTEXT_ROWS:raise ValueError('Demasiados eventos de contexto: reduzca la ventana temporal')
        selected={r['id']:dict(r) for r in raw_rows}
        predicates=[
            "event_code=3 AND json_type(raw_json,'$.eventProperties.idp')='integer'",
            "event_code=69 AND json_extract(raw_json,'$.eventProperties.status')=3",
            "event_code IN (13,14)",
            "event_code=229",
            "event_code IN (3,279)",
            "event_code=64 AND json_extract(raw_json,'$.eventProperties.carbRatio')>0",
            "event_code IN (16,65) AND json_extract(raw_json,'$.eventProperties.isf')>0",
            "event_code IN (16,65) AND json_extract(raw_json,'$.eventProperties.targetBg')>0",
            f"event_code IN ({','.join(map(str,IOB_CODES))}) AND json_type(raw_json,'$.eventProperties.iob') IN ('integer','real')",
        ]
        for predicate in predicates:
            row=conn.execute(f'''SELECT * FROM api_events WHERE pump_serial=? AND local_date<=? AND local_timestamp<? AND ({predicate})
                ORDER BY local_date DESC,local_timestamp DESC,sequence_group DESC,sequence_number DESC,id DESC LIMIT 1''',(pump_serial,startISO[:10],startISO)).fetchone()
            if row:selected[row['id']]=dict(row)
        # Profile names are split across messages69/57. Retrieve only the latest
        # earlier pair for IDs actually referenced by this bounded window.
        profile_ids=set()
        for row in selected.values():
            props=json.loads(row['raw_json']).get('eventProperties') or {}
            if row['event_code'] in (3,57,69) and isinstance(props.get('idp'),int):profile_ids.add(props['idp'])
        for pid in profile_ids:
            for code in (69,57):
                row=conn.execute('''SELECT * FROM api_events WHERE pump_serial=? AND event_code=? AND local_date<=? AND local_timestamp<?
                  AND json_extract(raw_json,'$.eventProperties.idp')=? ORDER BY local_date DESC,local_timestamp DESC,id DESC LIMIT 1''',
                  (pump_serial,code,startISO[:10],startISO,pid)).fetchone()
                if row:selected[row['id']]=dict(row)
        rows=sorted(selected.values(),key=lambda r:(r['local_timestamp'],r.get('sequence_group') or 0,r.get('sequence_number') or 0,r['id']))
        # An event identity with different raw revisions must not be silently
        # chosen as the historical truth.
        revisions={}
        for row in rows:
            key=(row['device_id'],row['identity_key'])
            if key not in revisions:
                revisions[key]=conn.execute('SELECT count(*) FROM api_events WHERE device_id=? AND identity_key=?',key).fetchone()[0]>1
        name_first={};active_pid=None
        def add(field,row,value,method='last_observed',**details):
            if revisions[(row['device_id'],row['identity_key'])]:value=None;method='ambiguous_source_revision'
            context['timelines'][field].append(_entry(row,value,UNITS[field],method,**details))
        for row in rows:
            raw=json.loads(row['raw_json']);props=raw.get('eventProperties') or {};code=row['event_code'];x=wall_seconds(row['local_timestamp'])
            if code in (13,14):
                context['clock_changes'].append(_entry(row,None,method='clock_change',properties=props))
                if code==13 and all(_numeric(props.get(k)) for k in ('timePrior','timeAfter')):
                    before,after=props['timePrior']/1000,props['timeAfter']/1000
                    if 0<=before<86400 and 0<=after<86400 and before!=after:
                        midnight=wall_seconds(row['local_timestamp'][:10]+'T00:00:00')
                        context['ambiguous_clock_ranges'].append((midnight+min(before,after),midnight+max(before,after)))
                elif code==14:
                    midnight=wall_seconds(row['local_timestamp'][:10]+'T00:00:00');context['ambiguous_clock_ranges'].append((midnight,midnight+86400))
            if code==69:
                pid=props.get('idp');name,terminated=_ascii_part(props,0,8)
                if pid is not None and name is not None:
                    name_first[pid]=(row,name,terminated)
                    context['names'].setdefault(pid,[]).append(_entry(row,name.rstrip() if terminated else name+'…',method='observed_name',complete=terminated))
                if props.get('status')==3 and isinstance(pid,int):
                    add('profile',row,pid,'observed_activation',profile_id=pid)
                    context['profile_changes'].append(x);active_pid=pid
            if code==57:
                pid=props.get('idp');second,terminated=_ascii_part(props,8,16);first=name_first.get(pid)
                # A NUL in message69 already terminates the complete name. The
                # unused continuation can contain non-ASCII padding and must
                # never be appended. Partial first chunks cannot skip bad bytes.
                if first and not first[2] and len(first[1])==8 and second is not None and abs(x-wall_seconds(first[0]['local_timestamp']))<=5:
                    name=(first[1]+second).rstrip()
                    context['names'].setdefault(pid,[]).append(_entry(row,name if terminated else name+'…',method='observed_name',complete=terminated))
            if code==3:
                pid=props.get('idp')
                if isinstance(pid,int):
                    if active_pid is not None and pid!=active_pid:context['profile_changes'].append(x)
                    active_pid=pid;add('profile',row,pid,'observed_basal_profile',profile_id=pid)
                value=props.get('baseBasalRate')
                if _numeric(value) and value>=0:add('basal_profile',row,value,profile_id=active_pid)
            elif code==279:
                value=props.get('profileBasalRate')
                if _numeric(value) and value>=0:add('basal_profile',row,value*.001,profile_id=active_pid)
            if code==64:
                value=props.get('carbRatio')
                if _numeric(value) and value>0:add('carb_ratio',row,value*.001,profile_id=active_pid,bolus_id=props.get('bolusId'))
            if code in (16,65):
                for field,source_field in (('sensitivity','isf'),('target','targetBg')):
                    value=props.get(source_field)
                    if _numeric(value) and value>0:add(field,row,value,profile_id=active_pid,bolus_id=props.get('bolusId'))
            if code in IOB_CODES:
                value=props.get('iob')
                if _numeric(value) and 0<=value<=1000:
                    add('iob',row,value,'reported_iob',selected_iob=props.get('selectedIob'),source_field='iob')
            if code==229:
                value=MODES.get(props.get('currentUserMode'))
                if value is not None:add('mode',row,value,'observed_state')
        # Retain only one predecessor per field after interpretation plus bounded
        # in-window values. Never retain a complete history in the UI process.
        for field,items in context['timelines'].items():
            earlier=[o for o in items if o['x']<start];inside=[o for o in items if start<=o['x']<=end]
            context['timelines'][field]=(earlier[-1:] if earlier else [])+inside
        context['profile_changes']=sorted(set(context['profile_changes']))
        context['clock_changes'].sort(key=lambda o:o['x'])
        context['_xs']={field:[o['x'] for o in items] for field,items in context['timelines'].items()}
        context['_clock_xs']=[o['x'] for o in context['clock_changes']]
        context['_name_xs']={pid:[o['x'] for o in items] for pid,items in context['names'].items()}
        context['observed_iob']=[dict(o) for o in context['timelines']['iob'] if start<=o['x']<=end and o['value'] is not None]
        context['loaded_rows']=len(rows)
        if context['clock_changes']:context['warnings'].append('Hay cambios de reloj; no se prolongan ajustes a través de ellos sin una observación posterior.')
        if any(revisions.values()):context['warnings'].append('Hay revisiones de una identidad de evento; sus valores quedan ambiguos.')
        return context

def context_at(context,whenISO):
    """Resolve last observations in memory; never query or interpolate values."""
    x=wall_seconds(whenISO)
    result={'warnings':list(context.get('warnings',[]))}
    if not wall_seconds(context['start'])<=x<=wall_seconds(context['end']):
        result.update({field:_empty(field,'outside_loaded_window') for field in FIELDS})
        result['warnings'].append('El instante queda fuera de la ventana cargada.');return result
    clock_xs=context.get('_clock_xs',[]);clock_i=bisect_right(clock_xs,x)-1
    clock_barrier=clock_xs[clock_i] if clock_i>=0 else float('-inf')
    profile_xs=context.get('profile_changes',[]);profile_i=bisect_right(profile_xs,x)-1
    profile_barrier=profile_xs[profile_i] if profile_i>=0 else float('-inf')
    clock_ambiguous=any(a<=x<=b for a,b in context.get('ambiguous_clock_ranges',[]))
    for field in FIELDS:
        items=context.get('timelines',{}).get(field,[]);xs=context.get('_xs',{}).get(field,[]);i=bisect_right(xs,x)-1
        if i<0:result[field]=_empty(field);continue
        item=dict(items[i]);item['age_seconds']=x-item['x'];item['last_observed_value']=item['value']
        barrier=clock_barrier if field in ('profile','mode','iob') else max(clock_barrier,profile_barrier)
        if clock_ambiguous:item['value']=None;item['method']='ambiguous_clock_interval'
        elif item['x']<=barrier:item['value']=None;item['method']='invalidated_by_clock_or_profile_change'
        elif field=='iob' and item['age_seconds']>IOB_MAX_AGE_SECONDS:item['value']=None;item['method']='stale_iob_observation'
        # Multiple values at exactly one wall time cannot be silently reduced to
        # a current IOB/settings value, including repeated times after DST.
        j=i
        while j>0 and xs[j-1]==item['x']:j-=1
        observed={str(o['value']) for o in items[j:i+1]}
        if len(observed)>1:
            item['value']=None;item['method']='ambiguous_same_wall_time';item['candidates']=[o['value'] for o in items[j:i+1]]
        result[field]=item
    profile=result['profile'];pid=profile.get('value')
    if pid is not None:
        profile['profile_id']=pid;names=context.get('names',{}).get(pid,[]);name_xs=context.get('_name_xs',{}).get(pid,[]);index=bisect_right(name_xs,x)-1
        profile['value']=names[index]['value'] if index>=0 else f'Programa {pid}'
        profile['name_complete']=names[index]['details'].get('complete',False) if index>=0 else False
    if clock_ambiguous:result['warnings'].append('Este intervalo tiene un salto/repetición del reloj y no identifica de forma unívoca los ajustes.')
    return result
