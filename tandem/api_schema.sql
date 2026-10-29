CREATE TABLE IF NOT EXISTS api_runs(
 id INTEGER PRIMARY KEY,started_at TEXT NOT NULL,finished_at TEXT,status TEXT NOT NULL,
 region TEXT NOT NULL DEFAULT 'EU',requested_start TEXT,requested_end TEXT,summary_json TEXT,error_code TEXT);
CREATE TABLE IF NOT EXISTS api_payloads(
 id INTEGER PRIMARY KEY,sha256 TEXT NOT NULL UNIQUE,content BLOB NOT NULL,byte_count INTEGER NOT NULL,received_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS api_receipts(
 id INTEGER PRIMARY KEY,run_id INTEGER NOT NULL REFERENCES api_runs(id),payload_id INTEGER NOT NULL REFERENCES api_payloads(id),
 endpoint TEXT NOT NULL,device_id TEXT,start_date TEXT,end_date TEXT,status TEXT NOT NULL,error_code TEXT);
CREATE TABLE IF NOT EXISTS api_snapshots(
 id INTEGER PRIMARY KEY,payload_id INTEGER NOT NULL REFERENCES api_payloads(id),device_id TEXT NOT NULL,pump_serial TEXT NOT NULL,
 received_at TEXT NOT NULL,uploaded_at_source TEXT,details_json TEXT NOT NULL,UNIQUE(payload_id,device_id));
CREATE TABLE IF NOT EXISTS api_events(
 id INTEGER PRIMARY KEY,device_id TEXT NOT NULL,pump_serial TEXT NOT NULL,identity_key TEXT NOT NULL,
 identity_method TEXT NOT NULL,sequence_group INTEGER,sequence_number INTEGER,event_code INTEGER,
 event_name TEXT,kind TEXT NOT NULL,local_timestamp TEXT,local_date TEXT,clock_status TEXT NOT NULL,
 unit TEXT,value REAL,values_json TEXT NOT NULL,decode_status TEXT NOT NULL,raw_json TEXT NOT NULL,sha256 TEXT NOT NULL,
 decoder_version TEXT NOT NULL,UNIQUE(device_id,identity_key,sha256));
CREATE INDEX IF NOT EXISTS api_event_dates ON api_events(local_date,kind);
CREATE INDEX IF NOT EXISTS api_event_identity ON api_events(device_id,identity_key);
CREATE TABLE IF NOT EXISTS api_event_sources(
 event_id INTEGER NOT NULL REFERENCES api_events(id),payload_id INTEGER NOT NULL REFERENCES api_payloads(id),
 stream TEXT NOT NULL,ordinal INTEGER NOT NULL,PRIMARY KEY(payload_id,stream,ordinal));
CREATE TABLE IF NOT EXISTS api_windows(
 id INTEGER PRIMARY KEY,receipt_id INTEGER NOT NULL UNIQUE REFERENCES api_receipts(id),device_id TEXT NOT NULL,
 start_date TEXT NOT NULL,end_date TEXT NOT NULL,event_count INTEGER NOT NULL,clock_count INTEGER NOT NULL,completed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS source_links(
 id INTEGER PRIMARY KEY,event_id INTEGER NOT NULL REFERENCES api_events(id),source_table TEXT NOT NULL,source_id INTEGER NOT NULL,
 relation TEXT NOT NULL,details_json TEXT NOT NULL,UNIQUE(event_id,source_table,source_id,relation));
CREATE VIEW IF NOT EXISTS v_api_events AS
 SELECT e.*, (SELECT count(*) FROM api_events x WHERE x.device_id=e.device_id AND x.identity_key=e.identity_key) revision_count
 FROM api_events e;
CREATE VIEW IF NOT EXISTS v_source_links AS SELECT * FROM source_links;

CREATE INDEX IF NOT EXISTS records_device_time ON records(pump_serial,local_timestamp,kind);

CREATE INDEX IF NOT EXISTS api_event_sources_event ON api_event_sources(event_id);
CREATE VIEW IF NOT EXISTS v_api_measurements AS
SELECT id event_id,device_id,pump_serial,kind,local_timestamp log_local_timestamp,
 CASE WHEN kind='cgm' THEN json_extract(values_json,'$.measurement_local_timestamp') ELSE local_timestamp END measurement_local_timestamp,
 unit,value,decode_status,clock_status,decoder_version FROM api_events WHERE kind IN ('cgm','bg');
CREATE VIEW IF NOT EXISTS v_api_state_transitions AS
SELECT e.id event_id,e.device_id,e.pump_serial,e.local_timestamp,
 json_extract(t.value,'$.state') state,json_extract(t.value,'$.action') action,
 e.decode_status,e.clock_status FROM api_events e,json_each(e.values_json,'$.state_transitions') t;
