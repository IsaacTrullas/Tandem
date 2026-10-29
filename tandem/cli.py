from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path
from .db import DEFAULT_DB,connect,digest,dumps,backup,now

def status(conn,verify=False):
    counts={name:conn.execute('SELECT COUNT(*) FROM '+name).fetchone()[0] for name in
      ('artifacts','raw_rows','records','glucose_readings','boluses','carbohydrate_entries','basal_doses',
       'basal_hourly','pdf_pages','daily_panels','pdf_facts','therapy_events','profiles','profile_segments',
       'report_images','report_fields','sleep_schedules','legend_templates','chart_observations','state_intervals','visual_series',
       'chart_labels','report_text_events','native_text_blocks','report_metrics','native_drawings','report_image_masks',
       'legend_definitions','legend_instances','legend_symbol_hits','legend_feature_links','legend_chart_scans',
       'plot_calibrations','quantitative_layers','basal_rate_annotations','extended_bolus_spans','quantitative_runs')}
    result={'tables':counts,
      'records_by_kind':dict(conn.execute('SELECT kind,COUNT(*) FROM records GROUP BY kind').fetchall()),
      'range_by_kind':[dict(r) for r in conn.execute('SELECT kind,MIN(local_timestamp) first,MAX(local_timestamp) last FROM records GROUP BY kind')],
      'ocr_status':dict(conn.execute('SELECT ocr_status,COUNT(*) FROM pdf_pages GROUP BY ocr_status').fetchall()),
      'pending_review':conn.execute('SELECT COUNT(*) FROM v_pending_review').fetchone()[0],
      'quarantined_files':conn.execute("SELECT COUNT(*) FROM artifacts WHERE status='quarantined'").fetchone()[0],
      'stored_bytes':conn.execute('SELECT SUM(byte_count) FROM artifacts').fetchone()[0] or 0}
    result['visual_extraction_status']=dict(conn.execute("SELECT status,count(*) FROM pdf_extractions WHERE extractor='full_pdf' GROUP BY status").fetchall())
    result['state_intervals_by_type']=dict(conn.execute('SELECT state,count(*) FROM state_intervals GROUP BY state').fetchall())
    result['visual_observations_by_type']=dict(conn.execute('SELECT observation_type,count(*) FROM chart_observations GROUP BY observation_type').fetchall())
    result['visual_review_pending']=conn.execute("SELECT count(*) FROM chart_observations WHERE review_status='visual_unreviewed'").fetchone()[0]
    result['legend_catalogue_status']=[dict(r) for r in conn.execute('SELECT legend_kind,status,count(*) n FROM legend_page_audits GROUP BY legend_kind,status')]
    result['legend_scan_status']=dict(conn.execute('SELECT status,count(*) FROM legend_chart_scans GROUP BY status').fetchall())
    result['legend_symbol_review_pending']=conn.execute("SELECT count(*) FROM legend_symbol_hits WHERE review_status LIKE '%unreviewed%'").fetchone()[0]
    result['legend_partial_adapters']=[dict(r) for r in conn.execute("SELECT key,label,json_extract(rule_json,'$.implementation_state') state FROM legend_definitions WHERE json_extract(rule_json,'$.implementation_state') LIKE 'partial%'")]
    result['quantitative_status']=dict(conn.execute('SELECT status,count(*) FROM quantitative_runs GROUP BY status').fetchall())
    result['plot_calibration_status']=dict(conn.execute('SELECT status,count(*) FROM plot_calibrations GROUP BY status').fetchall())
    result['extended_bolus_records_matched']=conn.execute('SELECT count(DISTINCT bolus_record_id) FROM extended_bolus_spans').fetchone()[0]
    from .collector import audit_api
    result['api']=audit_api(conn)
    if verify:
        result['integrity_check']=conn.execute('PRAGMA integrity_check').fetchone()[0]
        result['foreign_key_errors']=[list(r) for r in conn.execute('PRAGMA foreign_key_check')]
        result['artifact_hash_errors']=[r['id'] for r in conn.execute('SELECT id,sha256,content FROM artifacts') if digest(r['content'])!=r['sha256']]
        result['raw_rows_without_record']=conn.execute('SELECT COUNT(*) FROM raw_rows r LEFT JOIN record_sources s ON s.raw_row_id=r.id WHERE s.record_id IS NULL').fetchone()[0]
        result['source_files_by_status']=dict(conn.execute('SELECT status,COUNT(*) FROM artifacts GROUP BY status').fetchall())
        result['raw_row_hash_errors']=[r['id'] for r in conn.execute('SELECT id,raw_json,sha256 FROM raw_rows') if digest(r['raw_json'].encode())!=r['sha256']]
        result['daily_coverage']=[dict(r) for r in conn.execute('SELECT * FROM v_daily_csv ORDER BY local_date')]
        result['pdf_dates_outside_requested_period']=[r[0] for r in conn.execute('''SELECT d.id FROM daily_panels d
          JOIN pdf_pages p ON p.id=d.page_id JOIN artifacts a ON a.id=p.artifact_id
          WHERE d.local_date<a.period_start OR d.local_date>a.period_end''')]
        result['report_image_hash_errors']=[r['id'] for r in conn.execute('SELECT id,image_png,sha256 FROM report_images') if digest(r['image_png'])!=r['sha256']]
        result['report_mask_hash_errors']=[r['image_id'] for r in conn.execute('SELECT image_id,mask_png,sha256 FROM report_image_masks') if digest(r['mask_png'])!=r['sha256']]
        result['pdf_layout_verification_errors']=conn.execute("SELECT count(*) FROM pdf_pages p LEFT JOIN pdf_layout_verifications v ON v.page_id=p.id WHERE v.status IS NULL OR v.status!='complete'").fetchone()[0]
        result['visual_dates_missing']=conn.execute("SELECT count(*) FROM report_images WHERE image_kind='daily_chart' AND local_date IS NULL").fetchone()[0]
        result['pdf_unexpanded_pages']=conn.execute("SELECT count(*) FROM pdf_pages p WHERE NOT EXISTS(SELECT 1 FROM pdf_extractions e WHERE e.page_id=p.id AND e.extractor='full_pdf' AND e.status='complete')").fetchone()[0]
        result['visual_block_count_errors']=[]
        result['legend_hash_errors']=[r['id'] for r in conn.execute('SELECT id,symbol_png,sha256 FROM legend_instances') if digest(r['symbol_png'])!=r['sha256']]
        result['legend_catalogue_errors']=conn.execute("SELECT count(*) FROM legend_page_audits WHERE status!='complete'").fetchone()[0]
        result['legend_missing_pages']=conn.execute("""SELECT count(*) FROM pdf_pages p WHERE p.native_text LIKE '%Glucemia alta%'
          AND p.native_text LIKE '%Detener de%' AND NOT EXISTS(SELECT 1 FROM legend_page_audits l WHERE l.page_id=p.id AND l.legend_kind='daily' AND l.status='complete')""").fetchone()[0]
        result['legend_unscanned_charts']=conn.execute("SELECT count(*) FROM report_images i WHERE image_kind='daily_chart' AND NOT EXISTS(SELECT 1 FROM legend_chart_scans s WHERE s.image_id=i.id AND status='complete')").fetchone()[0]
        result['legend_scan_errors']=conn.execute("SELECT count(*) FROM legend_chart_scans WHERE status='error'").fetchone()[0]
        result['quantitative_missing_charts']=conn.execute("SELECT count(*) FROM report_images i WHERE image_kind='daily_chart' AND NOT EXISTS(SELECT 1 FROM quantitative_runs q WHERE q.image_id=i.id AND q.status='complete')").fetchone()[0]
        result['quantitative_unscaled_charts']=[r[0] for r in conn.execute("SELECT image_id FROM plot_calibrations WHERE status!='calibrated'")]
        result['quantitative_readout_conflicts']=[dict(r) for r in conn.execute('''SELECT a.id,a.image_id,a.text FROM basal_rate_annotations a
          JOIN plot_calibrations p ON p.image_id=a.image_id WHERE a.line_y IS NOT NULL AND p.status='calibrated'
          AND abs(a.rate_units_per_hour-(p.zero_y-a.line_y)*p.units_per_pixel)>p.uncertainty_units_per_hour*1.5+.01''')]
        result['extended_bolus_unmatched_records']=[r[0] for r in conn.execute("SELECT record_id FROM boluses b WHERE delivery_method='Extendido' AND NOT EXISTS(SELECT 1 FROM extended_bolus_spans e WHERE e.bolus_record_id=b.record_id)")]
        result['extended_bolus_unmatched_slices']=[]
        from .quantitative import expected_extended
        for b in conn.execute("SELECT * FROM boluses WHERE delivery_method='Extendido' AND extended_start_local IS NOT NULL AND extended_end_local IS NOT NULL").fetchall():
            for i in conn.execute("SELECT id,local_date FROM report_images WHERE image_kind='daily_chart'").fetchall():
                if not i['local_date'] or not expected_extended(b,i['local_date']):continue
                if not conn.execute('SELECT 1 FROM extended_bolus_spans WHERE image_id=? AND bolus_record_id=?',(i['id'],b['record_id'])).fetchone():
                    result['extended_bolus_unmatched_slices'].append({'image_id':i['id'],'bolus_record_id':b['record_id']})
        for r in conn.execute("SELECT page_id,details_json FROM pdf_extractions WHERE extractor='full_pdf' AND status='complete'"):
            detail=json.loads(r['details_json'])
            for key,table in [('image_block_count','report_images'),('native_block_count','native_text_blocks')]:
                if key in detail and conn.execute('SELECT count(*) FROM '+table+' WHERE page_id=?',(r['page_id'],)).fetchone()[0]!=detail[key]:
                    result['visual_block_count_errors'].append({'page_id':r['page_id'],'type':key})
    return result

