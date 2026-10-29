import io,json,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from tandem.db import connect,store_artifact
from tandem.visual import axes,chart,chart_words,expand,groups,minute,native_events,png,summary_series,enrich_assets


class Visual(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.c=connect(Path(self.temp.name)/'test.sqlite')
        with self.c:
            a,_=store_artifact(self.c,b'fixture','fixture','application/pdf','fixture',None)
            self.page=self.c.execute("INSERT INTO pdf_pages(artifact_id,page_number,width_points,height_points,native_text,words_json,raster_image_count) VALUES(?,1,612,792,'','[]',0)",(a,)).lastrowid
            self.image=self.c.execute("INSERT INTO report_images(page_id,block_number,image_kind,bbox_json,width,height,sha256,image_png,local_date) VALUES(?,1,'daily_chart','[0,0,612,240]',2432,974,'synthetic',?,'2026-10-25')",(self.page,png(np.ones((974,2432,3),dtype='uint8')*255))).lastrowid

    def tearDown(self):self.c.close();self.temp.cleanup()

    def layout(self,partial=False):
        a=np.ones((974,2432,3),dtype='uint8')*255
        a[633:637,56:900 if partial else 2296]=[0,118,174]
        a[739:743,56:2296]=[138,138,138]
        return a

    def test_clock_partial_grid_stays_24_hours(self):
        a=self.layout(True);axis=axes(a)
        self.assertEqual(axis[:2],(56,2295))
        self.assertEqual(minute(2295,axis),1440)
        self.assertLess(minute(900,axis),600)

    def test_unknown_band_is_recorded_without_inventing_sleep(self):
        a=self.layout();a[715:738,80:600]=226
        with self.c:chart(self.c,self.image,a,'2026-10-25',[])
        r=self.c.execute('SELECT * FROM state_intervals').fetchone()
        self.assertEqual(r['state'],'unclassified_event_duration')
        self.assertEqual(r['review_status'],'visual_unreviewed')
        self.assertEqual(self.c.execute("SELECT count(*) FROM state_intervals WHERE state='sleep'").fetchone()[0],0)

    def test_no_active_trace_clock_panel_stays_empty(self):
        a=np.ones((977,2432,3),dtype='uint8')*255;a[70:900,1200:1204]=[240,0,240]
        result=chart(self.c,self.image,a,'2026-10-25',[])
        self.assertTrue(result['empty_clock_change_panel'])
        self.assertEqual(self.c.execute('SELECT count(*) FROM state_intervals').fetchone()[0],0)

    def test_auto_suspension_does_not_mean_physical_disconnection(self):
        a=self.layout();a[745:885,700:740]=[255,170,170]
        with self.c:chart(self.c,self.image,a,'2026-10-25',[])
        r=self.c.execute("SELECT * FROM chart_observations WHERE observation_type='automatic_suspension'").fetchone()
        self.assertIsNotNone(r)
        self.assertEqual(json.loads(r['details_json'])['physical_disconnection'],'not_inferred')
        self.assertGreater(r['uncertainty_minutes'],0)

    def test_multiple_native_alerts_are_all_preserved(self):
        import pymupdf
        d=pymupdf.open();p=d.new_page();p.insert_text((50,300),'Alertas de MCG: 04:15 - Aviso uno. 05:30 - Aviso dos.')
        with self.c:native_events(self.c,self.page,p)
        rows=self.c.execute('SELECT time_local,review_status FROM report_text_events ORDER BY time_local').fetchall()
        self.assertEqual([r[0] for r in rows],['2026-10-25T04:15:00','2026-10-25T05:30:00'])
        self.assertTrue(all(r[1]=='date_unreviewed' for r in rows));d.close()

    def test_changed_axis_template_is_rejected(self):
        with self.assertRaises(ValueError):axes(np.ones((500,900,3),dtype='uint8')*255)

    def test_rebuild_refuses_to_delete_human_review(self):
        with self.c:
            self.c.execute("INSERT INTO chart_labels(image_id,word_index,label_type,text,bbox_json,review_status) VALUES(?,1,'graph_text','x','[]','reviewed_accepted')",(self.image,))
        with self.assertRaisesRegex(ValueError,'revisados'):expand(self.c,True)

    def test_connection_stripes_registered_separately_from_pump_disconnection(self):
        import cv2
        a=self.layout()
        for x in range(500,620,12):cv2.line(a,(x,735),(x+20,715),(138,138,138),4)
        with self.c:self.c.execute('UPDATE report_images SET image_png=? WHERE id=?',(png(a),self.image))
        enrich_assets(self.c)
        row=self.c.execute("SELECT * FROM chart_observations WHERE observation_type='cgm_connection_lost'").fetchone()
        self.assertIsNotNone(row)
        self.assertTrue(json.loads(row['details_json'])['not_physical_pump_disconnection'])

    def test_percentile_series_has_explicit_estimated_units(self):
        a=np.ones((632,2440,3),dtype='uint8')*255
        a[137:139,44:2304]=223;a[528:532,44:2304]=138
        a[345:356,44:2304]=213;a[349:353,44:2304]=60
        with self.c:result=summary_series(self.c,self.image,a)
        self.assertEqual(result['status'],'digitized_unreviewed')
        row=self.c.execute("SELECT * FROM visual_series WHERE series_name='p50'").fetchone()
        self.assertEqual(row['coordinate_system'],'minutes_mg_dl_digitized')
        self.assertAlmostEqual(json.loads(row['points_json'])[0][1],181.6,delta=3)

    def test_clock_notice_uses_only_a_unique_year_inside_requested_period(self):
        import pymupdf
        with self.c:self.c.execute("UPDATE artifacts SET period_start='2026-09-27',period_end='2026-10-26'")
        d=pymupdf.open();p=d.new_page()
        p.insert_text((40,40),'cambio de hora de la bomba de 25 oct a 10:30')
        with self.c:native_events(self.c,self.page,p)
        row=self.c.execute("SELECT time_local,review_status FROM report_text_events WHERE event_type='clock_change_notice'").fetchone()
        self.assertEqual(row[0],'2026-10-25T10:30:00');self.assertEqual(row[1],'source_text');d.close()

    def test_mixed_pump_alarm_and_cgm_alert_block_keeps_both_types(self):
        import pymupdf
        d=pymupdf.open();p=d.new_page()
        p.insert_text((20,300),'Alarmas de la bomba: 10:38 - Temperatura. Alertas de MCG: 10:42 - Fuera de alcance.',fontsize=9)
        with self.c:native_events(self.c,self.page,p)
        rows=self.c.execute('SELECT event_type,description FROM report_text_events ORDER BY time_local').fetchall()
        self.assertEqual([r[0] for r in rows],['pump_alarm','cgm_alert'])
        self.assertNotIn('MCG',rows[0][1])
        with self.c:native_events(self.c,self.page,p)
        self.assertEqual(self.c.execute('SELECT count(*) FROM report_text_events').fetchone()[0],2);d.close()


if __name__=='__main__':unittest.main()
