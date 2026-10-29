"""Complete, source-backed PDF legend and its extraction contract.

Legend inventory, symbol detection and clinical validation are separate stages.
Never turn a source label or a swatch match into an exact clinical event.
"""
from __future__ import annotations
import io,json,re,textwrap,unicodedata
from collections import Counter
from pathlib import Path
import cv2,numpy as np,pymupdf
from PIL import Image,ImageDraw,ImageFont
from .db import dumps,digest,now

VERSION='1.0'
GUIDE_URL='https://www.tandemdiabetes.com/docs/default-source/user-guide/user-guide-tandem-source-professional-es-es-aw1013410.pdf?sfvrsn=d37dd8d7_4'
# key, literal label, family, graphical form, unit, extraction adapter, source destination
DEFINITIONS=[
 ('bg_high','Glucemia alta','Glucemia','círculo naranja','mg/dL','color_symbol','glucose_readings'),
 ('bg_range','Glucemia en rango','Glucemia','círculo verde','mg/dL','color_symbol','glucose_readings'),
 ('bg_low','Glucemia baja','Glucemia','círculo rojo','mg/dL','color_symbol','glucose_readings'),
 ('bg_auto','Glucemia capturada de forma automática','Glucemia','círculo gris con gota','mg/dL','color_symbol','glucose_readings'),
 ('cgm_high','MCG alto','MCG','punto naranja','mg/dL','colored_trace','visual_series'),
 ('cgm_range','MCG en rango','MCG','punto verde','mg/dL','colored_trace','visual_series'),
 ('cgm_low','MCG bajo','MCG','punto rojo','mg/dL','colored_trace','visual_series'),
 ('cgm_fill','Relleno de MCG','MCG','círculo vacío con contorno gris','mg/dL','color_symbol','legend_symbol_hits'),
 ('bolus_food','Posprandial','Bolo','gota azul clara','U','color_symbol','boluses'),
 ('bolus_correction','Corrección','Bolo','gota azul oscura','U','color_symbol','boluses'),
 ('bolus_combined','Posprandial + corrección','Bolo','gota azul clara y oscura','U','color_symbol','boluses'),
 ('bolus_extended','Extendido','Bolo','barra azul clara','U','csv_and_two_endpoint_bar_link','extended_bolus_spans'),
 ('bolus_override_up','Anular aumento','Bolo','gota oliva con flecha arriba','U','color_symbol','legend_symbol_hits'),
 ('bolus_override_down','Anular disminución','Bolo','gota oliva con flecha abajo','U','color_symbol','legend_symbol_hits'),
 ('bolus_quick','Rápido','Bolo','gota azul rayada','U','color_symbol','legend_symbol_hits'),
 ('bolus_auto','Automático','Bolo','gota azul con rombo blanco','U','color_symbol','boluses'),
 ('basal_delivered','Perfil suministrado','Basal','área azul','U/h','profile_area_below_step','quantitative_layers'),
 ('basal_setting','Configuración del perfil','Basal','línea azul con tasa','U/h','numeric_labels_and_step_line','quantitative_layers'),
 ('basal_temporary','Temporal','Basal','área naranja con borde discontinuo','U/h','orange_fill_and_dashed_border','quantitative_layers'),
 ('basal_control_iq','Control-IQ','Basal','barras azules de altura variable','U/h','bright_bar_caps','quantitative_layers'),
 ('basal_zero','0 unidades/hora','Basal','línea roja continua','U/h','basal_zero_line','legend_symbol_hits'),
 ('basal_zero_temp','0 unidades/hora temp.','Basal','línea azul discontinua','U/h','basal_zero_line','legend_symbol_hits'),
 ('basal_auto_suspend','Suspensión automática','Basal','hachurado rojo','U/h','existing_pattern','state_intervals'),
 ('carbs','Carbohidratos (g)','Evento','manzana y número','g','color_symbol','carbohydrate_entries'),
 ('sleep','Sueño','Evento','nube Zzz',None,'existing_symbol','state_intervals'),
 ('exercise','Ejercicio','Evento','persona corriendo',None,'existing_symbol','state_intervals'),
 ('cartridge','Cambio de cartucho o sitio','Evento','círculo con flecha',None,'existing_symbol','chart_observations'),
 ('event_duration','Duración del evento','Evento','banda gris con límite vertical','min','existing_band','state_intervals'),
 ('cgm_lost','Conexión MCG perdida','Evento','hachurado gris','min','existing_pattern','state_intervals'),
 ('cgm_alert','Alerta de MCG','Evento','triángulo con exclamación',None,'existing_symbol_and_native','report_text_events'),
 ('pump_alarm','Alarma de la bomba','Evento','círculo con exclamación',None,'existing_symbol_and_native','report_text_events'),
 ('manual_stop','Detener de forma manual','Evento','círculo con cuadrado',None,'existing_symbol','chart_observations'),
 ('power_off','Apagado','Evento','círculo con símbolo de encendido',None,'existing_symbol','chart_observations'),
 ('percentile_50','50 % medio','Tendencia','línea gris continua','mg/dL','digitized_percentile','visual_series'),
 ('percentiles_25_75','25/75 %','Tendencia','banda gris','mg/dL','digitized_percentile','visual_series'),
 ('percentiles_10_90','10/90 %','Tendencia','líneas grises de puntos','mg/dL','digitized_percentile','visual_series'),
]
DAILY=[d for d in DEFINITIONS if d[2]!='Tendencia']


