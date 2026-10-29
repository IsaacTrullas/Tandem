import io,json,tempfile,unittest
from pathlib import Path
import cv2,numpy as np,pymupdf
from tandem.db import connect,store_artifact,dumps
from tandem.legend import DAILY,DEFINITIONS,seed,daily_page,find_symbols,basal_fragments,crosswalk,scan_charts,encode,trend_page,store_instance


class Legend(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.c=connect(Path(self.temp.name)/'test.sqlite')
        with self.c:
            seed(self.c)
            a,_=store_artifact(self.c,b'synthetic','fixture','application/pdf','fixture',None)
            self.page=self.c.execute("INSERT INTO pdf_pages(artifact_id,page_number,width_points,height_points,native_text,words_json,raster_image_count) VALUES(?,1,612,792,'','[]',0)",(a,)).lastrowid
            self.image=self.c.execute("INSERT INTO report_images(page_id,block_number,image_kind,bbox_json,width,height,sha256,image_png,local_date) VALUES(?,1,'daily_chart','[0,0,585.6,151.68]',2432,974,'synthetic',?,'2026-10-25')",(self.page,encode(np.ones((974,2432,3),dtype='uint8')*255))).lastrowid

    def tearDown(self):self.c.close();self.temp.cleanup()

    def test_complete_inventory_and_independent_glucose_dimensions(self):
        self.assertEqual(len(DAILY),33);self.assertEqual(len(DEFINITIONS),36)
        self.assertEqual(len({d[0] for d in DEFINITIONS}),36)
        row=self.c.execute("SELECT rule_json FROM legend_definitions WHERE key='bg_auto'").fetchone()
        self.assertEqual(json.loads(row[0])['dimension'],'glucose_capture_method')

    def test_missing_and_unknown_labels_are_reported(self):
        d=pymupdf.open();p=d.new_page();p.draw_rect(pymupdf.Rect(18,110,594,219),color=(.8,.8,.8),fill=(1,1,1))
        for x,y,label in [(43,135,'Glucemia alta'),(464,155,'Sueño'),(533,195,'Detener de forma manual'),(112,140,'Nuevo simbolo')]:
            p.insert_text((x,y),label,fontsize=5)
        with self.c:r=daily_page(self.c,self.page,p)
        self.assertEqual(r['found'],3);self.assertEqual(len(r['missing']),30)
        self.assertIn('Nuevo simbolo',r['unknown'])
        self.assertEqual(self.c.execute('SELECT status FROM legend_page_audits').fetchone()[0],'incomplete');d.close()

    def test_color_competition_does_not_merge_food_and_correction(self):
        canvas=np.ones((974,2432,3),dtype='uint8')*255
        templates=[]
        for n,(key,color,x) in enumerate([('bolus_food',(147,206,248),500),('bolus_correction',(0,86,126),800)]):
            glyph=np.ones((51,45,3),dtype='uint8')*255
            cv2.circle(glyph,(22,25),17,color,-1)
            canvas[575:626,x:x+45]=glyph
            templates.append({'definition_key':key,'category':'Bolo','symbol_png':encode(glyph),'id':n+1})
        hits=find_symbols(canvas,templates,(56,2295,633,739))
        self.assertEqual({h['key'] for h in hits},{'bolus_food','bolus_correction'})
        self.assertLess(next(h for h in hits if h['key']=='bolus_food')['box'][0],600)

    def test_zero_continuous_and_temporary_dashes_stay_distinct(self):
        canvas=np.ones((974,2432,3),dtype='uint8')*255
        canvas[887:890,56:2296]=138
        canvas[885:887,300:350]=[216,25,32]
        for x in (700,730,760):canvas[885:887,x:x+20]=[123,180,236]
        with self.c:r=basal_fragments(self.c,self.image,canvas,(56,2295,633,739))
        self.assertIn('basal_zero',r);self.assertIn('basal_zero_temp',r)

    def test_red_hatch_antialias_is_not_orange_temporary_fill(self):
        a=np.ones((974,2432,3),dtype='uint8')*255;a[887:890,56:2296]=138
        a[780:850,600:640]=[249,229,216]
        with self.c:r=basal_fragments(self.c,self.image,a,(56,2295,633,739))
        self.assertNotIn('basal_temporary',r)

    def test_true_orange_fill_is_retained_as_candidate(self):
        a=np.ones((974,2432,3),dtype='uint8')*255;a[887:890,56:2296]=138
        a[780:850,600:640]=[255,240,216]
        with self.c:r=basal_fragments(self.c,self.image,a,(56,2295,633,739))
        self.assertIn('basal_temporary',r)

    def test_unknown_chart_layout_is_an_error_not_an_empty_day(self):
        r=scan_charts(self.c)
        self.assertEqual(len(r['errors']),1)
        self.assertEqual(self.c.execute('SELECT status FROM legend_chart_scans').fetchone()[0],'error')

    def test_csv_override_direction_is_not_fabricated(self):
        from tandem.ingest import KINDS,ingest_csv
        import csv
        row=dict.fromkeys(KINDS['Bolo'],'');row.update({'Número de serie':'SYNTHETIC','Fecha y hora de finalización':'2026-10-25T12:00:00','Tipo de bolo':'Anular'})
        output=io.StringIO();writer=csv.DictWriter(output,fieldnames=KINDS['Bolo']);writer.writeheader();writer.writerow(row)
        with self.c:
            ingest_csv(self.c,output.getvalue().encode(),'fixture.csv','fixture.csv',None)
            crosswalk(self.c)
        rows=self.c.execute("SELECT relation FROM legend_feature_links WHERE definition_key LIKE 'bolus_override_%'").fetchall()
        self.assertEqual(len(rows),2)
        self.assertTrue(all(r[0]=='direction_not_resolved_in_csv' for r in rows))

    def test_ambiguous_ocr_percentile_needs_matching_reference_glyph(self):
        canvas=np.ones((632,2440,3),dtype='uint8')*255
        ocr={'dpi':150,'result':{'lines':[]}}
        for token,x in [('50',1600),('25/75',1900),('10190',2200)]:
            ocr['result']['lines'].append({'words':[{'text':token,'bounding_rect':{'x':x/2,'y':35,'width':20,'height':10}}]})
        for x in range(2137,2180,9):canvas[78:82,x:x+4]=153
        with self.c:
            self.c.execute('UPDATE pdf_pages SET ocr_json=? WHERE id=?',(dumps(ocr),self.page))
            self.c.execute("UPDATE report_images SET image_kind='summary_chart',image_png=? WHERE id=?",(encode(canvas),self.image))
            result=trend_page(self.c,self.page,None)
        self.assertIn('percentiles_10_90',result['missing'])
        crop=canvas[67:93,2135:2185]
        with self.c:
            store_instance(self.c,self.page,'percentiles_10_90','10/90 %',[0,0,1,1],[0,0,1,1],crop,'ocr_label_and_embedded_glyph')
            result=trend_page(self.c,self.page,None)
        self.assertEqual(result['missing'],[])


if __name__=='__main__':unittest.main()
