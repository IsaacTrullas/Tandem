from __future__ import annotations
import csv
import io
import json
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from .db import digest,dumps,now,store_artifact,issue

KINDS={
 'MCG':['Tipo de dispositivo','Número de serie','Descripción','Fecha y hora del caso','Lecturas (mg/dl)'],
 'GLUCOSA':['Tipo de dispositivo','Número de serie','Descripción','Fecha y hora del caso','Glucosa (mg/dl)','Nota'],
 'Dosis basales':['Tipo de dispositivo','Número de serie','Fecha y hora del caso','Dosis basal prescrita (unidades de insulina)'],
 'Suministro basal por hora':['Número de serie','Fecha del evento']+[str(i) for i in range(24)],
 'Bolo':['Tipo','Tipo de bolo','Método de suministro del bolo','Glucosa (mg/dl)','Número de serie',
 'Fecha y hora de finalización','Insulina suministrada','Alimento suministrado','Corrección suministrada',
 'Descripción del estado de finalización','Fecha y hora de inicio del bolo','Fecha y hora de finalización del bolo',
 'Insulina suministrada en bolo','Descripción del estado de finalización del bolo','Porcentaje estándar','Duración (minutos)',
 'Cantidad de carbohidratos','Objetivo de glucemia (mg/dl)','Factor de corrección','I:C']}

def number(value, required=False):
    if value is None or value.strip()=='':
        if required: raise ValueError('Falta un valor numérico requerido')
        return None
    # CSV decimals use dots; commas must be quoted and are accepted for reviewed corrections.
    result=float(value.strip().replace(',','.'))
    if not __import__('math').isfinite(result): raise ValueError('Número no finito')
    return result

def period_from_name(name):
    m=re.search(r'(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})',name)
    return m.groups() if m else (None,None)

def normalize(row,kind):
    values=dict(row)
    numeric={
     'MCG':['Lecturas (mg/dl)'],'GLUCOSA':['Glucosa (mg/dl)'],
     'Dosis basales':['Dosis basal prescrita (unidades de insulina)'],
     'Suministro basal por hora':[str(i) for i in range(24)],
     'Bolo':['Glucosa (mg/dl)','Insulina suministrada','Alimento suministrado','Corrección suministrada',
     'Insulina suministrada en bolo','Porcentaje estándar','Duración (minutos)','Cantidad de carbohidratos',
     'Objetivo de glucemia (mg/dl)','Factor de corrección','I:C']}[kind]
    for key in numeric: values[key]=number(row[key])
    return values