def normalize(text):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text)).casefold()


def encode(a):
    b=io.BytesIO();Image.fromarray(a).save(b,format='PNG');return b.getvalue()


def seed(conn):
    for key,label,family,shape,unit,adapter,destination in DEFINITIONS:
        caveats=['Las horas de un eje son estimadas; el CSV conserva tiempos del dispositivo.',
                 'Una plantilla de la leyenda no demuestra una aparición en el historial.',
                 'Las evidencias gráficas y CSV del mismo evento no se suman.']
        if family=='Basal':caveats+=['Distinguir tasa U/h de dosis CSV en U. No asignar Control-IQ/temporal por el color azul solamente.']
        if key.startswith('bg_') or key.startswith('cgm_'):
            caveats+=['El color del informe distingue la categoría; no se fija un umbral clínico nuevo.']
        if key=='cgm_fill':caveats+=['La guía del fabricante describe lecturas recuperadas por la bomba, con bordes de color de rango. No se crean lecturas interpoladas ni se les asigna una hora de recepción inventada.']
        if key=='cartridge':caveats+=['La guía agrupa cambio de cartucho, llenado de tubo y llenado de cánula. El subtipo no se decide solo por este icono.']
        if key=='bg_auto':caveats+=['La gota central es un modificador de captura automática. El punto puede ser naranja, verde o rojo: no es una cuarta categoría de rango ni un evento adicional.']
        if key in ('bolus_override_up','bolus_override_down'):
            caveats+=['El CSV solo indica Anular; no se infiere aumento/disminución a partir de ese texto.']
        if key=='event_duration':caveats+=['Es un modificador temporal, no un estado independiente. Los solapamientos requieren resolver a qué símbolo pertenece.']
        if key=='cgm_lost':caveats+=['No equivale a desconexión física de la bomba.']
        implementation='implemented_quantitative_candidate' if key in ('basal_delivered','basal_setting','basal_temporary','basal_control_iq','bolus_extended') else 'implemented_candidate'
        dimension='glucose_capture_method' if key=='bg_auto' else 'glucose_range' if key.startswith('bg_') else 'cgm_fill_modifier' if key=='cgm_fill' else family
        rule={'adapter':adapter,'destination':destination,'caveats':caveats,'implementation_state':implementation,'dimension':dimension,
              'manufacturer_reference':{'url':GUIDE_URL,'printed_pages':[13,14]},
              'contract':'catalogued; every actual hit retains method, evidence and review state',
              'value_reading':'nearby_annotation_or_exact_CSV; never from glyph size'}
        conn.execute('''INSERT INTO legend_definitions VALUES(?,?,?,?,?,?,?)
          ON CONFLICT(key) DO UPDATE SET label=excluded.label,category=excluded.category,shape=excluded.shape,
          unit=excluded.unit,rule_json=excluded.rule_json,definition_version=excluded.definition_version''',
          (key,label,family,shape,unit,dumps(rule),VERSION))


def style_features(rgb):
    mask=rgb.min(2)<240
    pixels=rgb[mask]
    colors=Counter(tuple(int(v) for v in p) for p in pixels)
    return {'palette':[{'rgb':list(c),'pixels':n} for c,n in colors.most_common(8)],
            'ink_pixels':int(mask.sum()),'size':[rgb.shape[1],rgb.shape[0]]}


