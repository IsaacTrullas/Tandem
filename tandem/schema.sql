PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY, installed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS import_runs(
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
 source_path TEXT NOT NULL, summary_json TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS artifacts(
 id INTEGER PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, filename TEXT NOT NULL, mime_type TEXT NOT NULL,
 byte_count INTEGER NOT NULL, content BLOB NOT NULL, first_seen_at TEXT NOT NULL,
 period_start TEXT, period_end TEXT, export_generated_local TEXT, metadata_json TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'stored');
CREATE TABLE IF NOT EXISTS artifact_locations(
 artifact_id INTEGER NOT NULL REFERENCES artifacts(id), path TEXT NOT NULL, run_id INTEGER REFERENCES import_runs(id),
 PRIMARY KEY(artifact_id,path));
CREATE TABLE IF NOT EXISTS artifact_links(
 parent_id INTEGER NOT NULL REFERENCES artifacts(id), child_id INTEGER NOT NULL REFERENCES artifacts(id),
 relation TEXT NOT NULL, PRIMARY KEY(parent_id,child_id,relation));
CREATE TABLE IF NOT EXISTS artifact_receipts(
 id INTEGER PRIMARY KEY, artifact_id INTEGER NOT NULL REFERENCES artifacts(id),
 period_start TEXT NOT NULL, period_end TEXT NOT NULL, source_path TEXT NOT NULL,
 observed_at TEXT NOT NULL, metadata_json TEXT NOT NULL,
 UNIQUE(artifact_id,period_start,period_end,source_path));
INSERT OR IGNORE INTO artifact_receipts(artifact_id,period_start,period_end,source_path,observed_at,metadata_json)
 SELECT id,period_start,period_end,filename,first_seen_at,metadata_json FROM artifacts WHERE period_start IS NOT NULL AND period_end IS NOT NULL;
CREATE TABLE IF NOT EXISTS raw_rows(
 id INTEGER PRIMARY KEY, artifact_id INTEGER NOT NULL REFERENCES artifacts(id), row_number INTEGER NOT NULL,
 kind TEXT NOT NULL, raw_json TEXT NOT NULL, sha256 TEXT NOT NULL,
 UNIQUE(artifact_id,row_number));
CREATE TABLE IF NOT EXISTS records(
 id INTEGER PRIMARY KEY, fingerprint TEXT NOT NULL, occurrence INTEGER NOT NULL,
 kind TEXT NOT NULL, pump_serial TEXT NOT NULL, local_timestamp TEXT NOT NULL,
 local_date TEXT NOT NULL, timezone_name TEXT, utc_timestamp TEXT,
 clock_status TEXT NOT NULL DEFAULT 'device_local_unresolved', values_json TEXT NOT NULL,
 UNIQUE(fingerprint,occurrence));
CREATE INDEX IF NOT EXISTS records_time ON records(kind,local_timestamp);
CREATE INDEX IF NOT EXISTS records_date ON records(local_date,kind);
CREATE TABLE IF NOT EXISTS record_sources(
 record_id INTEGER NOT NULL REFERENCES records(id), raw_row_id INTEGER NOT NULL REFERENCES raw_rows(id),
 clock_segment INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(record_id,raw_row_id));
CREATE TABLE IF NOT EXISTS glucose_readings(
 record_id INTEGER PRIMARY KEY REFERENCES records(id), origin TEXT NOT NULL,
 glucose_mg_dl REAL NOT NULL, description TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS boluses(
 record_id INTEGER PRIMARY KEY REFERENCES records(id), bolus_type TEXT, delivery_method TEXT,
 glucose_mg_dl REAL, delivered_units REAL, food_units REAL, correction_units REAL, completion_status TEXT,
 extended_start_local TEXT, extended_end_local TEXT, extended_units REAL, extended_status TEXT,
 standard_percent REAL, duration_minutes REAL, carbohydrate_grams REAL, target_glucose_mg_dl REAL,
 correction_factor_mg_dl_per_unit REAL, carbohydrate_ratio_g_per_unit REAL);
CREATE TABLE IF NOT EXISTS carbohydrate_entries(
 bolus_record_id INTEGER PRIMARY KEY REFERENCES boluses(record_id), grams REAL NOT NULL,
 timestamp_meaning TEXT NOT NULL DEFAULT 'bolus_completion_not_meal_time',
 food_name TEXT, origin TEXT NOT NULL DEFAULT 'csv_bolus');
CREATE TABLE IF NOT EXISTS basal_doses(
 record_id INTEGER PRIMARY KEY REFERENCES records(id), prescribed_units REAL NOT NULL);
CREATE TABLE IF NOT EXISTS basal_hourly(
 record_id INTEGER NOT NULL REFERENCES records(id), hour INTEGER NOT NULL CHECK(hour BETWEEN 0 AND 23),
 delivered_units REAL, PRIMARY KEY(record_id,hour));
CREATE TABLE IF NOT EXISTS clock_observations(
 id INTEGER PRIMARY KEY, artifact_id INTEGER NOT NULL REFERENCES artifacts(id), raw_row_id INTEGER REFERENCES raw_rows(id),
 before_local TEXT, after_local TEXT, observation_type TEXT NOT NULL, details_json TEXT NOT NULL,
 UNIQUE(artifact_id,raw_row_id,observation_type));
CREATE TABLE IF NOT EXISTS pdf_pages(
 id INTEGER PRIMARY KEY, artifact_id INTEGER NOT NULL REFERENCES artifacts(id), page_number INTEGER NOT NULL,
 width_points REAL NOT NULL, height_points REAL NOT NULL, native_text TEXT NOT NULL, words_json TEXT NOT NULL,
 raster_image_count INTEGER NOT NULL, rendered_png BLOB, ocr_text TEXT, ocr_json TEXT,
 ocr_engine TEXT, ocr_status TEXT NOT NULL DEFAULT 'pending', ocr_error TEXT,
 UNIQUE(artifact_id,page_number));
CREATE TABLE IF NOT EXISTS pdf_facts(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), category TEXT NOT NULL,
 name TEXT NOT NULL, local_date TEXT, value_json TEXT NOT NULL, evidence_text TEXT NOT NULL,
 bbox_json TEXT, extraction_method TEXT NOT NULL, review_status TEXT NOT NULL,
 UNIQUE(page_id,category,name,local_date,evidence_text));
CREATE TABLE IF NOT EXISTS daily_panels(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), local_date TEXT NOT NULL,
 panel_index INTEGER NOT NULL, bbox_json TEXT NOT NULL, header_text TEXT NOT NULL,
 facts_json TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'ocr_unreviewed',
 UNIQUE(page_id,panel_index));
