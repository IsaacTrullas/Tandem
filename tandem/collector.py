"""Read-only remote collection; immutable evidence and conservative cross-source links."""
from __future__ import annotations
import json, sqlite3, time, uuid
from collections import Counter
from contextlib import contextmanager, closing
from datetime import date, datetime, timedelta
from pathlib import Path
from .db import connect, backup, digest, dumps, now

from .event_decode import VERSION as DECODER_VERSION

@contextmanager
def writer_lock(dbpath):
    """OS releases the lock after a crash; never delete a possibly live lock file."""
    path=Path(str(dbpath)+'.collect.lock');path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open('a+b')
    if path.stat().st_size==0:handle.write(b'0');handle.flush()
    try:
        handle.seek(0)
        if __import__('os').name=='nt':
            import msvcrt
            try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
            except OSError:raise RuntimeError('Otra actualización está en curso') from None
        else:
            import fcntl
            try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except OSError:raise RuntimeError('Otra actualización está en curso') from None
        yield
    finally:handle.close()

def payload(conn,run,body,endpoint,device=None,start=None,end=None):
    if not isinstance(body,bytes):raise ValueError('La respuesta debe conservar sus bytes originales')
    sha=digest(body)
    with conn:
        conn.execute('INSERT OR IGNORE INTO api_payloads(sha256,content,byte_count,received_at) VALUES(?,?,?,?)',(sha,body,len(body),now()))
        pid=conn.execute('SELECT id FROM api_payloads WHERE sha256=?',(sha,)).fetchone()[0]
        rid=conn.execute('INSERT INTO api_receipts(run_id,payload_id,endpoint,device_id,start_date,end_date,status) VALUES(?,?,?,?,?,?,?)',
          (run,pid,endpoint,device,start,end,'received')).lastrowid
    return pid,rid

def parse_body(body):
    def invalid(_):raise ValueError('Número JSON no finito')
    obj=json.loads(body,parse_constant=invalid)
    if not isinstance(obj,dict):raise ValueError('Esquema API inesperado')
    # Fail visibly rather than claiming completion on a new pagination contract.
    for key in ('next','nextPage','nextCursor','continuationToken','hasMore','truncated'):
        if obj.get(key):raise ValueError('Respuesta paginada o truncada no compatible')
    return obj

def ingest_pumper(conn,run,body):
    pid,rid=payload(conn,run,body,'pumper')
    try:
        obj=parse_body(body);pumps=obj.get('pumps')
        if not isinstance(pumps,list) or not pumps:raise ValueError('No hay bombas disponibles en la respuesta')
        ids=set()
        with conn:
            for pump in pumps:
                if not isinstance(pump,dict) or not pump.get('assignmentId') or not pump.get('serialNumber'):raise ValueError('Bomba sin identidad')
                device=str(pump['assignmentId']);uuid.UUID(device)
                if device in ids:raise ValueError('Identidad de bomba repetida')
                ids.add(device)
                conn.execute('INSERT OR IGNORE INTO api_snapshots(payload_id,device_id,pump_serial,received_at,uploaded_at_source,details_json) VALUES(?,?,?,?,?,?)',
                  (pid,device,str(pump['serialNumber']),now(),pump.get('lastUploadDate'),dumps(pump)))
            conn.execute("UPDATE api_receipts SET status='complete' WHERE id=?",(rid,))
        return pumps
    except (ValueError,TypeError,KeyError):
        with conn:conn.execute("UPDATE api_receipts SET status='rejected',error_code='metadata_schema' WHERE id=?",(rid,))
        raise ValueError('Metadatos API inesperados; respuesta original conservada') from None