def store_instance(conn,page_id,key,label,lbox,sbox,rgb,method):
    content=encode(rgb)
    conn.execute('''INSERT OR IGNORE INTO legend_instances
      (page_id,definition_key,label_text,label_bbox_json,symbol_bbox_json,symbol_png,sha256,style_json,source_method)
      VALUES(?,?,?,?,?,?,?,?,?)''',(page_id,key,label,dumps(lbox),dumps(sbox),content,digest(content),dumps(style_features(rgb)),method))


def daily_page(conn,page_id,page):
    blocks=[]
    for b in page.get_text('dict')['blocks']:
        if b['type']==0:
            text=' '.join(' '.join(s['text'] for s in line['spans']) for line in b['lines'])
            blocks.append((text,list(b['bbox'])))
    by_label={normalize(text):(text,box) for text,box in blocks}
    if not all(normalize(x) in by_label for x in ['Glucemia alta','Sueño','Detener de forma manual']):return None
    matched={d[0]:by_label[normalize(d[1])] for d in DAILY if normalize(d[1]) in by_label}
    if not matched:return None
    positions=[(b[0],(b[1]+b[3])/2) for t,b in matched.values()]
    rects=[x['rect'] for x in page.get_drawings() if 500<x['rect'].width<600 and 75<x['rect'].height<200
           and all(x['rect'].contains(pymupdf.Point(*p)) for p in positions)]
    unknown=[]
    if rects:
        outer=min(rects,key=lambda r:r.width*r.height)
        for text,box in blocks:
            if outer.contains(pymupdf.Rect(box)) and normalize(text) not in {normalize(d[1]) for d in DAILY}:
                if not ('Glucosa' in text and 'Basal' in text and 'Evento' in text):unknown.append(text)
    pix=page.get_pixmap(dpi=300,alpha=False)
    rgb=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
    for key,(text,box) in matched.items():
        cx=box[0]-9.5;cy=(box[1]+box[3])/2
        sb=[cx-7.2,cy-7.2,cx+7.2,cy+7.2]
        x0,y0,x1,y1=[round(v*300/72) for v in sb]
        crop=rgb[y0:y1,x0:x1].copy()
        store_instance(conn,page_id,key,text,box,sb,crop,'native_label_and_rendered_glyph')
    missing=[d[0] for d in DAILY if d[0] not in matched]
    conn.execute('''INSERT OR REPLACE INTO legend_page_audits VALUES(?,?,?,?,?,?,?,?)''',
      (page_id,'daily',len(DAILY),len(matched),dumps(unknown),dumps(missing),'complete' if not missing and not unknown else 'incomplete',now()))
    return {'page_id':page_id,'found':len(matched),'missing':missing,'unknown':unknown}