CREATE INDEX IF NOT EXISTS panels_date ON daily_panels(local_date);
CREATE TABLE IF NOT EXISTS therapy_events(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), panel_id INTEGER REFERENCES daily_panels(id),
 event_type TEXT NOT NULL, local_date TEXT, start_local TEXT, end_local TEXT,
 evidence_text TEXT NOT NULL, bbox_json TEXT, extraction_method TEXT NOT NULL,
 review_status TEXT NOT NULL, details_json TEXT NOT NULL,
 UNIQUE(page_id,event_type,evidence_text,bbox_json));
CREATE TABLE IF NOT EXISTS profiles(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), name TEXT NOT NULL,
 active_at_upload INTEGER NOT NULL, as_of_date TEXT, duration_hours REAL, daily_basal_units REAL,
 source_text TEXT NOT NULL, UNIQUE(page_id,name));
CREATE TABLE IF NOT EXISTS profile_segments(
 profile_id INTEGER NOT NULL REFERENCES profiles(id), start_time TEXT NOT NULL,
 basal_rate_units_per_hour REAL NOT NULL, correction_factor_mg_dl_per_unit REAL NOT NULL,
 carbohydrate_ratio_g_per_unit REAL NOT NULL, target_glucose_mg_dl REAL NOT NULL,
 PRIMARY KEY(profile_id,start_time));
