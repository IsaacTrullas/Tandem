"""Bounded, read-only series for the timeline. Plot coordinates are pump wall time.

The synthetic epoch on the x axis is not a conversion to UTC. Source timestamps,
identities and all uncertainties stay attached to the points. Quantities from
overlapping source families are never added together.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timedelta
import json
import math
from pathlib import Path
import sqlite3
from .last_events import load_predecessors

MAX_SOURCE_ROWS = 25000
EPOCH = datetime(1970, 1, 1)
EVENT_LABELS = {
    4:'Alerta', 5:'Alarma de bomba', 11:'Suministro suspendido',
    12:'Suministro reanudado', 13:'Cambio de hora', 14:'Cambio de fecha',
    33:'Llenado de cartucho', 61:'Llenado de cánula', 63:'Llenado de tubo',
    69:'Perfil de bomba', 229:'Cambio de modo', 230:'Cambio de control',
    369:'Alerta del sensor', 371:'Alerta del sensor reconocida',
    8:'Alarma reconocida',26:'Alerta desactivada',27:'Alerta reconocida',28:'Alarma desactivada',
    34:'Inicio de carga eléctrica',35:'Fin de carga eléctrica',
    394:'Incorporación a sesión del sensor',447:'Fin de sesión del sensor',
    370:'Alerta del sensor desactivada',313:'Estado diario de bomba',
}


def parse_local(value):
    if not isinstance(value, str):raise ValueError('La fecha debe ser texto ISO local')
    result = datetime.fromisoformat(value)
    if result.tzinfo is not None:raise ValueError('El gráfico usa el reloj local de la bomba, sin conversión UTC')
    return result


def wall_seconds(value):
    return (parse_local(value) - EPOCH).total_seconds()


def wall_time(value):
    return (EPOCH + timedelta(seconds=float(value))).isoformat()


def _numeric(value):
    return isinstance(value, (int,float)) and not isinstance(value,bool) and math.isfinite(value)


def _open(path):
    conn=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=30)
    conn.row_factory=sqlite3.Row;conn.execute('PRAGMA query_only=ON')
    return conn


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}


def _bounds(conn,tables):
    ranges={}
    if 'api_events' in tables:
        for r in conn.execute("""SELECT pump_serial,
            min(json_extract(values_json,'$.measurement_local_timestamp')) first,
            max(json_extract(values_json,'$.measurement_local_timestamp')) last
            FROM api_events WHERE kind='cgm' AND json_extract(values_json,'$.measurement_local_timestamp') IS NOT NULL
            GROUP BY pump_serial"""):
            if r['first'] and r['last']:ranges[r['pump_serial']]=[r['first'],r['last']]
    if 'glucose_readings' in tables and 'records' in tables:
        for r in conn.execute("""SELECT r.pump_serial,min(r.local_timestamp) first,max(r.local_timestamp) last
            FROM records r JOIN glucose_readings g ON g.record_id=r.id
            WHERE g.origin='sensor' GROUP BY r.pump_serial"""):
            if not r['first']:continue
            prior=ranges.get(r['pump_serial'])
            ranges[r['pump_serial']]=[min(prior[0],r['first']),max(prior[1],r['last'])] if prior else [r['first'],r['last']]
    devices=sorted(ranges,key=lambda d:ranges[d][1],reverse=True)
    return {'first':min((r[0] for r in ranges.values()),default=None),
            'last':max((r[1] for r in ranges.values()),default=None),
            'devices':devices,'device_ranges':{k:{'first':v[0],'last':v[1]} for k,v in ranges.items()}}


def timeline_bounds(dbpath):
    """Clinical sensor range, excluding 2025 setup/clock-only records."""
    with closing(_open(dbpath)) as conn:
        conn.execute('BEGIN')
        try:return _bounds(conn,_tables(conn))
        finally:conn.rollback()


def _point(stamp,value,unit,source,identity,details=None):
    return {'x':wall_seconds(stamp),'time':stamp,'value':value,'unit':unit,
            'source':source,'id':identity,'details':details or {}}


def load_timeline(dbpath,start,end,pump_serial=None):
    """Return only one selected interval, [start,end), at most seven days.

    Every query has a shared hard row budget; an overfull result is explicitly
    marked truncated. API CGM filtering uses measurement time inside SQLite so
    late-arriving sensor samples are not lost by a log-date-only restriction.
    """
    begin,finish=parse_local(start),parse_local(end)
    if not timedelta(0)<finish-begin<=timedelta(days=7):raise ValueError('Seleccione un periodo de hasta siete días')
    first,last=begin.isoformat(),finish.isoformat()
    result={'start':first,'end':last,'devices':[],'pump_serial':pump_serial,
            'glucose':[],'boluses':[],'carbs':[],'basal':[],'events':[],
            'clock_changes':[],'warnings':[],'truncated':False,'source_rows_loaded':0,
            'predecessors':{'boluses':[],'carbs':[]},'predecessor_source_rows_loaded':0,'predecessor_truncated':False}
    with closing(_open(dbpath)) as conn:
        conn.execute('BEGIN')
        try:
            tables=_tables(conn)
            # Device discovery uses aggregates, never full-history event objects.
            bounds=_bounds(conn,tables);result['devices']=bounds['devices']
            if pump_serial is None:pump_serial=next(iter(bounds['devices']),None)
            result['pump_serial']=pump_serial
            if pump_serial is None:return result
            if pump_serial not in bounds['devices']:raise ValueError('La bomba seleccionada no tiene datos de sensor')
            budget=MAX_SOURCE_ROWS
            def rows(sql,args=()):
                nonlocal budget
                if budget<=0:
                    result['truncated']=True;return []
                collected=list(conn.execute(sql+' LIMIT ?',tuple(args)+(budget+1,)))
                if len(collected)>budget:
                    collected=collected[:budget];result['truncated']=True
                budget-=len(collected);result['source_rows_loaded']+=len(collected)
                return collected
            def visible(stamp):
                try:return begin<=parse_local(stamp)<finish
                except (ValueError,TypeError):return False
            api=[];cgms=[];csv_glucose=[];csv_boluses=[]
            if 'api_events' in tables:
                cgms=rows("""SELECT id,device_id,identity_key,event_code,kind,local_timestamp,unit,value,values_json,
                    (SELECT count(*) FROM api_events revision WHERE revision.device_id=e.device_id
                        AND revision.identity_key=e.identity_key) revision_count
                    FROM api_events e WHERE pump_serial=? AND kind='cgm'
                    AND json_extract(values_json,'$.measurement_local_timestamp')>=?
                    AND json_extract(values_json,'$.measurement_local_timestamp')<?
                    ORDER BY json_extract(values_json,'$.measurement_local_timestamp'),id""",(pump_serial,first,last))
                # Include boundary phases so a delivery started at the edge is
                # associated with its completed event rather than drawn twice.
                lo=(begin-timedelta(days=1)).date().isoformat();hi=(finish+timedelta(days=1)).date().isoformat()
                api=rows("""SELECT id,device_id,identity_key,event_code,kind,local_timestamp,unit,value,values_json,
                    (SELECT count(*) FROM api_events revision WHERE revision.device_id=e.device_id
                        AND revision.identity_key=e.identity_key) revision_count
                    FROM api_events e WHERE pump_serial=? AND local_date>=? AND local_date<=?
                    AND event_code IN(3,4,5,8,11,12,13,14,16,20,21,26,27,28,33,34,35,55,59,61,63,64,65,66,69,229,230,279,280,313,369,370,371,394,447)
                    ORDER BY local_timestamp,id""",(pump_serial,lo,hi))
            if 'glucose_readings' in tables:
                csv_glucose=rows("""SELECT r.id,r.local_timestamp,r.clock_status,g.origin,g.glucose_mg_dl
                    FROM records r JOIN glucose_readings g ON g.record_id=r.id
                    WHERE r.pump_serial=? AND r.local_timestamp>=? AND r.local_timestamp<?
                    ORDER BY r.local_timestamp,r.id""",(pump_serial,first,last))
            if 'boluses' in tables:
                csv_boluses=rows("""SELECT r.local_timestamp,b.* FROM records r JOIN boluses b ON b.record_id=r.id
                    WHERE r.pump_serial=? AND r.local_timestamp>=? AND r.local_timestamp<?
                    ORDER BY r.local_timestamp,r.id""",(pump_serial,first,last))
            _build_series(result,cgms,api,csv_glucose,csv_boluses,visible)
            from .presentation_details import load_pdf_summary,alert_glucose_context
            result['events']=alert_glucose_context(result['events'],result['glucose'],result['clock_changes'])
            result['pdf_summary']=load_pdf_summary(conn,tables,first,last)
            previous,metrics,previous_warnings=load_predecessors(conn,tables,pump_serial,first)
            result['predecessors']=previous
            result['predecessor_source_rows_loaded']=metrics['source_rows_loaded']
            result['predecessor_truncated']=metrics['truncated']
            result['warnings'].extend(w for w in previous_warnings if w not in result['warnings'])
            if result['truncated']:result['warnings'].append('Periodo demasiado denso: reduzca el intervalo para consultar todos los puntos. No se ha interpolado ni promediado la información omitida.')
            for key in ('glucose','boluses','carbs','basal','events','clock_changes'):
                result[key].sort(key=lambda p:(p['x'],str(p['id'])))
            return result
        finally:conn.rollback()


def _build_series(result,cgms,api,csv_glucose,csv_boluses,visible):
    api_glucose=Counter();stages=defaultdict(list);requests=defaultdict(list);completed=[];phase_index=defaultdict(list)
    active_identities=defaultdict(list)
    for row in list(cgms)+list(api):active_identities[(row['device_id'],row['identity_key'])].append(row['id'])
    for row in cgms:
        data=json.loads(row['values_json']);stamp=data.get('measurement_local_timestamp')
        if not stamp or not visible(stamp):continue
        details={'kind':'cgm','log_time':row['local_timestamp'],'measurement_time':stamp,
                 'properties':data.get('properties',{}),'labels':data.get('labels',{}),
                 'qualifier':data.get('glucose_qualifier'),'identity_key':row['identity_key'],
                 'revision_count':row['revision_count'],
                 'revision_ids':active_identities[(row['device_id'],row['identity_key'])]}
        result['glucose'].append(_point(stamp,row['value'],'mg/dL','api_measurement',row['id'],details))
        if _numeric(row['value']):api_glucose[(parse_local(stamp),float(row['value']),'sensor')]+=1
    for row in api:
        code=row['event_code'];data=json.loads(row['values_json']);props=data.get('properties') or {};stamp=row['local_timestamp']
        if code in (20,21,55,59,65,66):phase_index[(row['device_id'],props.get('bolusId'))].append((row,data))
        if code==280:
            key=(row['device_id'],props.get('bolusId'))
            if props.get('bolusDeliveryStatus')==1:stages[key].append((row,props))
            elif props.get('bolusDeliveryStatus')==0:completed.append((row,props))
        elif code==64:requests[(row['device_id'],props.get('bolusId'))].append((row,props))
        if not stamp or not visible(stamp):continue
        if code==16 and row['unit']=='mg/dL' and _numeric(row['value']):
            result['glucose'].append(_point(stamp,row['value'],'mg/dL','api_bg',row['id'],
                {'kind':'bg','properties':props,'labels':data.get('labels',{}),'revision_count':row['revision_count']}))
            api_glucose[(parse_local(stamp),float(row['value']),'pump_entry')]+=1
        if code==279:
            commanded=(data.get('measures',{}).get('commandedRate') or {}).get('value')
            profile=(data.get('measures',{}).get('profileBasalRate') or {}).get('value')
            if _numeric(commanded):result['basal'].append(_point(stamp,commanded,'U/h','api_basal_commanded',row['id'],
                {'profile_rate':profile,'measures':data.get('measures',{}),'labels':data.get('labels',{}),'rate_meaning':'commanded_not_a_delivered_dose','properties':props}))
        if code in EVENT_LABELS:
            details={'event_code':code,'label':EVENT_LABELS[code],'kind':row['kind'],'properties':props,
                     'measures':data.get('measures',{}),
                     'labels':data.get('labels',{}),'state_transitions':data.get('state_transitions',[])}
            point=_point(stamp,None,'','api_event',row['id'],details)
            if code in (13,14):result['clock_changes'].append(point)
            else:result['events'].append(point)
    for row in csv_glucose:
        key=(parse_local(row['local_timestamp']),float(row['glucose_mg_dl']),row['origin'])
        if api_glucose[key]:api_glucose[key]-=1;continue
        result['glucose'].append(_point(row['local_timestamp'],row['glucose_mg_dl'],'mg/dL','csv_glucose',row['id'],
            {'kind':'cgm' if row['origin']=='sensor' else 'bg','origin':row['origin'],'clock_status':row['clock_status']}))
    consumed_csv=set();seen_requests=set()
    for row,props in completed:
        if not _numeric(row['value']) or row['unit']!='U':continue
        bid=props.get('bolusId');key=(row['device_id'],bid)
        starts=[r for r,p in stages.get(key,[]) if r['local_timestamp'] and row['local_timestamp'] and
                timedelta(0)<=parse_local(row['local_timestamp'])-parse_local(r['local_timestamp'])<=timedelta(hours=8)]
        # A repeated pump clock can produce several plausible start phases.
        start=max(starts,key=lambda r:parse_local(r['local_timestamp'])) if len(starts)==1 else None
        stamp=start['local_timestamp'] if start else row['local_timestamp']
        if not stamp or not visible(stamp):continue
        requested=[(r,p) for r,p in requests.get(key,[]) if r['local_timestamp'] and
                   timedelta(0)<=parse_local(stamp)-parse_local(r['local_timestamp'])<=timedelta(hours=8)]
        request=max(requested,key=lambda rp:parse_local(rp[0]['local_timestamp'])) if len(requested)==1 else None
        matches=[b for b in csv_boluses if parse_local(b['local_timestamp'])==parse_local(stamp)]
        details={'bolus_id':bid,'completed_at':row['local_timestamp'],'started_at':start['local_timestamp'] if start else None,
                 'start_properties':json.loads(start['values_json']).get('properties',{}) if start else {},
                 'labels':json.loads(row['values_json']).get('labels',{}),
                 'measures':json.loads(row['values_json']).get('measures',{}),
                 'timestamp_meaning':'delivery_start' if start else 'delivery_completion',
                 'properties':props,'start_candidates':len(starts),'csv_candidates':len(matches),
                 'revision_count':row['revision_count'],
                 'revision_ids':active_identities[(row['device_id'],row['identity_key'])]}
        details['phases']=[{'code':r['event_code'],'time':r['local_timestamp'],**d} for r,d in phase_index.get((row['device_id'],bid),[])
                          if r['local_timestamp'] and abs((parse_local(r['local_timestamp'])-parse_local(stamp)).total_seconds())<=8*3600]
        if len(matches)==1:
            match=matches[0];consumed_csv.add(match['record_id']);details['csv_record_id']=match['record_id']
            details['csv_values']=dict(match);details['source_association']='same_start_time_candidate_not_identity_proof'
            if _numeric(match['delivered_units']) and abs(row['value']-match['delivered_units'])>0.001+1e-12:
                details['source_conflict']={'api_delivered_units':row['value'],'csv_delivered_units':match['delivered_units']}
                warning='Hay bolos cuya dosis difiere entre API y CSV; consulte los valores originales del evento. No se han sumado las fuentes.'
                if warning not in result['warnings']:result['warnings'].append(warning)
        if request:
            rr,rp=request;details['request_at']=rr['local_timestamp'];details['carbohydrate_grams']=rp.get('carbAmount')
            seen_requests.add(rr['id'])
            if _numeric(rp.get('carbAmount')) and rp['carbAmount']>0 and visible(rr['local_timestamp']):
                result['carbs'].append(_point(rr['local_timestamp'],rp['carbAmount'],'g','api_bolus_request',rr['id'],
                    {'bolus_id':bid,'timestamp_meaning':'bolus_request_not_actual_meal_time','bolus_event_id':row['id'],
                     'revision_count':rr['revision_count'],
                     'revision_ids':active_identities[(rr['device_id'],rr['identity_key'])]}))
        result['boluses'].append(_point(stamp,row['value'],'U','api_bolus_completed',row['id'],details))
    # Requests can exist before the completed dose arrives. They remain request
    # inputs, not delivered insulin and not assertions of a meal time.
    for key,items in requests.items():
        for row,props in items:
            grams=props.get('carbAmount');stamp=row['local_timestamp']
            if row['id'] not in seen_requests and stamp and visible(stamp) and _numeric(grams) and grams>0:
                result['carbs'].append(_point(stamp,grams,'g','api_bolus_request',row['id'],
                    {'bolus_id':key[1],'timestamp_meaning':'bolus_request_not_actual_meal_time','delivery_confirmation':'not_linked',
                     'revision_count':row['revision_count'],
                     'revision_ids':active_identities[(row['device_id'],row['identity_key'])]}))
    for row in csv_boluses:
        details=dict(row);details['timestamp_meaning']='csv_declared_event_time_not_actual_meal_time'
        # A dose already associated with API can still carry the only available
        # carbohydrate entry. Deduplicate quantities independently.
        if row['record_id'] not in consumed_csv and _numeric(row['delivered_units']):
            result['boluses'].append(_point(row['local_timestamp'],row['delivered_units'],'U','csv_bolus',row['record_id'],details))
        grams=row['carbohydrate_grams']
        if _numeric(grams) and grams>0:
            # If an unmatched API request of the same quantity is very near the
            # CSV event, keep one marker with both candidate sources, not two
            # apparent meals. Multiple candidates remain explicit ambiguity.
            nearby=[p for p in result['carbs'] if p['value']==grams and abs(p['x']-wall_seconds(row['local_timestamp']))<=180]
            if len(nearby)==1:
                nearby[0]['details']['csv_record_id']=row['record_id'];nearby[0]['details']['source_association']='near_request_candidate'
            else:
                details['api_request_candidates']=len(nearby)
                result['carbs'].append(_point(row['local_timestamp'],grams,'g','csv_carbohydrates',row['record_id'],details))