def ingest_csv(conn,content,filename,location,run_id,parent_id=None,period=(None,None)):
    artifact_id,status=store_artifact(conn,content,filename,'text/csv',location,run_id,*period)
    if parent_id: conn.execute('INSERT OR IGNORE INTO artifact_links VALUES(?,?,?)',(parent_id,artifact_id,'contains'))
    reader=csv.DictReader(io.StringIO(content.decode('utf-8-sig'),newline=''))
    header=reader.fieldnames
    kind=next((k for k,v in KINDS.items() if header==v),None)
    if not kind: raise ValueError('Esquema CSV no reconocido: '+filename+' '+repr(header))
    occurrences=Counter()
    previous_time=None
    segment=0
    count=0
    for line,row in enumerate(reader,2):
        if None in row or any(v is None for v in row.values()): raise ValueError(f'Fila CSV incompleta en {filename}:{line}')
        field='Fecha y hora de finalización' if kind=='Bolo' else ('Fecha del evento' if kind=='Suministro basal por hora' else 'Fecha y hora del caso')
        stamp=row[field]
        dt=datetime.fromisoformat(stamp)
        if dt.tzinfo is not None: raise ValueError('Ha cambiado el formato de zona horaria del CSV')
        if status!='imported' and previous_time and stamp<previous_time:
            segment+=1
            conn.execute('''INSERT OR IGNORE INTO clock_observations
              (artifact_id,before_local,after_local,observation_type,details_json) VALUES(?,?,?,?,?)''',
              (artifact_id,previous_time,stamp,'source_order_backwards',dumps({'row':line,'segment':segment})))
        previous_time=stamp
        if period[0] and not period[0]<=stamp[:10]<=period[1]:
            raise ValueError('Registro fuera del periodo solicitado: '+stamp)
        if status=='imported':continue
        raw=dumps(row)
        conn.execute('INSERT OR IGNORE INTO raw_rows(artifact_id,row_number,kind,raw_json,sha256) VALUES(?,?,?,?,?)',
                     (artifact_id,line,kind,raw,digest(raw.encode())))
        raw_id=conn.execute('SELECT id FROM raw_rows WHERE artifact_id=? AND row_number=?',(artifact_id,line)).fetchone()[0]
        values=normalize(row,kind)
        canonical=dumps({'kind':kind,'values':values})
        fingerprint=digest(canonical.encode())
        occurrence=occurrences[fingerprint]
        occurrences[fingerprint]+=1
        conn.execute('''INSERT OR IGNORE INTO records
          (fingerprint,occurrence,kind,pump_serial,local_timestamp,local_date,values_json)
          VALUES(?,?,?,?,?,?,?)''',(fingerprint,occurrence,kind,row['Número de serie'],stamp,stamp[:10],dumps(values)))
        record_id=conn.execute('SELECT id FROM records WHERE fingerprint=? AND occurrence=?',(fingerprint,occurrence)).fetchone()[0]
        conn.execute('INSERT OR IGNORE INTO record_sources VALUES(?,?,?)',(record_id,raw_id,segment))
        if kind in ('MCG','GLUCOSA'):
            glucose=number(row['Lecturas (mg/dl)' if kind=='MCG' else 'Glucosa (mg/dl)'],True)
            conn.execute('INSERT OR IGNORE INTO glucose_readings VALUES(?,?,?,?,?)',
                         (record_id,'sensor' if kind=='MCG' else 'pump_entry',glucose,row['Descripción'],row.get('Nota')))
        elif kind=='Bolo':
            v=values
            conn.execute('INSERT OR IGNORE INTO boluses VALUES('+','.join('?'*18)+')',
              (record_id,v['Tipo de bolo'],v['Método de suministro del bolo'],v['Glucosa (mg/dl)'],
               v['Insulina suministrada'],v['Alimento suministrado'],v['Corrección suministrada'],v['Descripción del estado de finalización'],
               v['Fecha y hora de inicio del bolo'] or None,v['Fecha y hora de finalización del bolo'] or None,
               v['Insulina suministrada en bolo'],v['Descripción del estado de finalización del bolo'] or None,
               v['Porcentaje estándar'],v['Duración (minutos)'],v['Cantidad de carbohidratos'],
               v['Objetivo de glucemia (mg/dl)'],v['Factor de corrección'],v['I:C']))
            # 0 grams is an explicit source value and remains in boluses. Meals are not inferred from it.
            if v['Cantidad de carbohidratos'] is not None and v['Cantidad de carbohidratos']>0:
                conn.execute('INSERT OR IGNORE INTO carbohydrate_entries(bolus_record_id,grams) VALUES(?,?)',(record_id,v['Cantidad de carbohidratos']))
        elif kind=='Dosis basales':
            conn.execute('INSERT OR IGNORE INTO basal_doses VALUES(?,?)',(record_id,number(row[KINDS[kind][-1]],True)))
        else:
            conn.executemany('INSERT OR IGNORE INTO basal_hourly VALUES(?,?,?)',[(record_id,h,values[str(h)]) for h in range(24)])
        count+=1
    if status=='imported':return artifact_id,0
    if any(v>1 for v in occurrences.values()):
        issue(conn,'identical_rows_within_export',{'counts':dict((k,v) for k,v in occurrences.items() if v>1)},artifact_id)
    conn.execute("UPDATE artifacts SET status='imported',metadata_json=? WHERE id=?",(dumps({'kind':kind,'columns':header,'rows':count}),artifact_id))
    return artifact_id,count

