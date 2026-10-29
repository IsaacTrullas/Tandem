"""UI-independent import pipeline and read-only dashboard queries."""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
from .reader import Reader


def import_manifest(database, manifest):
    from .collector import writer_lock
    with writer_lock(database):
        return _import_manifest(database, manifest)


def _import_manifest(database, manifest):
    from .db import backup, connect
    from .sync import accept_downloads
    from .pdf import run_ocr
    from .visual import expand
    from .cli import status
    from .collector import reconcile, audit_api
    database = Path(database)
    conn = connect(database)
    try:
        loaded = accept_downloads(conn, manifest, database.parent / 'archive', database.parent / 'backups')
        ocr = run_ocr(conn)
        visual = expand(conn)
        reconcile(conn)
        report = status(conn, True)
        report['api_audit'] = audit_api(conn)
        failures = {k: v for k, v in report.items() if
                    ('error' in k or 'missing' in k or 'unmatched' in k or 'unscaled' in k or
                     'conflicts' in k or 'unexpanded' in k or k in ('raw_rows_without_record', 'quarantined_files')) and v}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        audit = database.parent / 'auditorias' / ('app_' + stamp + '.json')
        audit.parent.mkdir(parents=True, exist_ok=True)
        audit.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        api_failures = any(report['api_audit'].get(k) for k in ('payload_hash_errors', 'event_hash_errors', 'events_without_source'))
        if report.get('integrity_check') != 'ok' or failures or visual.get('errors') or ocr.get('errors') or api_failures:
            raise RuntimeError('La importación requiere revisión de la auditoría')
        final = backup(conn, database.parent / 'backups' / ('app_' + stamp + '.sqlite'))
        return {'windows': loaded['windows'], 'new_raw_rows': loaded['new_raw_rows'],
                'audit': str(audit), 'backup': final, 'status': 'complete'}
    finally:
        conn.close()


DASHBOARD_TABLES = ('records', 'pdf_pages', 'api_events', 'api_payloads', 'source_links')


def load_dashboard(database):
    """Read one consistent snapshot; never create or migrate the database.

    Counts and time ranges identify source families independently. Device times
    are source wall-clock strings, not reconstructed UTC treatment timestamps.
    """
    database = Path(database)
    result = {
        'status': 'missing',
        'counts': {name: 0 for name in DASHBOARD_TABLES},
        'csv_range': {'first': None, 'last': None},
        'api_range': {'first': None, 'last': None},
        'unknown_count': 0,
        'pending_review': 0,
        'last_run': None,
        'runs': [],
        'datasets': [],
    }
    if not database.exists():
        return result
    with Reader(database) as reader:
        conn = reader._conn
        conn.execute('BEGIN')
        try:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
            result['datasets'] = reader.datasets()
            for name in DASHBOARD_TABLES:
                if name in tables:
                    result['counts'][name] = conn.execute('SELECT count(*) FROM ' + name).fetchone()[0]
            for table, key in (('records', 'csv_range'), ('api_events', 'api_range')):
                if table in tables:
                    row = conn.execute('SELECT min(local_timestamp) first,max(local_timestamp) last FROM ' + table).fetchone()
                    result[key] = dict(row)
            if 'api_events' in tables:
                result['unknown_count'] = conn.execute(
                    "SELECT count(*) FROM api_events WHERE decode_status NOT IN ('decoded','classified')").fetchone()[0]
            if 'v_pending_review' in tables:
                result['pending_review'] = conn.execute('SELECT count(*) FROM v_pending_review').fetchone()[0]
            if 'api_runs' in tables:
                result['runs'] = [dict(r) for r in conn.execute('SELECT * FROM api_runs ORDER BY id DESC LIMIT 100')]
                result['last_run'] = result['runs'][0] if result['runs'] else None
            result['status'] = 'ready'
            return result
        finally:
            conn.rollback()
