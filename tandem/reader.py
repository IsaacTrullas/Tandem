"""Versioned, read-only access for local consumer programs.

No connection returned by this module can update Tandem's database. Source
families remain distinct: API, CSV and visual observations must not be added
together as independent insulin doses.
"""
from __future__ import annotations

import base64
from datetime import date, datetime, timezone
import json
from pathlib import Path
import sqlite3

DATASETS = {
    'glucose': ('v_glucose', ('id',), ('local_date', 'local_timestamp')),
    'boluses': ('v_boluses', ('id',), ('local_date', 'local_timestamp')),
    'carbohydrates': ('v_carbohydrates', ('id',), ('local_date', 'local_timestamp')),
    'states': ('v_states', ('id',), ('local_date',)),
    'report_fields': ('v_report_fields', ('id',), ('period_start',)),
    'api_events': ('v_api_events', ('id',), ('local_timestamp',)),
    'source_links': ('v_source_links', ('event_id', 'source_table', 'source_id', 'relation'), ()),
    'api_runs': ('api_runs', ('id',), ('started_at',)),
    'api_snapshots': ('api_snapshots', ('id',), ('received_at', 'fetched_at', 'created_at')),
    'records': ('records', ('id',), ('local_date', 'local_timestamp')),
    'basal_doses': ('basal_doses', ('record_id',), ()),
    'basal_hourly': ('basal_hourly', ('record_id', 'hour'), ()),
    'profiles': ('profiles', ('id',), ('as_of_date',)),
    'profile_segments': ('profile_segments', ('profile_id', 'start_time'), ()),
    'visual_series': ('visual_series', ('id',), ()),
    'quantitative_layers': ('quantitative_layers', ('id',), ()),
    'report_metrics': ('report_metrics', ('id',), ()),
    'clock_observations': ('clock_observations', ('id',), ('after_local',)),
}
MAX_PAGE_SIZE = 10000
EXPORT_FORMAT = 'tandem-local-jsonl/1'


def _json_default(value):
    if isinstance(value, bytes):
        return {'encoding': 'base64', 'data': base64.b64encode(value).decode('ascii')}
    raise TypeError('Tipo no serializable: ' + type(value).__name__)


class Reader:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self._conn = sqlite3.connect(self.path.as_uri() + '?mode=ro', uri=True, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute('PRAGMA query_only=ON')

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def datasets(self):
        existing = {r[0] for r in self._conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table','view')")}
        return [name for name, (table, _, _) in DATASETS.items() if table in existing]

    def _query(self, dataset, since, until, limit, offset):
        if dataset not in DATASETS:
            raise ValueError('Conjunto de datos no permitido')
        if dataset not in self.datasets():
            raise ValueError('Conjunto de datos no disponible en esta base')
        if type(limit) is not int or not 1 <= limit <= MAX_PAGE_SIZE:
            raise ValueError(f'limit debe estar entre 1 y {MAX_PAGE_SIZE}')
        if type(offset) is not int or offset < 0:
            raise ValueError('offset debe ser un entero no negativo')
        for bound in (since, until):
            if bound is not None:
                if not isinstance(bound, str) or date.fromisoformat(bound).isoformat() != bound:
                    raise ValueError('Fechas en formato YYYY-MM-DD')
        if since and until and since > until:
            raise ValueError('El inicio es posterior al final')
        table, order, dates = DATASETS[dataset]
        columns = {d[0] for d in self._conn.execute('SELECT * FROM ' + table + ' LIMIT 0').description}
        date_column = next((c for c in dates if c in columns), None)
        if (since or until) and not date_column:
            raise ValueError('Este conjunto no admite filtro por fecha')
        where, args = [], []
        if since:
            where.append('substr(' + date_column + ',1,10)>=?'); args.append(since)
        if until:
            where.append('substr(' + date_column + ',1,10)<=?'); args.append(until)
        # All SQL identifiers originate exclusively in DATASETS, never in inputs.
        sql = 'SELECT * FROM ' + table
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        sql += ' ORDER BY ' + ','.join(order) + ' LIMIT ? OFFSET ?'
        return sql, args + [limit, offset]

    def rows(self, dataset, *, since=None, until=None, limit=1000, offset=0):
        sql, args = self._query(dataset, since, until, limit, offset)
        return [dict(r) for r in self._conn.execute(sql, args)]

    def export_jsonl(self, dataset, output, *, since=None, until=None, page_size=1000):
        """Stream all matching rows under one consistent SQLite read snapshot.

        The first JSONL object is metadata; subsequent objects wrap each record.
        Existing files are never overwritten. A failed export is removed so that
        a partial file cannot be mistaken for a complete one.
        """
        self._query(dataset, since, until, page_size, 0)
        output = Path(output)
        if output.resolve() == self.path:
            raise ValueError('La salida no puede ser la base de datos')
        if self._conn.in_transaction:
            raise RuntimeError('Hay una lectura transaccional en curso')
        count = 0
        created = False
        self._conn.execute('BEGIN')
        try:
            version = self._conn.execute('SELECT max(version) FROM schema_version').fetchone()[0]
            metadata = {'type': 'metadata', 'format': EXPORT_FORMAT, 'schema_version': version,
                        'dataset': dataset, 'source_view': DATASETS[dataset][0],
                        'exported_at': datetime.now(timezone.utc).isoformat(),
                        'filters': {'since': since, 'until': until},
                        'time_semantics': 'Original device times; no inferred UTC conversion',
                        'source_semantics': 'Source records and evidence; do not sum overlapping sources'}
            with output.open('x', encoding='utf-8', newline='\n') as stream:
                created = True
                stream.write(json.dumps(metadata, ensure_ascii=False) + '\n')
                while True:
                    page = self.rows(dataset, since=since, until=until, limit=page_size, offset=count)
                    if not page:
                        break
                    for row in page:
                        stream.write(json.dumps({'type': 'record', 'data': row}, ensure_ascii=False,
                                                default=_json_default) + '\n')
                    count += len(page)
                stream.write(json.dumps({'type': 'complete', 'records': count}) + '\n')
            return {'output': str(output), 'dataset': dataset, 'records': count, 'format': EXPORT_FORMAT}
        except Exception:
            if created:
                output.unlink(missing_ok=True)
            raise
        finally:
            self._conn.rollback()