def ingest_file(conn,path,run_id,metadata=None):
    from .pdf import ingest_pdf
    path=Path(path)
    content=path.read_bytes()
    period=period_from_name(path.name)
    if metadata and metadata.get('period_start') and metadata.get('period_end'):
        period=(metadata['period_start'],metadata['period_end'])
    suffix=path.suffix.lower()
    if suffix=='.csv': return ingest_csv(conn,content,path.name,str(path),run_id,period=period)
    mime={'.zip':'application/zip','.pdf':'application/pdf','.json':'application/json','.txt':'text/plain'}.get(suffix,'application/octet-stream')
    artifact_id,status=store_artifact(conn,content,path.name,mime,str(path),run_id,*period,metadata=metadata)
    if status=='archived' or (status=='imported' and suffix not in ('.zip','.pdf')): return artifact_id,0
    rows=0
    if suffix=='.zip':
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            if z.testzip(): raise ValueError('ZIP corrupto: '+path.name)
            members=[n for n in z.namelist() if n.lower().endswith('.csv')]
            if len(members)!=5: raise ValueError('Se esperaban cinco CSV en '+path.name)
            found=[]
            for name in members:
                child,n=ingest_csv(conn,z.read(name),Path(name).name,str(path)+'!'+name,run_id,artifact_id,period)
                found.append(json.loads(conn.execute('SELECT metadata_json FROM artifacts WHERE id=?',(child,)).fetchone()[0])['kind'])
                rows+=n
            if set(found)!=set(KINDS): raise ValueError('Tipos CSV incompletos en '+path.name)
    elif suffix=='.pdf':
        if period[0]:
            from .sync import verify_pdf_period
            verify_pdf_period(content,*period)
        if status=='imported':return artifact_id,0
        ingest_pdf(conn,artifact_id,content)
    else:
        conn.execute("UPDATE artifacts SET status='archived' WHERE id=?",(artifact_id,))
        return artifact_id,0
    conn.execute("UPDATE artifacts SET status='imported' WHERE id=?",(artifact_id,))
    return artifact_id,rows

def discover(source):
    source=Path(source)
    if source.is_file(): return [source]
    # Include the original files and documentary evidence, not generated CSV copies or executable scripts.
    original=source/'originales'
    files=sorted(original.iterdir()) if original.is_dir() else sorted(p for p in source.iterdir() if p.is_file())
    if original.is_dir():
        files+=sorted(p for p in source.iterdir() if p.suffix.lower() in ('.json','.txt'))
        if (source/'evidencias').is_dir(): files+=sorted(p for p in (source/'evidencias').iterdir() if p.suffix.lower() in ('.json','.txt'))
    return [p for p in files if p.suffix.lower() in ('.zip','.pdf','.csv','.json','.txt')]

def import_source(conn,source):
    run=conn.execute('INSERT INTO import_runs(started_at,status,source_path) VALUES(?,?,?)',(now(),'running',str(source))).lastrowid
    conn.commit()
    summary={'files':0,'new_raw_rows':0,'failures':[]}
    for path in discover(source):
        try:
            with conn:
                _,rows=ingest_file(conn,path,run)
            summary['files']+=1
            summary['new_raw_rows']+=rows
        except Exception as exc:
            summary['failures'].append({'file':path.name,'error':str(exc)})
            # Preserve even unsupported or corrupt source files; never mark them successfully normalized.
            with conn:
                aid,_=store_artifact(conn,path.read_bytes(),path.name,'application/octet-stream',str(path),run)
                conn.execute("UPDATE artifacts SET status='quarantined' WHERE id=?",(aid,))
                issue(conn,'import_failed',{'file':path.name,'error':str(exc)},aid,severity='error')
    with conn:
        conn.execute('UPDATE import_runs SET finished_at=?,status=?,summary_json=? WHERE id=?',
                     (now(),'failed' if summary['failures'] else 'complete',dumps(summary),run))
    return summary