def trend_page(conn,page_id,page):
    row=conn.execute('SELECT ocr_json FROM pdf_pages WHERE id=?',(page_id,)).fetchone()
    if not row or not row[0]:return None
    source=conn.execute("SELECT * FROM report_images WHERE page_id=? AND image_kind='summary_chart'",(page_id,)).fetchone()
    if not source:return None
    ocr=json.loads(row[0]);scale=ocr['dpi']/72;box=json.loads(source['bbox_json'])
    rgb=np.array(Image.open(io.BytesIO(source['image_png'])).convert('RGB'))
    found={}
    for line in ocr['result']['lines']:
        for word in line.get('words',[]):
            r=word['bounding_rect'];cx=(r['x']+r['width']/2)/scale;cy=(r['y']+r['height']/2)/scale
            x=(cx-box[0])/(box[2]-box[0])*rgb.shape[1];y=(cy-box[1])/(box[3]-box[1])*rgb.shape[0]
            if not (rgb.shape[1]*.5<x<rgb.shape[1] and 30<y<115):continue
            token=word['text'].replace('%','').strip()
            ambiguous=token=='10190'
            key={'50':'percentile_50','25/75':'percentiles_25_75','10/90':'percentiles_10_90','10190':'percentiles_10_90'}.get(token)
            if key and key not in found:
                left=(r['x']/scale-box[0])/(box[2]-box[0])*rgb.shape[1]
                # Source glyph sits immediately left of its own label; coordinates retained in PDF points.
                sx0,sx1=int(left-65),int(left-15);sy0,sy1=int(y-13),int(y+13)
                crop=rgb[sy0:sy1,sx0:sx1].copy()
                if ambiguous:
                    reference=conn.execute("SELECT symbol_png FROM legend_instances WHERE definition_key='percentiles_10_90' AND source_method='ocr_label_and_embedded_glyph' LIMIT 1").fetchone()
                    if not reference:continue
                    template=np.array(Image.open(io.BytesIO(reference[0])).convert('RGB'))
                    padded=cv2.copyMakeBorder(crop,4,4,4,4,cv2.BORDER_CONSTANT,value=(255,255,255))
                    score=cv2.matchTemplate(padded,template,cv2.TM_CCOEFF_NORMED).max()
                    if not np.isfinite(score) or score<.8:continue
                sb=[box[0]+sx0/rgb.shape[1]*(box[2]-box[0]),box[1]+sy0/rgb.shape[0]*(box[3]-box[1]),
                    box[0]+sx1/rgb.shape[1]*(box[2]-box[0]),box[1]+sy1/rgb.shape[0]*(box[3]-box[1])]
                lb=[r['x']/scale,r['y']/scale,(r['x']+r['width'])/scale,(r['y']+r['height'])/scale]
                label=next(d[1] for d in DEFINITIONS if d[0]==key)
                store_instance(conn,page_id,key,label,lb,sb,crop,'ocr_10190_context_and_reference_glyph' if ambiguous else 'ocr_label_and_embedded_glyph')
                found[key]=True
    missing=[d[0] for d in DEFINITIONS if d[2]=='Tendencia' and d[0] not in found]
    conn.execute('INSERT OR REPLACE INTO legend_page_audits VALUES(?,?,?,?,?,?,?,?)',
      (page_id,'trend',3,len(found),'[]',dumps(missing),'complete' if not missing else 'incomplete',now()))
    return {'page_id':page_id,'found':len(found),'missing':missing,'unknown':[]}


def catalogue(conn):
    summary={'daily_pages':[],'trend_pages':[],'errors':[]}
    with conn:seed(conn)
    artifacts=conn.execute("SELECT id FROM artifacts WHERE mime_type='application/pdf' AND status='imported'").fetchall()
    for a in artifacts:
        data=conn.execute('SELECT content FROM artifacts WHERE id=?',(a[0],)).fetchone()[0]
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            rows=conn.execute('SELECT id,page_number,native_text FROM pdf_pages WHERE artifact_id=?',(a[0],)).fetchall()
            for row in rows:
                text=row['native_text'];page=doc[row['page_number']-1]
                with conn:
                    if 'Detener de' in text and 'Glucemia alta' in text:
                        result=daily_page(conn,row['id'],page)
                        if result:summary['daily_pages'].append(result)
                    if text.startswith('Resumen general'):
                        result=trend_page(conn,row['id'],page)
                        if result:summary['trend_pages'].append(result)
    summary['errors']=[r for r in summary['daily_pages']+summary['trend_pages'] if r['missing'] or r['unknown']]
    return summary


def tight_symbol(content):
    rgb=np.array(Image.open(io.BytesIO(content)).convert('RGB'))
    ink=rgb.min(2)<235
    ys,xs=np.where(ink)
    if not len(xs):return None
    return rgb[max(0,int(ys.min())-2):min(rgb.shape[0],int(ys.max())+3),
               max(0,int(xs.min())-2):min(rgb.shape[1],int(xs.max())+3)].copy()


def clean_background(rgb):
    a=rgb.copy()
    neutral=(a.max(2)-a.min(2)<5)&(a[:,:,0]>=215)
    a[neutral]=255
    return a


