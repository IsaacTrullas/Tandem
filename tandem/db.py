from __future__ import annotations
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[1] / 'data' / 'tandem.sqlite'

def now():
    return datetime.now(timezone.utc).isoformat()

def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))

def digest(data):
    return hashlib.sha256(data).hexdigest()

def connect(path=DEFAULT_DB):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(path,timeout=30)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA journal_mode=WAL')
    installed=conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'").fetchone()
    version=conn.execute('SELECT max(version) FROM schema_version').fetchone()[0] if installed else 0
    if version and version>7:raise ValueError('Versión de base más reciente que este programa')
    if not version or version<7:
        conn.executescript(Path(__file__).with_name('schema.sql').read_text(encoding='utf-8'))
        conn.executescript(Path(__file__).with_name('api_schema.sql').read_text(encoding='utf-8'))
        for v in range(1,8):conn.execute('INSERT OR IGNORE INTO schema_version VALUES(?,?)',(v,now()))
        conn.commit()
    return conn

def backup(conn, destination):
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise ValueError('La copia de seguridad ya existe: '+str(destination))
    target=sqlite3.connect(destination)
    try: conn.backup(target)
    finally: target.close()
    return str(destination)

def store_artifact(conn, content, filename, mime, location, run_id, start=None, end=None, metadata=None):
    sha=digest(content)
    conn.execute('''INSERT OR IGNORE INTO artifacts
      (sha256,filename,mime_type,byte_count,content,first_seen_at,period_start,period_end,metadata_json)
      VALUES(?,?,?,?,?,?,?,?,?)''',(sha,filename,mime,len(content),content,now(),start,end,dumps(metadata or {})))
    row=conn.execute('SELECT id,status FROM artifacts WHERE sha256=?',(sha,)).fetchone()
    if row['status'] in ('stored','quarantined') and mime!='application/octet-stream':
        conn.execute('UPDATE artifacts SET mime_type=?,period_start=COALESCE(?,period_start),period_end=COALESCE(?,period_end),metadata_json=? WHERE id=?',
                     (mime,start,end,dumps(metadata or {}),row['id']))
    conn.execute('INSERT OR IGNORE INTO artifact_locations VALUES(?,?,?)',(row['id'],location,run_id))
    if start and end:
        conn.execute('''INSERT OR IGNORE INTO artifact_receipts
          (artifact_id,period_start,period_end,source_path,observed_at,metadata_json) VALUES(?,?,?,?,?,?)''',
          (row['id'],start,end,location,now(),dumps(metadata or {})))
    return row['id'],row['status']

def issue(conn, kind, details, artifact_id=None, page_id=None, severity='warning'):
    conn.execute('INSERT INTO quality_issues(artifact_id,page_id,issue_type,severity,details_json,created_at) VALUES(?,?,?,?,?,?)',
                 (artifact_id,page_id,kind,severity,dumps(details),now()))
