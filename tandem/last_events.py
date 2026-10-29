"""Bounded, read-only predecessors for the last-bolus/carbohydrate inspector.

SQL finds scalar anchor dates over the archive. Only small phase windows around
those anchors are materialized, never the complete historical event stream.
These observations are returned separately and are not chart markers.
"""
from datetime import timedelta

MAX_PREDECESSOR_ROWS = 2048
_FINITE = "typeof(value) IN ('real','integer') AND value BETWEEN -1.7976931348623157e308 AND 1.7976931348623157e308"
_API_COLUMNS = """e.id,e.device_id,e.identity_key,e.event_code,e.kind,e.local_timestamp,
    e.clock_status,e.unit,e.value,e.values_json,
    (SELECT count(*) FROM api_events revision WHERE revision.device_id=e.device_id
        AND revision.identity_key=e.identity_key) revision_count"""


def _merge_windows(windows):
    merged=[]
    for start,end in sorted(windows):
        if merged and start<=merged[-1][1]:merged[-1]=(merged[-1][0],max(end,merged[-1][1]))
        else:merged.append((start,end))
    return merged


def load_predecessors(conn,tables,pump_serial,cutoff):
    """Return the latest exact-time group before cutoff for each source series.

    Completed API deliveries retain the existing timeline's unique start-phase
    association. A completion up to eight hours after cutoff can therefore
    establish a delivery whose recorded start is before cutoff; its completion
    time remains attached as evidence. Unfinished requests are not insulin.
    """
    # Runtime import avoids a module cycle while reusing the one normalizer.
    from .timeline_data import _build_series,parse_local
    boundary=parse_local(cutoff)
    output={'boluses':[],'carbs':[]}
    metrics={'source_rows_loaded':0,'truncated':False}
    remaining=MAX_PREDECESSOR_ROWS
    anchors={}
    if 'api_events' in tables:
        for name,where in (
            ('api_bolus',"event_code=280 AND unit='U' AND "+_FINITE+
             " AND json_extract(values_json,'$.properties.bolusDeliveryStatus')=0"),
            ('api_carbs',"event_code=64 AND typeof(json_extract(values_json,'$.properties.carbAmount')) IN ('real','integer')"
             " AND json_extract(values_json,'$.properties.carbAmount')>0")):
            anchors[name]=conn.execute('SELECT max(local_timestamp) FROM api_events WHERE pump_serial=? AND local_timestamp<? AND '+where,
                                      (pump_serial,cutoff)).fetchone()[0]
    if 'boluses' in tables and 'records' in tables:
        for name,where in (('csv_bolus',"typeof(b.delivered_units) IN ('real','integer') AND b.delivered_units BETWEEN -1.7976931348623157e308 AND 1.7976931348623157e308"),
                           ('csv_carbs',"typeof(b.carbohydrate_grams) IN ('real','integer') AND b.carbohydrate_grams>0")):
            anchors[name]=conn.execute('SELECT max(r.local_timestamp) FROM records r JOIN boluses b ON b.record_id=r.id '
                                      'WHERE r.pump_serial=? AND r.local_timestamp<? AND '+where,
                                      (pump_serial,cutoff)).fetchone()[0]
    # The cutoff window also catches a long delivery completed just after the
    # selected boundary. Its phases can span eight hours, and a request may
    # precede the delivery start by another eight hours.
    windows=[(boundary-timedelta(hours=16),boundary+timedelta(hours=8))]
    for name,stamp in anchors.items():
        if not stamp:continue
        anchor=parse_local(stamp)
        if name=='api_bolus':windows.append((anchor-timedelta(hours=16),anchor))
        elif name=='csv_bolus':windows.append((anchor-timedelta(hours=8),anchor+timedelta(hours=8)))
        else:windows.append((anchor-timedelta(minutes=3),anchor+timedelta(minutes=3)))
    windows=_merge_windows(windows)

    def rows(sql,args):
        nonlocal remaining
        if remaining<=0:
            metrics['truncated']=True;return []
        collected=list(conn.execute(sql+' LIMIT ?',tuple(args)+(remaining+1,)))
        if len(collected)>remaining:
            collected=collected[:remaining];metrics['truncated']=True
        remaining-=len(collected);metrics['source_rows_loaded']+=len(collected)
        return collected

    api=[];csv=[]
    for start,end in windows:
        a,b=start.isoformat(),end.isoformat()
        if 'api_events' in tables:
            api.extend(rows('SELECT '+_API_COLUMNS+''' FROM api_events e
                WHERE pump_serial=? AND local_date>=? AND local_date<=?
                AND local_timestamp>=? AND local_timestamp<=? AND event_code IN (20,21,55,59,64,65,66,280)
                ORDER BY local_timestamp,id''',(pump_serial,start.date().isoformat(),end.date().isoformat(),a,b)))
        if 'boluses' in tables and 'records' in tables:
            csv.extend(rows('''SELECT r.local_timestamp,r.clock_status,b.* FROM records r
                JOIN boluses b ON b.record_id=r.id WHERE r.pump_serial=?
                AND r.local_timestamp>=? AND r.local_timestamp<=?
                ORDER BY r.local_timestamp,r.id''',(pump_serial,a,b)))
    if metrics['truncated']:
        return output,metrics,['Consulta previa limitada: no se ha elegido un último valor a partir de registros incompletos.']
    result={key:[] for key in ('glucose','boluses','carbs','basal','events','clock_changes','warnings')}
    def before(stamp):
        try:return parse_local(stamp)<boundary
        except (ValueError,TypeError):return False
    _build_series(result,[],api,[],csv,before)
    api_clocks={row['id']:row['clock_status'] for row in api}
    # The same CSV/API associations and conflicts as in the chart are retained.
    # Only the most recent normalized wall-time group survives this function.
    for kind in ('boluses','carbs'):
        points=result[kind]
        if not points:continue
        latest=max(p['x'] for p in points)
        group=sorted((p for p in points if p['x']==latest),key=lambda p:str(p['id']))
        clock=False
        if 'api_events' in tables:
            clock=conn.execute('''SELECT 1 FROM api_events WHERE pump_serial=? AND event_code IN (13,14)
                AND local_timestamp>=? AND local_timestamp<=? LIMIT 1''',
                (pump_serial,group[0]['time'],cutoff)).fetchone() is not None
        for point in group:
            point['details']['predecessor']=True
            if point['source'].startswith('api_'):
                point['details']['clock_status']=api_clocks.get(point['id'],'device_local_unresolved')
            if clock:point['details']['clock_change_between']=True
        output[kind]=group
    return output,metrics,result['warnings']