def ingest_logs(conn,run,body,device,serial,start,end):
    from .event_decode import decode
    pid,rid=payload(conn,run,body,'pump-logs',device,start,end)
    try:
        obj=parse_body(body)
        if not isinstance(obj.get('events'),list) or not isinstance(obj.get('clockChanges'),list):raise ValueError('Faltan colecciones de eventos')
        new=0
        with conn:
            for stream in ('events','clockChanges'):
                occurrences=Counter()
                for i,event in enumerate(obj[stream]):
                    if not isinstance(event,dict):raise ValueError('Evento inválido')
                    if event.get('deviceAssignmentId',device)!=device:raise ValueError('Evento de otra bomba')
                    raw=dumps(event);sha=digest(raw.encode());occurrences[sha]+=1
                    sg,sn=event.get('sequenceGroup'),event.get('sequenceNumber')
                    has_id=all(isinstance(v,int) and not isinstance(v,bool) for v in (sg,sn))
                    identity=f'{sg}:{sn}' if has_id else f'{sha}:{occurrences[sha]}'
                    decoded=decode(event)
                    stamp=decoded.get('local_timestamp')
                    # Only wall-clock is cross-matched. Never reinterpret estimatedDateTime's Z.
                    if stamp:
                        dt=datetime.fromisoformat(stamp)
                        if dt.tzinfo:raise ValueError('pumpDateTime dejó de ser hora local')
                        if stream=='events' and not start<=dt.date().isoformat()<=end:raise ValueError('Evento fuera de ventana')
                    code=event.get('eventCode')
                    if not isinstance(code,int) or isinstance(code,bool):raise ValueError('Código de evento inválido')
                    cur=conn.execute('''INSERT OR IGNORE INTO api_events(device_id,pump_serial,identity_key,identity_method,
                      sequence_group,sequence_number,event_code,event_name,kind,local_timestamp,local_date,clock_status,
                      unit,value,values_json,decode_status,raw_json,sha256,decoder_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                      (device,str(serial),identity,'sequence' if has_id else 'content_occurrence',sg if has_id else None,sn if has_id else None,
                       code,decoded.get('event_name') or decoded.get('values',{}).get('event_name'),decoded['kind'],stamp,stamp[:10] if stamp else None,
                       'device_local_unresolved',decoded.get('unit'),decoded.get('value'),dumps(decoded['values']),decoded['decode_status'],raw,sha,DECODER_VERSION))
                    new+=cur.rowcount
                    eid=conn.execute('SELECT id FROM api_events WHERE device_id=? AND identity_key=? AND sha256=?',(device,identity,sha)).fetchone()[0]
                    conn.execute('INSERT OR IGNORE INTO api_event_sources VALUES(?,?,?,?)',(eid,pid,stream,i))
                    actual=conn.execute('SELECT event_id FROM api_event_sources WHERE payload_id=? AND stream=? AND ordinal=?',(pid,stream,i)).fetchone()[0]
                    if actual!=eid:raise ValueError('Conflicto de procedencia de evento')
            conn.execute('INSERT INTO api_windows(receipt_id,device_id,start_date,end_date,event_count,clock_count,completed_at) VALUES(?,?,?,?,?,?,?)',
              (rid,device,start,end,len(obj['events']),len(obj['clockChanges']),now()))
            conn.execute("UPDATE api_receipts SET status='complete' WHERE id=?",(rid,))
        return {'new_events':new,'events_received':len(obj['events']),'clock_changes_received':len(obj['clockChanges'])}
    except (ValueError,TypeError,KeyError):
        with conn:conn.execute("UPDATE api_receipts SET status='rejected',error_code='event_schema' WHERE id=?",(rid,))
        raise ValueError('Esquema o rango API inesperado; respuesta conservada y ventana pendiente') from None

def windows(conn,pump,since=None,until=None):
    """Earliest uncovered day, then overlap. A later successful window cannot hide a gap."""
    available=pump.get('availableDataRange') or {}
    rawstart=available.get('start');rawend=available.get('end') or pump.get('maxDateOfEvents')
    if not rawstart or not rawend:
        if rawstart or rawend or pump.get('lastUploadDate') or pump.get('settings'):
            raise ValueError('La bomba tiene subidas pero falta su rango de datos')
        return []
    first=date.fromisoformat(str(rawstart)[:10]);last=date.fromisoformat(str(rawend)[:10])
    if until:last=min(last,date.fromisoformat(until))
    if since:cursor=max(first,date.fromisoformat(since))
    else:
        cursor=first
        for r in conn.execute('SELECT start_date,end_date FROM api_windows WHERE device_id=? ORDER BY start_date,end_date',(pump['assignmentId'],)):
            a,b=date.fromisoformat(r[0]),date.fromisoformat(r[1])
            if a>cursor:break
            if b>=cursor:cursor=b+timedelta(days=1)
        cursor=max(first,min(cursor,last)-timedelta(days=6))
    result=[]
    while cursor<=last:
        stop=min(cursor+timedelta(days=27),last);result.append((cursor.isoformat(),stop.isoformat()));cursor=stop+timedelta(days=1)
    return result

def reconcile(conn):
    """Links are evidence, never a destructive merge or duplicate insulin dose."""
    with conn:
        conn.execute('CREATE TEMP TABLE IF NOT EXISTS wanted_links(event_id INTEGER NOT NULL,source_table TEXT NOT NULL,source_id INTEGER NOT NULL,relation TEXT NOT NULL,PRIMARY KEY(event_id,source_table,source_id,relation))')
        conn.execute('DELETE FROM wanted_links')
        for e in conn.execute('SELECT * FROM api_events WHERE local_timestamp IS NOT NULL'):
            candidates=[]
            matched_stamp=json.loads(e['values_json']).get('measurement_local_timestamp',e['local_timestamp']) if e['kind']=='cgm' else e['local_timestamp']
            if e['kind'] in ('cgm','bg') and e['unit']=='mg/dL':
                kind='MCG' if e['kind']=='cgm' else 'GLUCOSA'
                candidates=conn.execute('''SELECT r.id,g.glucose_mg_dl val FROM records r JOIN glucose_readings g ON g.record_id=r.id
                  WHERE r.kind=? AND r.pump_serial=? AND r.local_timestamp=?''',(kind,e['pump_serial'],matched_stamp)).fetchall()
            # Code280 deliveredTotal is the verified full total. Component boluses stay separate.
            elif e['kind']=='bolus_completed' and e['event_code']==280 and e['unit']=='U':
                candidates=conn.execute('''SELECT r.id,b.delivered_units val FROM records r JOIN boluses b ON b.record_id=r.id
                  WHERE r.pump_serial=? AND r.local_timestamp=?''',(e['pump_serial'],e['local_timestamp'])).fetchall()
            for r in candidates:
                equal=e['value'] is not None and r['val'] is not None and abs(e['value']-r['val'])<0.00001
                relation='same_time_value_candidate' if equal else 'same_time_value_conflict'
                conn.execute('INSERT OR IGNORE INTO source_links(event_id,source_table,source_id,relation,details_json) VALUES(?,?,?,?,?)',
                  (e['id'],'records',r['id'],relation,dumps({'api_value':e['value'],'csv_value':r['val'],'match_timestamp':matched_stamp,'timestamp_source':'sensor_measurement' if e['kind']=='cgm' else 'pump_log','candidate_count':len(candidates),'identity_confirmed':False})))
                conn.execute('INSERT OR IGNORE INTO wanted_links VALUES(?,?,?,?)',(e['id'],'records',r['id'],relation))
                conn.execute('UPDATE source_links SET details_json=? WHERE event_id=? AND source_table=? AND source_id=? AND relation=?',
                    (dumps({'api_value':e['value'],'csv_value':r['val'],'match_timestamp':matched_stamp,'timestamp_source':'sensor_measurement' if e['kind']=='cgm' else 'pump_log','candidate_count':len(candidates),'identity_confirmed':False}),e['id'],'records',r['id'],relation))
            # A document-day link is context only, never a claim that one icon matches one event.
            for panel in conn.execute('SELECT id FROM daily_panels WHERE local_date=?',(e['local_date'],)):
                conn.execute('INSERT OR IGNORE INTO source_links(event_id,source_table,source_id,relation,details_json) VALUES(?,?,?,?,?)',
                  (e['id'],'daily_panels',panel[0],'same_day_context',dumps({'identity_confirmed':False})))
                conn.execute('INSERT OR IGNORE INTO wanted_links VALUES(?,?,?,?)',(e['id'],'daily_panels',panel[0],'same_day_context'))
        conn.execute('''DELETE FROM source_links WHERE NOT EXISTS(SELECT 1 FROM wanted_links w WHERE w.event_id=source_links.event_id
            AND w.source_table=source_links.source_table AND w.source_id=source_links.source_id AND w.relation=source_links.relation)''')
    return dict(conn.execute('SELECT relation,count(*) FROM source_links GROUP BY relation'))

def audit_api(conn):
    return {
      'payload_hash_errors':[r['id'] for r in conn.execute('SELECT id,sha256,content FROM api_payloads') if digest(r['content'])!=r['sha256']],
      'event_hash_errors':[r['id'] for r in conn.execute('SELECT id,sha256,raw_json FROM api_events') if digest(r['raw_json'].encode())!=r['sha256']],
      'events_without_source':conn.execute('SELECT count(*) FROM api_events e WHERE NOT EXISTS(SELECT 1 FROM api_event_sources s WHERE s.event_id=e.id)').fetchone()[0],
      'identity_revisions':conn.execute('SELECT count(*) FROM (SELECT 1 FROM api_events GROUP BY device_id,identity_key HAVING count(*)>1)').fetchone()[0],
      'unknown_events':conn.execute("SELECT count(*) FROM api_events WHERE decode_status NOT IN ('decoded','classified')").fetchone()[0],
      'received_windows':conn.execute('SELECT count(*) FROM api_windows').fetchone()[0],
      'pending_receipts':conn.execute("SELECT count(*) FROM api_receipts WHERE status!='complete'").fetchone()[0],
      'cross_source_conflicts':conn.execute("SELECT count(*) FROM source_links WHERE relation='same_time_value_conflict'").fetchone()[0]}

def redecode(conn):
    """Rebuild versioned interpretations without changing identities or raw evidence."""
    from .event_decode import decode
    count=0
    with conn:
        for row in conn.execute('SELECT id,raw_json FROM api_events WHERE decoder_version!=?',(DECODER_VERSION,)):
            d=decode(json.loads(row['raw_json']));stamp=d.get('local_timestamp')
            conn.execute('''UPDATE api_events SET event_name=?,kind=?,local_timestamp=?,local_date=?,unit=?,value=?,values_json=?,
              decode_status=?,decoder_version=? WHERE id=?''',(d.get('event_name') or d['values'].get('event_name'),d['kind'],stamp,
                stamp[:10] if stamp else None,d.get('unit'),d.get('value'),dumps(d['values']),d['decode_status'],DECODER_VERSION,row['id']))
            count+=1
    return count

def status_summary(dbpath):
    p=Path(dbpath).resolve()
    if not p.exists():return {'status':'not_initialized'}
    with closing(sqlite3.connect(p.as_uri()+'?mode=ro',uri=True)) as c:
        c.row_factory=sqlite3.Row
        tables={r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        counts={name:c.execute('SELECT count(*) FROM '+name).fetchone()[0] for name in ('records','pdf_pages','api_events','api_snapshots','source_links') if name in tables}
        runs=[dict(r) for r in c.execute('SELECT * FROM api_runs ORDER BY id DESC LIMIT 5')] if 'api_runs' in tables else []
        return {'tables':counts,'api_runs':runs,'api_authenticated':any(r['status']=='complete' for r in runs),
                'csv_range':dict(c.execute('SELECT min(local_timestamp) first,max(local_timestamp) last FROM records').fetchone())}

def collect(dbpath,since=None,until=None,client=None,delay=1.0):
    """One run, all account pumps. No scheduling, Nightscout writes or pump mutations."""
    if since:date.fromisoformat(since)
    if until:date.fromisoformat(until)
    if since and until and since>until:raise ValueError('Intervalo invertido')
    own=client is None
    if own:
        from .credentials import load_credentials
        credentials=load_credentials()
        if not credentials:raise RuntimeError('Configure el acceso en la aplicación o con el comando credentials')
    with writer_lock(dbpath):
        conn=connect(dbpath)
        tag=uuid.uuid4().hex
        snapshot=Path(dbpath).parent/'backups'/f'antes_api_{tag}.sqlite'
        backup(conn,snapshot)
        run=conn.execute('INSERT INTO api_runs(started_at,status,requested_start,requested_end) VALUES(?,?,?,?)',(now(),'running',since,until)).lastrowid;conn.commit()
        result={'run_id':run,'windows':0,'new_events':0,'backup_before':str(snapshot),'scope':'all_returned_events_no_filter','unknown_codes_preserved':True}
        try:
            if own:
                from .source_client import SourceClient
                client=SourceClient(*credentials)
                del credentials
            pumps=ingest_pumper(conn,run,client.get_pumper())
            result['pumps']=len(pumps);result['device_requests']=[]
            for pump in pumps:
                planned=windows(conn,pump,since,until)
                result['device_requests'].append({'device_id':pump['assignmentId'],'windows':planned,
                    'status':'requested' if planned else 'no_available_data_in_requested_range'})
                for start,end in planned:
                    if delay:time.sleep(delay)
                    body=client.get_pump_logs(pump['assignmentId'],start,end)
                    imported=ingest_logs(conn,run,body,pump['assignmentId'],pump['serialNumber'],start,end)
                    result['new_events']+=imported['new_events'];result['windows']+=1
            result['redecoded_events']=redecode(conn)
            result['links']=reconcile(conn);result['audit']=audit_api(conn)
            if result['audit']['payload_hash_errors'] or result['audit']['event_hash_errors'] or result['audit']['events_without_source']:raise RuntimeError('Auditoría API fallida')
            result['status']='complete'
            with conn:conn.execute('UPDATE api_runs SET status=?,finished_at=?,summary_json=? WHERE id=?',('complete',now(),dumps(result),run))
            final=Path(dbpath).parent/'backups'/f'despues_api_{tag}.sqlite';backup(conn,final);result['backup_after']=str(final)
            return result
        except Exception as exc:
            # Exception strings from transports may contain authorization codes or account details.
            safe_code=getattr(exc,'code',type(exc).__name__)
            with conn:conn.execute('UPDATE api_runs SET status=?,finished_at=?,error_code=?,summary_json=? WHERE id=?',('failed',now(),safe_code,dumps(result),run))
            raise RuntimeError('Recopilación incompleta. Se conservan las ventanas recibidas; compruebe acceso y diagnóstico local.') from None
        finally:
            if own and client is not None:client.close()
            conn.close()
