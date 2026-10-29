"""Plans and accepts browser downloads. No passwords, network API or pump writes."""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from pypdf import PdfReader
import io,json,re
from .db import backup,digest,dumps,now

MONTHS=['','ene','feb','mar','abr','may','jun','jul','ago','sept','oct','nov','dic']

def label(start,end):
    s,e=date.fromisoformat(start),date.fromisoformat(end)
    if s==e:return f'{s.day} {MONTHS[s.month]} {s.year}'
    if s.year==e.year and s.month==e.month:return f'{s.day}-{e.day} {MONTHS[e.month]} {e.year}'
    if s.year==e.year:return f'{s.day} {MONTHS[s.month]} - {e.day} {MONTHS[e.month]} {e.year}'
    return f'{s.day} {MONTHS[s.month]} {s.year} - {e.day} {MONTHS[e.month]} {e.year}'

def verify_pdf_period(content,start,end):
    reader=PdfReader(io.BytesIO(content))
    text=''.join(''.join(p.extract_text().split()) for p in reader.pages)
    expected=''.join(label(start,end).split())
    for heading in ('Resumen general','Cronograma diario'):
        if ''.join(heading.split())+expected not in text:
            raise ValueError(f'El PDF no contiene {heading} para {start} - {end}')

def plan(conn,through=None,since=None,overlap_days=7):
    if overlap_days<1 or overlap_days>30:raise ValueError('El solapamiento debe ser entre 1 y 30 días')
    # User-facing calendar comes from Europe/Madrid, never host localtime.
    if through is None:
        from zoneinfo import ZoneInfo
        through=datetime.now(ZoneInfo('Europe/Madrid')).date().isoformat()
    end=date.fromisoformat(through)
    paired=conn.execute("""SELECT e.period_start,e.period_end FROM artifact_receipts e JOIN artifacts a ON a.id=e.artifact_id WHERE status='imported'
      AND mime_type IN ('application/zip','application/pdf') AND e.period_start IS NOT NULL
      GROUP BY e.period_start,e.period_end HAVING COUNT(DISTINCT mime_type)=2 ORDER BY e.period_end"""
    ).fetchall()
    if since:
        start=date.fromisoformat(since)
    elif paired:
        latest=max(date.fromisoformat(r['period_end']) for r in paired)
        start=latest-timedelta(days=overlap_days-1)
        # Also repair an earlier orphaned ZIP or PDF; don't advance over a failed window.
        orphans=conn.execute("""SELECT e.period_start FROM artifact_receipts e JOIN artifacts a ON a.id=e.artifact_id WHERE status='imported'
          AND mime_type IN ('application/zip','application/pdf') AND e.period_start IS NOT NULL
          GROUP BY e.period_start,e.period_end HAVING COUNT(DISTINCT mime_type)<2"""
        ).fetchall()
        if orphans:start=min(start,min(date.fromisoformat(r[0]) for r in orphans))
    else:
        raise ValueError('Primera descarga: indique --since YYYY-MM-DD')
    if start>end:raise ValueError('La fecha inicial es posterior a la final')
    windows=[]
    cursor=start
    while cursor<=end:
        stop=min(end,cursor+timedelta(days=29))
        windows.append({'start':str(cursor),'end':str(stop),'expected_pdf_label':label(str(cursor),str(stop)),
          'timeline_url':f'https://source.eu.tandemdiabetes.com/reports/timeline?startDate={cursor}&endDate={stop}',
          'csv_zip_file':f'cronologia_{cursor}_{stop}.zip','pdf_file':f'informes_{cursor}_{stop}.pdf'})
        cursor=stop+timedelta(days=1)
    return {'schema_version':1,'created_at':now(),'timezone':'Europe/Madrid','overlap_days':overlap_days,
      'start':str(start),'end':str(end),'site':'https://source.eu.tandemdiabetes.com/',
      'mode':'browser_read_and_download_only','windows':windows,
      'browser_protocol':'docs/PROTOCOLO_SINCRONIZACION.md'}

def accept_downloads(conn,manifest_path,archive_dir,backup_dir):
    from .ingest import ingest_file
    manifest_path=Path(manifest_path).resolve()
    manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if manifest.get('schema_version')!=1 or not manifest.get('windows'):raise ValueError('Manifiesto de descarga inválido')
    timestamp=now().replace(':','').replace('+','_')
    snapshot=Path(backup_dir)/('antes_sync_'+timestamp+'.sqlite')
    backup(conn,snapshot)
    run=conn.execute('INSERT INTO sync_runs(started_at,status,plan_json,download_manifest_json) VALUES(?,?,?,?)',
        (now(),'running',dumps(manifest.get('plan',{})),dumps(manifest))).lastrowid
    conn.commit()
    summary={'windows':0,'new_raw_rows':0,'backup':str(snapshot),'artifacts':[]}
    try:
        # One transaction for every CSV/PDF pair. Any invalid file rolls back the entire sync.
        with conn:
            for window in manifest['windows']:
                start,end=window['start'],window['end']
                s,e=date.fromisoformat(start),date.fromisoformat(end)
                if not 0<=(e-s).days<30:raise ValueError('Ventana de descarga fuera del límite de 30 días')
                for key,suffix in (('csv_zip','.zip'),('pdf','.pdf')):
                    spec=window[key]
                    path=Path(spec['path'])
                    if not path.is_absolute():path=manifest_path.parent/path
                    if path.suffix.lower()!=suffix:raise ValueError('La extensión del archivo no corresponde a '+key)
                    content=path.read_bytes()
                    sha=digest(content)
                    if spec.get('sha256'):
                        expected_sha=spec['sha256']
                        if not isinstance(expected_sha,str) or not re.fullmatch('[0-9a-fA-F]{64}',expected_sha):raise ValueError('SHA-256 no válido en el recibo de descarga')
                        if sha!=expected_sha.lower():raise ValueError('SHA-256 distinto del recibo de descarga')
                    if suffix=='.pdf':verify_pdf_period(content,start,end)
                    destination=Path(archive_dir)/(sha+suffix)
                    destination.parent.mkdir(parents=True,exist_ok=True)
                    if destination.exists():
                        if digest(destination.read_bytes())!=sha:raise ValueError('Copia de archivo dañada')
                    else:destination.write_bytes(content)
                    aid,n=ingest_file(conn,path,None,{'period_start':start,'period_end':end,
                         'downloaded_at':spec.get('downloaded_at'),'last_upload':window.get('last_upload'),
                         'archive_copy':str(destination)})
                    summary['new_raw_rows']+=n
                    summary['artifacts'].append(aid)
                summary['windows']+=1
            conn.execute('UPDATE sync_runs SET finished_at=?,status=?,summary_json=? WHERE id=?',(now(),'complete',dumps(summary),run))
    except Exception as exc:
        with conn:conn.execute('UPDATE sync_runs SET finished_at=?,status=?,error=? WHERE id=?',(now(),'failed',str(exc),run))
        raise
    return summary