def main(argv=None):
    parser=argparse.ArgumentParser(description='Base local de Tandem Source. Nunca escribe en la cuenta o bomba.')
    parser.add_argument('--db',type=Path,default=DEFAULT_DB)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init')
    imp=sub.add_parser('import-source');imp.add_argument('source',type=Path)
    sub.add_parser('status')
    au=sub.add_parser('audit');au.add_argument('--output',type=Path)
    oc=sub.add_parser('ocr');oc.add_argument('--limit',type=int);oc.add_argument('--language',default='es')
    ep=sub.add_parser('extract-pdf');ep.add_argument('--rebuild',action='store_true')
    sub.add_parser('quantify')
    lg=sub.add_parser('legend');lg.add_argument('--atlas',type=Path);lg.add_argument('--scan',action='store_true')
    st=sub.add_parser('states');st.add_argument('--day')
    evt=sub.add_parser('events');evt.add_argument('--day')
    ev=sub.add_parser('export-visual');ev.add_argument('id',type=int);ev.add_argument('output',type=Path)
    es=sub.add_parser('export-symbol');es.add_argument('id',type=int);es.add_argument('output',type=Path)
    pl=sub.add_parser('plan');pl.add_argument('--through');pl.add_argument('--since');pl.add_argument('--overlap-days',type=int,default=7);pl.add_argument('--output',type=Path)
    sy=sub.add_parser('sync');sy.add_argument('manifest',type=Path)
    ba=sub.add_parser('backup');ba.add_argument('output',type=Path)
    ex=sub.add_parser('export-artifact');ex.add_argument('id',type=int);ex.add_argument('output',type=Path)
    page=sub.add_parser('export-page');page.add_argument('id',type=int);page.add_argument('output',type=Path)
    se=sub.add_parser('search');se.add_argument('text')
    re=sub.add_parser('review');re.add_argument('table',choices=['daily_panels','therapy_events','chart_observations','state_intervals','report_text_events','chart_labels','report_fields','report_metrics','legend_symbol_hits','quantitative_layers','extended_bolus_spans','basal_rate_annotations']);re.add_argument('id',type=int);re.add_argument('--decision',choices=['accepted','rejected'],required=True);re.add_argument('--reviewer',required=True);re.add_argument('--note',required=True)
    sub.add_parser('app')
    sub.add_parser('credentials')
    collect_parser=sub.add_parser('collect');collect_parser.add_argument('--since');collect_parser.add_argument('--until')
    export_parser=sub.add_parser('export-data');export_parser.add_argument('dataset');export_parser.add_argument('output',type=Path);export_parser.add_argument('--since');export_parser.add_argument('--until')
    args=parser.parse_args(argv)
    if args.command in ('app','credentials','collect','export-data'):
        try:
            if args.command=='app':
                from .app import launch
                launch(args.db)
            elif args.command=='credentials':
                from .credentials import configure_credentials
                configure_credentials()
            elif args.command=='collect':
                from .collector import collect
                print(json.dumps(collect(args.db,args.since,args.until),ensure_ascii=False,indent=2))
            elif args.command=='export-data':
                from .reader import Reader
                with Reader(args.db) as reader:reader.export_jsonl(args.dataset,args.output,since=args.since,until=args.until)
            return 0
        except (ValueError,RuntimeError,OSError) as exc:
            print(json.dumps({'error':str(exc)},ensure_ascii=False));return 1
    conn=connect(args.db)
    try:
        if args.command=='init':result={'database':str(args.db),'schema_version':conn.execute('SELECT max(version) FROM schema_version').fetchone()[0]}
        elif args.command=='import-source':
            from .ingest import import_source
            result=import_source(conn,args.source)
        elif args.command in ('status','audit'):
            result=status(conn,args.command=='audit')
            if args.command=='audit' and args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        elif args.command=='ocr':
            from .pdf import run_ocr
            result=run_ocr(conn,args.limit,args.language)
        elif args.command=='extract-pdf':
            from .visual import expand
            result=expand(conn,args.rebuild)
        elif args.command=='legend':
            from .legend import catalogue,atlas,scan_charts
            result=catalogue(conn)
            if args.scan and not result['errors']:
                result['scans']=scan_charts(conn)
                result['errors']+=result['scans']['errors']
            if args.atlas:result['atlas']=atlas(conn,args.atlas)
        elif args.command=='quantify':
            from .quantitative import process
            result=process(conn)
        elif args.command=='states':
            result=[dict(r) for r in conn.execute('''SELECT id,state,local_date,start_local,end_local,uncertainty_minutes,
              review_status,page_number,filename FROM v_states WHERE (? IS NULL OR local_date=?) ORDER BY local_date,start_minute''',(args.day,args.day))]
        elif args.command=='events':
            result=[dict(r) for r in conn.execute('SELECT * FROM v_event_evidence WHERE (? IS NULL OR local_date=?) ORDER BY local_date,minute_lower,time_local',(args.day,args.day))]
        elif args.command in ('export-visual','export-symbol'):
            table='chart_observations' if args.command=='export-visual' else 'legend_symbol_hits'
            row=conn.execute('SELECT evidence_png FROM '+table+' WHERE id=?',(args.id,)).fetchone()
            if not row:raise ValueError('Observación visual inexistente')
            if args.output.exists():raise ValueError('El archivo de salida ya existe')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(row[0]);result={'output':str(args.output)}
        elif args.command=='plan':
            from .sync import plan
            result=plan(conn,args.through,args.since,args.overlap_days)
            if args.output:
                args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        elif args.command=='sync':
            from .sync import accept_downloads
            result=accept_downloads(conn,args.manifest,args.db.parent/'archive',args.db.parent/'backups')
        elif args.command=='backup':result={'backup':backup(conn,args.output)}
        elif args.command=='export-artifact':
            row=conn.execute('SELECT content FROM artifacts WHERE id=?',(args.id,)).fetchone()
            if not row:raise ValueError('Archivo inexistente')
            if args.output.exists():raise ValueError('El archivo de salida ya existe')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(row[0]);result={'output':str(args.output)}
        elif args.command=='export-page':
            row=conn.execute('SELECT p.*,a.content FROM pdf_pages p JOIN artifacts a ON a.id=p.artifact_id WHERE p.id=?',(args.id,)).fetchone()
            if not row:raise ValueError('Página inexistente')
            if args.output.exists():raise ValueError('El archivo de salida ya existe')
            image=row['rendered_png']
            if not image:
                import pymupdf
                with pymupdf.open(stream=row['content'],filetype='pdf') as doc:image=doc[row['page_number']-1].get_pixmap(dpi=150).tobytes('png')
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(image);result={'output':str(args.output)}
        elif args.command=='search':
            result=[dict(r) for r in conn.execute('''SELECT p.id,a.filename,p.page_number,substr(COALESCE(p.ocr_text,p.native_text),1,250) preview
              FROM pdf_pages p JOIN artifacts a ON a.id=p.artifact_id WHERE instr(lower(p.native_text),lower(?))>0 OR instr(lower(COALESCE(p.ocr_text,'')),lower(?))>0''',(args.text,args.text))]
        elif args.command=='review':
            row=conn.execute(f'SELECT id FROM {args.table} WHERE id=?',(args.id,)).fetchone()
            if not row:raise ValueError('Registro de revisión inexistente')
            with conn:
                conn.execute(f'UPDATE {args.table} SET review_status=? WHERE id=?',('reviewed_'+args.decision,args.id))
                if args.table=='chart_observations':
                    conn.execute('UPDATE state_intervals SET review_status=? WHERE observation_id=?',('reviewed_'+args.decision,args.id))
                conn.execute('INSERT INTO review_log(target_table,target_id,decision,reviewer,reviewed_at,note) VALUES(?,?,?,?,?,?)',
                 (args.table,args.id,args.decision,args.reviewer,now(),args.note))
            result={'reviewed':args.id,'decision':args.decision}
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if isinstance(result,dict) and (result.get('api',{}).get('payload_hash_errors') or result.get('api',{}).get('event_hash_errors') or result.get('api',{}).get('events_without_source') or result.get('failures') or result.get('errors') or result.get('artifact_hash_errors') or result.get('report_image_hash_errors') or result.get('report_mask_hash_errors') or result.get('pdf_layout_verification_errors') or result.get('visual_dates_missing') or result.get('pdf_unexpanded_pages') or result.get('visual_block_count_errors') or result.get('legend_hash_errors') or result.get('legend_catalogue_errors') or result.get('legend_missing_pages') or result.get('legend_unscanned_charts') or result.get('legend_scan_errors') or result.get('quantitative_missing_charts') or result.get('quantitative_unscaled_charts') or result.get('quantitative_readout_conflicts') or result.get('extended_bolus_unmatched_records') or result.get('extended_bolus_unmatched_slices') or result.get('visual_extraction_status',{}).get('error') or result.get('foreign_key_errors') or result.get('raw_row_hash_errors') or result.get('raw_rows_without_record') or result.get('quarantined_files') or result.get('pdf_dates_outside_requested_period') or result.get('ocr_status',{}).get('error') or result.get('integrity_check','ok')!='ok'):
            return 1
        return 0
    except (ValueError,RuntimeError,sqlite3.Error,OSError) as exc:
        print(json.dumps({'error':str(exc)},ensure_ascii=False));return 1
    finally:conn.close()