CREATE TABLE IF NOT EXISTS quality_issues(
 id INTEGER PRIMARY KEY, artifact_id INTEGER REFERENCES artifacts(id), page_id INTEGER REFERENCES pdf_pages(id),
 issue_type TEXT NOT NULL, severity TEXT NOT NULL, details_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sync_runs(
 id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT, status TEXT NOT NULL,
 plan_json TEXT NOT NULL, download_manifest_json TEXT, summary_json TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS review_log(
 id INTEGER PRIMARY KEY, target_table TEXT NOT NULL, target_id INTEGER NOT NULL,
 decision TEXT NOT NULL, reviewer TEXT NOT NULL, reviewed_at TEXT NOT NULL, note TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS pdf_extractions(
 page_id INTEGER NOT NULL REFERENCES pdf_pages(id), extractor TEXT NOT NULL, version TEXT NOT NULL,
 status TEXT NOT NULL, extracted_at TEXT NOT NULL, details_json TEXT NOT NULL,
 PRIMARY KEY(page_id,extractor,version));
CREATE TABLE IF NOT EXISTS report_images(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), block_number INTEGER NOT NULL,
 image_kind TEXT NOT NULL, bbox_json TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
 sha256 TEXT NOT NULL, image_png BLOB NOT NULL, local_date TEXT, panel_id INTEGER REFERENCES daily_panels(id),
 UNIQUE(page_id,block_number));
CREATE TABLE IF NOT EXISTS report_fields(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), image_id INTEGER REFERENCES report_images(id),
 section TEXT NOT NULL, field_key TEXT NOT NULL, row_index INTEGER NOT NULL, label TEXT NOT NULL,
 value_text TEXT NOT NULL, values_json TEXT NOT NULL, evidence_text TEXT NOT NULL, bbox_json TEXT NOT NULL,
 scope TEXT NOT NULL, as_of_date TEXT, extraction_method TEXT NOT NULL, review_status TEXT NOT NULL,
 UNIQUE(page_id,image_id,row_index));
CREATE TABLE IF NOT EXISTS sleep_schedules(
 id INTEGER PRIMARY KEY, field_id INTEGER NOT NULL UNIQUE REFERENCES report_fields(id),
 as_of_date TEXT, weekdays_json TEXT NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
 enabled INTEGER NOT NULL, is_actual_sleep INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS legend_templates(
 id INTEGER PRIMARY KEY, page_id INTEGER NOT NULL REFERENCES pdf_pages(id), event_type TEXT NOT NULL,
 source_label TEXT NOT NULL, bbox_json TEXT NOT NULL, image_png BLOB NOT NULL, mask_png BLOB NOT NULL,
 UNIQUE(page_id,event_type));
CREATE TABLE IF NOT EXISTS chart_observations(
 id INTEGER PRIMARY KEY, image_id INTEGER NOT NULL REFERENCES report_images(id),
 observation_key TEXT NOT NULL, observation_type TEXT NOT NULL, local_date TEXT,
 bbox_json TEXT NOT NULL, minute_start REAL, minute_end REAL, uncertainty_minutes REAL,
 match_score REAL, template_id INTEGER REFERENCES legend_templates(id), evidence_png BLOB NOT NULL,
 details_json TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'visual_unreviewed',
 UNIQUE(image_id,observation_key));
CREATE TABLE IF NOT EXISTS state_intervals(
 id INTEGER PRIMARY KEY, observation_id INTEGER NOT NULL UNIQUE REFERENCES chart_observations(id),
 state TEXT NOT NULL, local_date TEXT NOT NULL, start_local TEXT, end_local TEXT,
 start_minute REAL NOT NULL, end_minute REAL NOT NULL, uncertainty_minutes REAL NOT NULL,
 left_censored INTEGER NOT NULL, right_censored INTEGER NOT NULL,
 time_basis TEXT NOT NULL, review_status TEXT NOT NULL DEFAULT 'visual_unreviewed');
CREATE TABLE IF NOT EXISTS visual_series(
 id INTEGER PRIMARY KEY, image_id INTEGER NOT NULL REFERENCES report_images(id), series_name TEXT NOT NULL,
 coordinate_system TEXT NOT NULL, points_json TEXT NOT NULL, interpretation_json TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'visual_unreviewed', UNIQUE(image_id,series_name));
CREATE TABLE IF NOT EXISTS chart_labels(
 id INTEGER PRIMARY KEY,image_id INTEGER NOT NULL REFERENCES report_images(id),word_index INTEGER NOT NULL,
 label_type TEXT NOT NULL,text TEXT NOT NULL,bbox_json TEXT NOT NULL,local_date TEXT,
 minute_lower REAL,minute_upper REAL,extraction_method TEXT NOT NULL DEFAULT 'windows_ocr',
 review_status TEXT NOT NULL DEFAULT 'ocr_unreviewed',UNIQUE(image_id,word_index));
CREATE TABLE IF NOT EXISTS report_text_events(
 id INTEGER PRIMARY KEY,page_id INTEGER NOT NULL REFERENCES pdf_pages(id),image_id INTEGER REFERENCES report_images(id),
 event_type TEXT NOT NULL,local_date TEXT,time_local TEXT,description TEXT NOT NULL,evidence_text TEXT NOT NULL,
 bbox_json TEXT NOT NULL,extraction_method TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'date_unreviewed',
 UNIQUE(page_id,event_type,evidence_text,bbox_json));
CREATE TABLE IF NOT EXISTS native_text_blocks(
 id INTEGER PRIMARY KEY,page_id INTEGER NOT NULL REFERENCES pdf_pages(id),block_number INTEGER NOT NULL,
 text TEXT NOT NULL,bbox_json TEXT NOT NULL,spans_json TEXT NOT NULL,UNIQUE(page_id,block_number));
CREATE TABLE IF NOT EXISTS report_metrics(
 id INTEGER PRIMARY KEY,page_id INTEGER NOT NULL REFERENCES pdf_pages(id),image_id INTEGER REFERENCES report_images(id),
 metric_key TEXT NOT NULL,value REAL,unit TEXT NOT NULL,qualifier TEXT NOT NULL,evidence_text TEXT NOT NULL,
 bbox_json TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'layout_unreviewed',
 UNIQUE(page_id,image_id,metric_key,qualifier));
CREATE TABLE IF NOT EXISTS report_image_masks(
 image_id INTEGER PRIMARY KEY REFERENCES report_images(id),mask_png BLOB NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS native_drawings(
 page_id INTEGER NOT NULL REFERENCES pdf_pages(id),drawing_index INTEGER NOT NULL,
 drawing_json TEXT NOT NULL,PRIMARY KEY(page_id,drawing_index));
CREATE TABLE IF NOT EXISTS pdf_layout_verifications(
 page_id INTEGER PRIMARY KEY REFERENCES pdf_pages(id),verified_at TEXT NOT NULL,
 image_blocks_expected INTEGER NOT NULL,image_blocks_stored INTEGER NOT NULL,
 text_blocks_expected INTEGER NOT NULL,text_blocks_stored INTEGER NOT NULL,
 drawings_expected INTEGER NOT NULL,drawings_stored INTEGER NOT NULL,status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS legend_definitions(
 key TEXT PRIMARY KEY,label TEXT NOT NULL,category TEXT NOT NULL,shape TEXT NOT NULL,
 unit TEXT,rule_json TEXT NOT NULL,definition_version TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS legend_instances(
 id INTEGER PRIMARY KEY,page_id INTEGER NOT NULL REFERENCES pdf_pages(id),
 definition_key TEXT NOT NULL REFERENCES legend_definitions(key),label_text TEXT NOT NULL,
 label_bbox_json TEXT NOT NULL,symbol_bbox_json TEXT NOT NULL,symbol_png BLOB NOT NULL,
 sha256 TEXT NOT NULL,style_json TEXT NOT NULL,source_method TEXT NOT NULL,
 UNIQUE(page_id,definition_key));
CREATE TABLE IF NOT EXISTS legend_page_audits(
 page_id INTEGER NOT NULL REFERENCES pdf_pages(id),legend_kind TEXT NOT NULL,
 expected_count INTEGER NOT NULL,found_count INTEGER NOT NULL,unknown_labels_json TEXT NOT NULL,
 missing_keys_json TEXT NOT NULL,status TEXT NOT NULL,checked_at TEXT NOT NULL,
 PRIMARY KEY(page_id,legend_kind));
CREATE TABLE IF NOT EXISTS legend_symbol_hits(
 id INTEGER PRIMARY KEY,image_id INTEGER NOT NULL REFERENCES report_images(id),hit_key TEXT NOT NULL,
 definition_key TEXT NOT NULL REFERENCES legend_definitions(key),legend_instance_id INTEGER REFERENCES legend_instances(id),
 bbox_json TEXT NOT NULL,minute_lower REAL,minute_upper REAL,match_score REAL,
 candidate_scores_json TEXT NOT NULL,evidence_png BLOB NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'visual_unreviewed',UNIQUE(image_id,hit_key));
CREATE TABLE IF NOT EXISTS legend_feature_links(
 definition_key TEXT NOT NULL REFERENCES legend_definitions(key),source_table TEXT NOT NULL,source_id INTEGER NOT NULL,
 relation TEXT NOT NULL,details_json TEXT NOT NULL,
 PRIMARY KEY(definition_key,source_table,source_id,relation));
CREATE TABLE IF NOT EXISTS legend_chart_scans(
 image_id INTEGER PRIMARY KEY REFERENCES report_images(id),version TEXT NOT NULL,status TEXT NOT NULL,
 checked_at TEXT NOT NULL,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plot_calibrations(
 image_id INTEGER PRIMARY KEY REFERENCES report_images(id),version TEXT NOT NULL,status TEXT NOT NULL,
 zero_y REAL,units_per_pixel REAL,uncertainty_units_per_hour REAL,ticks_json TEXT NOT NULL,
 focused_ocr_json TEXT NOT NULL,details_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS quantitative_layers(
 id INTEGER PRIMARY KEY,image_id INTEGER NOT NULL REFERENCES report_images(id),
 definition_key TEXT NOT NULL REFERENCES legend_definitions(key),layer_key TEXT NOT NULL,
 unit TEXT NOT NULL,points_json TEXT NOT NULL,bbox_json TEXT NOT NULL,evidence_png BLOB NOT NULL,
 details_json TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'visual_unreviewed',
 UNIQUE(image_id,layer_key));
CREATE TABLE IF NOT EXISTS basal_rate_annotations(
 id INTEGER PRIMARY KEY,image_id INTEGER NOT NULL REFERENCES report_images(id),text TEXT NOT NULL,
 rate_units_per_hour REAL NOT NULL,bbox_json TEXT NOT NULL,line_y REAL,minute_position REAL,
 association TEXT NOT NULL,review_status TEXT NOT NULL DEFAULT 'ocr_unreviewed',
 UNIQUE(image_id,text,bbox_json));
CREATE TABLE IF NOT EXISTS extended_bolus_spans(
 id INTEGER PRIMARY KEY,bolus_record_id INTEGER REFERENCES boluses(record_id),image_id INTEGER NOT NULL REFERENCES report_images(id),
 slice_start_local TEXT,slice_end_local TEXT,plot_start_minute REAL NOT NULL,plot_end_minute REAL NOT NULL,
 duration_minutes_csv REAL,total_units_csv REAL,extended_units_csv REAL,endpoint_error_minutes REAL,
 bbox_json TEXT NOT NULL,evidence_png BLOB NOT NULL,details_json TEXT NOT NULL,
 review_status TEXT NOT NULL DEFAULT 'visual_unreviewed',UNIQUE(image_id,bolus_record_id));
CREATE TABLE IF NOT EXISTS quantitative_runs(
 image_id INTEGER PRIMARY KEY REFERENCES report_images(id),version TEXT NOT NULL,status TEXT NOT NULL,
 checked_at TEXT NOT NULL,details_json TEXT NOT NULL);
CREATE VIEW IF NOT EXISTS v_basal_plot_points AS
 SELECT q.id layer_id,q.image_id,q.definition_key,q.unit,q.review_status,
 json_extract(p.value,'$[0]') x_pixel,json_extract(p.value,'$[1]') minute_position,
 json_extract(p.value,'$[2]') y_pixel,json_extract(p.value,'$[3]') value,
 json_extract(p.value,'$[4]') value_method
 FROM quantitative_layers q,json_each(q.points_json) p;
CREATE VIEW IF NOT EXISTS v_legend_coverage AS
 SELECT d.key,d.label,d.category,d.shape,d.unit,
 (SELECT count(*) FROM legend_instances i WHERE i.definition_key=d.key) source_examples,
 (SELECT count(*) FROM legend_symbol_hits h WHERE h.definition_key=d.key) symbol_candidates,
 (SELECT count(*) FROM legend_feature_links f WHERE f.definition_key=d.key) linked_evidence,
 d.rule_json FROM legend_definitions d;
CREATE VIEW IF NOT EXISTS v_states AS
 SELECT s.*,o.image_id,i.page_id,p.artifact_id,p.page_number,a.filename,o.bbox_json,o.details_json
 FROM state_intervals s JOIN chart_observations o ON o.id=s.observation_id
 JOIN report_images i ON i.id=o.image_id JOIN pdf_pages p ON p.id=i.page_id JOIN artifacts a ON a.id=p.artifact_id;
CREATE VIEW IF NOT EXISTS v_report_fields AS
 SELECT f.*,a.period_start,a.period_end,a.filename,p.page_number FROM report_fields f
 JOIN pdf_pages p ON p.id=f.page_id JOIN artifacts a ON a.id=p.artifact_id;
CREATE VIEW IF NOT EXISTS v_event_evidence AS
 SELECT 'chart_observations' source_table,o.id, i.page_id,o.local_date,o.observation_type event_type,
 o.minute_start minute_lower,o.minute_end minute_upper,NULL time_local,o.review_status,o.details_json evidence
 FROM chart_observations o JOIN report_images i ON i.id=o.image_id
 UNION ALL SELECT 'report_text_events',e.id,e.page_id,e.local_date,e.event_type,NULL,NULL,e.time_local,e.review_status,e.evidence_text
 FROM report_text_events e;

CREATE VIEW IF NOT EXISTS v_glucose AS
 SELECT r.id,r.pump_serial,r.local_timestamp,r.local_date,r.clock_status,
 g.origin,g.glucose_mg_dl,g.description,g.note FROM records r JOIN glucose_readings g ON g.record_id=r.id;
CREATE VIEW IF NOT EXISTS v_boluses AS
 SELECT r.id,r.pump_serial,r.local_timestamp,r.local_date,b.* FROM records r JOIN boluses b ON b.record_id=r.id;
CREATE VIEW IF NOT EXISTS v_carbohydrates AS
 SELECT r.id,r.pump_serial,r.local_timestamp,r.local_date,c.grams,c.timestamp_meaning,c.food_name
 FROM records r JOIN carbohydrate_entries c ON c.bolus_record_id=r.id;
CREATE VIEW IF NOT EXISTS v_daily_csv AS
 SELECT r.local_date,
 SUM(CASE WHEN r.kind='MCG' THEN 1 ELSE 0 END) sensor_readings,
 SUM(CASE WHEN r.kind='Bolo' THEN 1 ELSE 0 END) boluses,
 SUM(CASE WHEN r.kind='Dosis basales' THEN 1 ELSE 0 END) basal_records,
 SUM(COALESCE(c.grams,0)) carbohydrate_grams
 FROM records r LEFT JOIN carbohydrate_entries c ON c.bolus_record_id=r.id GROUP BY r.local_date;
CREATE VIEW IF NOT EXISTS v_daily_context AS
 SELECT p.local_date,p.id panel_id,p.facts_json,p.review_status,a.filename,pdf.page_number,p.bbox_json
 FROM daily_panels p JOIN pdf_pages pdf ON pdf.id=p.page_id JOIN artifacts a ON a.id=pdf.artifact_id;
CREATE VIEW IF NOT EXISTS v_pending_review AS
 SELECT 'daily_panels' target_table,id target_id,local_date,review_status,header_text evidence FROM daily_panels WHERE review_status='ocr_unreviewed'
 UNION ALL SELECT 'therapy_events',id,local_date,review_status,evidence_text FROM therapy_events WHERE review_status LIKE '%unreviewed%';
DROP VIEW IF EXISTS v_pending_review;
CREATE VIEW v_pending_review AS
 SELECT 'daily_panels' target_table,id target_id,local_date,review_status,header_text evidence FROM daily_panels WHERE review_status='ocr_unreviewed'
 UNION ALL SELECT 'therapy_events',id,local_date,review_status,evidence_text FROM therapy_events WHERE review_status LIKE '%unreviewed%'
 UNION ALL SELECT 'chart_observations',id,local_date,review_status,details_json FROM chart_observations WHERE review_status LIKE '%unreviewed%'
 UNION ALL SELECT 'report_text_events',id,local_date,review_status,evidence_text FROM report_text_events WHERE review_status LIKE '%unreviewed%'
 UNION ALL SELECT 'report_metrics',id,NULL,review_status,evidence_text FROM report_metrics WHERE review_status LIKE '%unreviewed%';