def find_symbols(rgb,templates,axis):
    """Different colour/core/arrow shapes compete; no fixed clinical thresholds."""
    left,right,top,bottom=axis
    hits=[]
    for t in templates:
        key=t['definition_key'];family=t['category']
        if family=='Glucemia' or key=='cgm_fill':y0,y1=75,top-100
        elif family=='Bolo':y0,y1=top-150,top+8
        elif key=='carbs':y0,y1=top+2,bottom-25
        else:continue
        symbol=tight_symbol(t['symbol_png'])
        if symbol is None:continue
        # Rendered symbol size and embedded daily image use the same 300-ppi source scale.
        th,tw=symbol.shape[:2]
        roi=clean_background(rgb[y0:y1,left:right+1]);model=clean_background(symbol)
        if min(th,tw)<4 or th>roi.shape[0] or tw>roi.shape[1]:continue
        if key=='bg_auto':
            # This is an independent central-shape modifier; its gray legend colour is not a glucose range.
            roi_edges=cv2.Canny(cv2.cvtColor(roi,cv2.COLOR_RGB2GRAY),45,130)
            for factor in (1.,1.1,1.2):
                scaled=cv2.resize(model,None,fx=factor,fy=factor,interpolation=cv2.INTER_LINEAR)
                edges=cv2.Canny(cv2.cvtColor(scaled,cv2.COLOR_RGB2GRAY),45,130)
                mh,mw=edges.shape
                score=cv2.matchTemplate(roi_edges,edges,cv2.TM_CCOEFF_NORMED)
                for _ in range(70):
                    _,best,_,location=cv2.minMaxLoc(score)
                    if best<.72:break
                    x,y=location
                    hits.append({'key':key,'instance_id':t['id'],'family':'Glucemia-captura','score':float(best),'color_error':0.,
                      'box':[left+x,y0+y,left+x+mw,y0+y+mh]})
                    cv2.rectangle(score,(x-mw//2,y-mh//2),(x+mw//2,y+mh//2),-1,-1)
            continue
        score=cv2.matchTemplate(roi,model,cv2.TM_CCOEFF_NORMED)
        minimum=.86 if family=='Glucemia' else .9 if key=='cgm_fill' else .78
        for _ in range(450 if key=='cgm_fill' else 70):
            _,best,_,location=cv2.minMaxLoc(score)
            if best<minimum:break
            x,y=location
            patch=roi[y:y+th,x:x+tw]
            color_error=float(np.abs(patch.astype(float)-model).mean()/255)
            if color_error<(.2 if family=='Bolo' else .16):
                hits.append({'key':key,'instance_id':t['id'],'family':family,'score':float(best),'color_error':color_error,
                  'box':[left+x,y0+y,left+x+tw,y0+y+th]})
            cv2.rectangle(score,(x-max(5,tw//2),y-max(5,th//2)),(x+max(5,tw//2),y+max(5,th//2)),-1,-1)
    selected=[]
    for h in sorted(hits,key=lambda h:-(h['score']-h['color_error'])):
        cx=(h['box'][0]+h['box'][2])/2;cy=(h['box'][1]+h['box'][3])/2
        existing=next((v for v in selected if v['family']==h['family'] and
          abs(cx-(v['box'][0]+v['box'][2])/2)<18 and abs(cy-(v['box'][1]+v['box'][3])/2)<22),None)
        alternative={'key':h['key'],'score':h['score'],'color_error':h['color_error']}
        if existing:
            if alternative['key'] not in [a['key'] for a in existing['alternatives']]:existing['alternatives'].append(alternative)
        else:selected.append({**h,'alternatives':[alternative]})
    return sorted(selected,key=lambda h:(h['box'][0],h['box'][1]))


def add_hit(conn,iid,hit_key,key,instance,box,rgb,axis,score=None,alternatives=None):
    from .visual import minute
    x0,y0,x1,y1=[int(v) for v in box]
    margin=35
    # Coordinate/time window is position evidence; symbols may be displaced by the PDF's layout.
    conn.execute('''INSERT OR IGNORE INTO legend_symbol_hits
      (image_id,hit_key,definition_key,legend_instance_id,bbox_json,minute_lower,minute_upper,match_score,
       candidate_scores_json,evidence_png) VALUES(?,?,?,?,?,?,?,?,?,?)''',
      (iid,hit_key,key,instance,dumps(box),minute(x0-margin,axis),minute(x1+margin,axis),score,
       dumps(alternatives or []),encode(rgb[max(0,y0-3):y1+4,max(0,x0-3):x1+4])))


def basal_fragments(conn,iid,rgb,axis):
    """Read explicit zero-rate line and temporary-fill candidates, never infer pump disconnection."""
    from .visual import groups
    left,right,top,bottom=axis;h,w=rgb.shape[:2]
    gray=(rgb.max(2)-rgb.min(2)<3)&(rgb[:,:,0]>=125)&(rgb[:,:,0]<=150)
    rows=[a for a,b in groups(np.where(gray[:,left:right].sum(1)>(right-left)*.75)[0]) if h*.82<a<h*.94]
    if not rows:return []
    base=max(rows)
    result=[]
    roi=rgb[max(bottom+2,base-5):base+2,left:right+1]
    red=(roi[:,:,0]>145)&(roi[:,:,1]<100)&(roi[:,:,2]<100)&(roi[:,:,0]>roi[:,:,1].astype(int)+60)
    for n,(a,b) in enumerate(groups(np.where(red.sum(0)>=1)[0])):
        if b-a<3:continue
        box=[a+left,base-5,b+left,base+2]
        add_hit(conn,iid,f'basal_zero:{n}','basal_zero',None,box,rgb,axis,
                alternatives=[{'method':'red_line_at_basal_zero_axis','not_physical_disconnection':True,'partial_or_overlapping_stroke':True}])
        result.append('basal_zero')
    blue_dash=(roi[:,:,0]>=90)&(roi[:,:,0]<=175)&(roi[:,:,1]>=150)&(roi[:,:,1]<=215)&(roi[:,:,2]>=210)
    runs=[(a,b) for a,b in groups(np.where(blue_dash.sum(0)>=1)[0]) if 6<=b-a<=30]
    chains=[]
    for run in runs:
        if chains and 3<=run[0]-chains[-1][-1][1]<=22:chains[-1].append(run)
        else:chains.append([run])
    for n,chain in enumerate(chains):
        if len(chain)<3:continue
        a,b=chain[0][0]+left,chain[-1][1]+left
        add_hit(conn,iid,f'basal_zero_temp:{n}','basal_zero_temp',None,[a,base-5,b,base+2],rgb,axis,
                alternatives=[{'method':'repeated_light_blue_dashes_at_zero_axis','dash_runs':chain,'requires_review':True}])
        result.append('basal_zero_temp')
    # Orange temporary-region pixels differ from blue delivered/profile/Control-IQ layers.
    roi=rgb[bottom+3:base,left:right+1]
    # Broad orange thresholds confuse red-hatch antialiasing over blue ink with temporary basal.
    orange=np.abs(roi.astype(int)-np.array([255,240,216])).max(2)<=5
    for n,(a,b) in enumerate(groups(np.where(orange.sum(0)>=8)[0],gap=3)):
        if b-a<12:continue
        add_hit(conn,iid,f'basal_temporary:{n}','basal_temporary',None,[a+left,bottom+3,b+left,base],rgb,axis,
                alternatives=[{'method':'orange_fill_candidate; dashed_border_not_yet_verified'}])
        result.append('basal_temporary')
    return result


def crosswalk(conn):
    mappings={'sleep':'sleep','exercise':'exercise','cartridge_or_site_change':'cartridge',
      'cgm_alert_icon':'cgm_alert','pump_alarm_icon':'pump_alarm','manual_stop':'manual_stop',
      'power_off':'power_off','automatic_suspension':'basal_auto_suspend','cgm_connection_lost':'cgm_lost'}
    def link(key,table,identifier,relation,details):
        conn.execute('INSERT OR IGNORE INTO legend_feature_links VALUES(?,?,?,?,?)',(key,table,identifier,relation,dumps(details)))
    for row in conn.execute('SELECT id,observation_type,observation_key,review_status FROM chart_observations').fetchall():
        key=mappings.get(row['observation_type'])
        if key:link(key,'chart_observations',row['id'],'existing_graphic_evidence',{'review_status':row['review_status']})
        if row['observation_key'].startswith('band:'):link('event_duration','chart_observations',row['id'],'duration_modifier',{'not_a_separate_event':True})
    for row in conn.execute("SELECT id,event_type,review_status FROM report_text_events WHERE event_type IN ('cgm_alert','pump_alarm')").fetchall():
        link(row['event_type'],'report_text_events',row['id'],'native_written_time',{'review_status':row['review_status']})
    types={'Posprandial':'bolus_food','Corrección':'bolus_correction','Posprandial/corrección':'bolus_combined','Automático':'bolus_auto'}
    for row in conn.execute('SELECT record_id,bolus_type,delivery_method FROM boluses').fetchall():
        if row['bolus_type'] in types:link(types[row['bolus_type']],'boluses',row['record_id'],'csv_category',{'source':'CSV; not a new PDF event'})
        if row['delivery_method']=='Extendido':link('bolus_extended','boluses',row['record_id'],'csv_delivery_method',{'source':'CSV; duration preserved in boluses'})
        if row['bolus_type']=='Anular':
            for key in ('bolus_override_up','bolus_override_down'):
                link(key,'boluses',row['record_id'],'direction_not_resolved_in_csv',{'not_a_confirmed_up_or_down_event':True})
    for row in conn.execute('SELECT bolus_record_id FROM carbohydrate_entries').fetchall():
        link('carbs','carbohydrate_entries',row[0],'csv_grams',{'not_food_name_or_meal_time':True})
    series={'p50':'percentile_50','p25':'percentiles_25_75','p75':'percentiles_25_75','p10':'percentiles_10_90','p90':'percentiles_10_90',
            'glucose_green':'cgm_range','glucose_orange':'cgm_high'}
    for row in conn.execute('SELECT id,series_name FROM visual_series').fetchall():
        if row['series_name'] in series:
            link(series[row['series_name']],'visual_series',row['id'],'pixel_trace_or_digitized_summary',{'may_include_annotations':row['series_name'].startswith('glucose_')})
        elif row['series_name']=='basal_blue':
            for key in ('basal_delivered','basal_control_iq'):
                link(key,'visual_series',row['id'],'shared_blue_geometry_not_separated',{'semantic_classification':'partial'})
    for row in conn.execute("SELECT id FROM chart_labels WHERE label_type='basal_annotation'").fetchall():
        link('basal_setting','chart_labels',row[0],'ocr_rate_annotation',{'requires_review':True})
    for row in conn.execute('SELECT id,definition_key FROM quantitative_layers').fetchall():
        link(row['definition_key'],'quantitative_layers',row['id'],'separated_quantitative_layer',{'requires_review':True,'not_additional_CSV_insulin':True})
    for row in conn.execute('SELECT id FROM extended_bolus_spans').fetchall():
        link('bolus_extended','extended_bolus_spans',row[0],'unique_bar_CSV_endpoint_match',{'not_an_additional_bolus':True})
    conn.execute("UPDATE legend_feature_links SET details_json=? WHERE relation='shared_blue_geometry_not_separated'",(dumps({'superseded_by':'quantitative_layers','historical_unseparated_evidence':True}),))


def reject_false_temporary_candidates(conn):
    """Preserve false starts as rejected evidence; never overwrite a reviewed decision."""
    rows=conn.execute("SELECT id,evidence_png,candidate_scores_json FROM legend_symbol_hits WHERE definition_key='basal_temporary' AND review_status='visual_unreviewed'").fetchall()
    for row in rows:
        rgb=np.array(Image.open(io.BytesIO(row['evidence_png'])).convert('RGB'))
        exact=np.abs(rgb.astype(int)-np.array([255,240,216])).max(2)<=5
        if (exact.sum(0)>=6).sum()<12:
            details=json.loads(row['candidate_scores_json'])
            details.append({'algorithm_rejection':'broad_color_match; no sufficient exact temporary-fill palette; can be red-hatch antialiasing'})
            conn.execute("UPDATE legend_symbol_hits SET review_status='algorithm_rejected',candidate_scores_json=? WHERE id=?",(dumps(details),row['id']))


def scan_charts(conn):
    from .visual import axes
    summary={'charts':0,'new_candidates':0,'errors':[]}
    rows=conn.execute("SELECT i.id,p.artifact_id FROM report_images i JOIN pdf_pages p ON p.id=i.page_id WHERE i.image_kind='daily_chart' AND NOT EXISTS(SELECT 1 FROM legend_chart_scans s WHERE s.image_id=i.id AND s.version=? AND s.status='complete')",(VERSION,)).fetchall()
    for row in rows:
        try:
            item=conn.execute('SELECT image_png FROM report_images WHERE id=?',(row['id'],)).fetchone()
            rgb=np.array(Image.open(io.BytesIO(item[0])).convert('RGB'))
            try:axis=axes(rgb)
            except ValueError:
                # A clock-split panel with no active trace has no symbols to scan; preserve its existing extraction record.
                h=rgb.shape[0]
                blue=(rgb[:,:,0]<20)&(rgb[:,:,1]>100)&(rgb[:,:,1]<140)&(rgb[:,:,2]>150)&(rgb[:,:,2]<200)
                magenta=(rgb[:,:,0]>180)&(rgb[:,:,1]<120)&(rgb[:,:,2]>180)
                if 965<=h<=985 and blue[int(h*.58):int(h*.7)].sum()==0 and np.any(magenta.sum(0)>h*.4):
                    with conn:conn.execute('INSERT OR REPLACE INTO legend_chart_scans VALUES(?,?,?,?,?)',(row['id'],VERSION,'complete',now(),dumps({'no_active_axis_clock_panel':True})))
                    continue
                raise
            templates=conn.execute('''SELECT i.*,d.category FROM legend_instances i JOIN legend_definitions d ON d.key=i.definition_key
              JOIN pdf_pages p ON p.id=i.page_id WHERE p.artifact_id=? AND json_extract(d.rule_json,'$.adapter')='color_symbol' ''',(row['artifact_id'],)).fetchall()
            if not templates:raise ValueError('Faltan plantillas completas del documento')
            hits=find_symbols(rgb,templates,axis)
            with conn:
                for n,hit in enumerate(hits):
                    add_hit(conn,row['id'],f'symbol:{n}',hit['key'],hit['instance_id'],hit['box'],rgb,axis,hit['score'],
                            hit['alternatives']+[{'color_error':hit['color_error'],'requires_annotation_or_CSV_for_quantity':True}])
                fragments=basal_fragments(conn,row['id'],rgb,axis)
                conn.execute('INSERT OR REPLACE INTO legend_chart_scans VALUES(?,?,?,?,?)',(row['id'],VERSION,'complete',now(),dumps({'symbol_candidates':len(hits),'basal_candidates':len(fragments),
                  'meaning':'candidate_scan_complete; not all semantic adapters are complete'})))
            summary['charts']+=1;summary['new_candidates']+=len(hits)+len(fragments)
            print(f"Leyenda: gráfico {row['id']} ({summary['charts']}/{len(rows)})",flush=True)
        except Exception as exc:
            with conn:conn.execute('INSERT OR REPLACE INTO legend_chart_scans VALUES(?,?,?,?,?)',(row['id'],VERSION,'error',now(),dumps({'error':str(exc)})))
            summary['errors'].append({'image_id':row['id'],'error':str(exc)})
    if not summary['errors']:
        from .quantitative import process
        summary['quantitative']=process(conn)
        summary['errors']+=summary['quantitative']['errors']
    with conn:
        crosswalk(conn)
        reject_false_temporary_candidates(conn)
    return summary


def atlas(conn,path):
    """Generic legend-only atlas; never includes patient header or clinical measurements."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    try:
        font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20)
        small=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',14)
        title=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',25)
    except OSError:font=small=title=ImageFont.load_default()
    families=['Glucemia','MCG','Bolo','Basal','Evento','Tendencia']
    out=Image.new('RGB',(1740,1820),'white');draw=ImageDraw.Draw(out)
    draw.text((25,10),'Tandem Source - leyenda desglosada: 33 elementos + 3 de tendencia',font=title,fill='#12364b')
    for i,family in enumerate(families):
        x=20+(i%3)*575;y=65+(i//3)*875
        draw.rounded_rectangle((x,y,x+555,y+855),radius=10,outline='#ccd8df',width=2)
        draw.text((x+15,y+12),family,font=title,fill='#12364b')
        for n,d in enumerate([d for d in DEFINITIONS if d[2]==family]):
            r=conn.execute('SELECT symbol_png FROM legend_instances WHERE definition_key=? ORDER BY page_id DESC LIMIT 1',(d[0],)).fetchone()
            yy=y+58+n*70
            if r:
                im=Image.open(io.BytesIO(r[0])).convert('RGB');im.thumbnail((65,65));out.paste(im,(x+10,yy))
            for j,line in enumerate(textwrap.wrap(d[1],36)):
                draw.text((x+85,yy+j*23),line,font=font,fill='#1d2630')
            draw.text((x+85,yy+49),d[0],font=small,fill='#5b6d7c')
        notes={'Glucemia':'Color: rango. Gota central: captura automática. Son atributos que pueden coexistir.',
          'Bolo':'Tipo y método de suministro son dimensiones distintas; no duplicar el mismo bolo.',
          'Basal':'U/h es una tasa. No confundirla con las U de una fila CSV ni con desconexión física.',
          'Evento':'La banda es duración, no otro evento. Pérdida MCG no equivale a desconexión de la bomba.'}
        if family in notes:
            for j,line in enumerate(textwrap.wrap(notes[family],65)):
                draw.text((x+15,y+800+j*18),line,font=small,fill='#5b6d7c')
    out.save(path)
    return str(path)
