"""PDF layout and graphical observations. Times digitized from axes are estimates.

No physical-disconnection inference. Every classified/unknown shape keeps pixels.
Native table rows retain their cells even where semantic normalization is ambiguous.
"""
from __future__ import annotations
import io,json,re,unicodedata
from datetime import datetime,timedelta
import cv2
import numpy as np
from PIL import Image
import pymupdf
from .db import digest,dumps,now

VERSION='2.0'
TYPES={
 'sleep':'Sueño', 'exercise':'Ejercicio', 'cartridge_or_site_change':'Cambio de cartucho o sitio',
 'cgm_alert_icon':'Alerta de MCG', 'pump_alarm_icon':'Alarma de la bomba',
 'manual_stop':'Detener de forma manual', 'power_off':'Apagado'}


def png(array):
    out=io.BytesIO();Image.fromarray(array).save(out,format='PNG');return out.getvalue()


def slug(text):
    return re.sub('[^a-z0-9]+','_',unicodedata.normalize('NFKD',text).encode('ascii','ignore').decode().lower()).strip('_')


def groups(indices,gap=1):
    out=[]
    for i in indices:
        i=int(i)
        if out and i-out[-1][-1]<=gap:out[-1].append(i)
        else:out.append([i])
    return [(g[0],g[-1]+1) for g in out]


def text_words(words):
    # Baseline rather than upper edge keeps differently sized numeric values in their row.
    return ' '.join(w[4] for w in sorted(words,key=lambda w:(round(w[3]/4)*4,w[0])))


def native_fields(conn,page_id,image_id,page,box,scope,asof):
    words=page.get_text('words',clip=box)
    horizontal={}
    for drawing in page.get_drawings():
        r=drawing['rect']
        if r.height<1.5 and r.width>5 and box.contains(r):
            horizontal.setdefault(round(r.y0,1),[]).append((r.x0,r.x1))
    boundaries=[(y,xs) for y,xs in sorted(horizontal.items()) if sum(b-a for a,b in xs)>box.width*.62]
    # Background cards have a title separator. Reject arbitrary chart geometry.
    if not boundaries:return 0
    title=text_words([w for w in words if (w[1]+w[3])/2<boundaries[0][0]])
    if not title:return 0
    if 'Comparación de Tiempo en rango' in title:
        # Percentages are native text over two graphical bars. Keep current/previous separately.
        columns={'current':[],'previous':[]}
        for word in words:
            if word[4]!='%':continue
            values=[w for w in words if re.fullmatch(r'\d+(?:[,.]\d+)?',w[4])
                    and 0<=word[0]-w[2]<12 and abs((word[1]+word[3]-w[1]-w[3])/2)<6]
            if not values:continue
            value=min(values,key=lambda w:word[0]-w[2])
            center=(value[0]+word[2])/2
            which='current' if center<box.x0+box.width*.45 else 'previous' if center>box.x0+box.width*.55 else None
            if which:columns[which].append(value)
        bands=['above_250','181_to_250','70_to_180','54_to_69','below_54']
        for which,values in columns.items():
            if len(values)!=5:continue
            for key,value in zip(bands,sorted(values,key=lambda w:w[1])):
                conn.execute('''INSERT OR IGNORE INTO report_metrics(page_id,image_id,metric_key,value,unit,qualifier,evidence_text,bbox_json)
                  VALUES(?,?,?,?,?,?,?,?)''',(page_id,image_id,'time_in_range_'+key,float(value[4].replace(',','.')),'percent',which,value[4]+' %',dumps(list(value[:4]))))
    previous=boundaries[0][0]
    count=0
    for index,(bottom,segments) in enumerate(boundaries[1:]+[(box.y1,[(box.x0,box.x1)])]):
        selected=[w for w in words if previous<=(w[1]+w[3])/2<bottom]
        if selected:
            evidence=text_words(selected)
            segments=sorted(segments)
            # Divider segments expose table cells, preserving multiple values and units.
            cells=[text_words([w for w in selected if left<=(w[0]+w[2])/2<right]) for left,right in segments]
            if not any(cells):cells=[evidence]
            label=cells[0] if len(cells)>1 else evidence
            value=' | '.join(cells[1:]) if len(cells)>1 else evidence
            values={'cells':cells,'numbers':[float(v.replace(',','.')) for v in re.findall(r'(?<![\w:])\d+(?:[,.]\d+)?(?![\w:])',value)],
                    'words':[list(w[:5]) for w in selected], 'normalization':'source_cells_not_inferred_units'}
            conn.execute('''INSERT OR IGNORE INTO report_fields
              (page_id,image_id,section,field_key,row_index,label,value_text,values_json,evidence_text,bbox_json,
               scope,as_of_date,extraction_method,review_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
              (page_id,image_id,title,slug(label),index,label,value,dumps(values),evidence,
               dumps([box.x0,previous,box.x1,bottom]),scope,asof,'pdf_native_layout','source_text'))
            field=conn.execute('SELECT id FROM report_fields WHERE page_id=? AND image_id=? AND row_index=?',(page_id,image_id,index)).fetchone()[0]
            schedule=re.search(r'([LMaMiJVSD\s]+)\s*\((\d{1,2}:\d{2})\s*-\s*(\d{1,2}:\d{2})\)\s*(Activado|Desactivado)',evidence)
            if schedule:
                days,start,end,enabled=schedule.groups()
                mapping={'L':1,'Ma':2,'Mi':3,'J':4,'V':5,'S':6,'D':7}
                weekdays=[mapping[x] for x in days.split() if x in mapping]
                conn.execute('''INSERT OR IGNORE INTO sleep_schedules(field_id,as_of_date,weekdays_json,start_time,end_time,enabled)
                  VALUES(?,?,?,?,?,?)''',(field,asof,dumps(weekdays),start.zfill(5),end.zfill(5),int(enabled=='Activado')))
            count+=1
        previous=bottom
    return count


def dark_mask(rgb):
    return ((rgb.max(2)-rgb.min(2)<8)&(rgb.mean(2)<180)).astype('uint8')


def legend(conn,page_id,page):
    text=page.get_text()
    if not all(x in text for x in ['Detener de','Sueño','Ejercicio','Apagado']):return
    words=page.get_text('words')
    drawings=page.get_drawings()
    rendered=None
    for kind,label in TYPES.items():
        first=label.split()[0]
        anchors=[w for w in words if w[4]==first and w[0]>440 and 40<w[1]<300]
        if not anchors:continue
        anchor=anchors[0]
        candidates=[]
        for d in drawings:
            r=d['rect'];fill=d.get('fill')
            if not fill or len(fill)!=3 or max(fill)-min(fill)>.02:continue
            if not .7<fill[0]<.85 or not 8<r.width<15 or not 7<r.height<15:continue
            if anchor[0]-20<r.x0<anchor[0] and abs((r.y0+r.y1)/2-(anchor[1]+anchor[3])/2)<7:candidates.append(r)
        if not candidates:continue
        rect=min(candidates,key=lambda r:abs((r.y0+r.y1)/2-(anchor[1]+anchor[3])/2))
        if rendered is None:
            pix=page.get_pixmap(dpi=300,alpha=False)
            rendered=np.frombuffer(pix.samples,dtype=np.uint8).reshape(pix.height,pix.width,3)
        x0,y0,x1,y1=[round(v*300/72) for v in rect]
        crop=rendered[y0-2:y1+3,x0-2:x1+3]
        conn.execute('''INSERT OR IGNORE INTO legend_templates(page_id,event_type,source_label,bbox_json,image_png,mask_png)
          VALUES(?,?,?,?,?,?)''',(page_id,kind,label,dumps(list(rect)),png(crop),png(dark_mask(crop)*255)))


def axes(rgb):
    h,w=rgb.shape[:2]
    blue=((rgb[:,:,0]<20)&(rgb[:,:,1]>100)&(rgb[:,:,1]<140)&(rgb[:,:,2]>150)&(rgb[:,:,2]<200))
    counts=blue.sum(1)
    window=counts[int(h*.58):int(h*.7)]
    peak=int(window.max())
    candidates=[g for g in groups(np.where(counts>=peak*.9)[0]) if h*.58<g[0]<h*.7]
    # Two nearby antialias runs can be separated by a single light row.
    if len(candidates)>1 and candidates[-1][1]-candidates[0][0]<12:
        candidates=[(candidates[0][0],candidates[-1][1])]
    if len(candidates)!=1:raise ValueError('Eje de eventos no identificable de forma única')
    bolus_bottom=candidates[0][0]
    if peak<15:raise ValueError('No se encuentra tramo activo del eje horario')
    # Clock-change panels fade the unused part. The 24-hour grid still spans the whole width.
    left,right=round(w*56/2432),round(w*2295/2432)
    neutral=(rgb.max(2)-rgb.min(2)<3)&(rgb[:,:,0]>110)&(rgb[:,:,0]<170)
    lines=groups(np.where(neutral[:,left:right].sum(1)>(right-left)*.8)[0])
    after=[g for g in lines if bolus_bottom+30<g[0]<h*.9]
    if not after:
        # In clock-split panels only the active part of the divider is dark.
        active=np.where(blue[bolus_bottom])[0]
        sub=neutral[:,int(active[0]):int(active[-1])+1]
        lines=groups(np.where(sub.sum(1)>sub.shape[1]*.8)[0])
        after=[g for g in lines if bolus_bottom+30<g[0]<h*.9]
    if not after:raise ValueError('No se localiza el límite de evento/basal')
    event_bottom=after[0][0]
    # Validate the known layout proportion; don't assign times to a changed template.
    if not h*.06<event_bottom-bolus_bottom<h*.16:raise ValueError('Altura del carril de eventos inesperada')
    return left,right,bolus_bottom,event_bottom


def icon_matches(rgb,templates,axis):
    left,right,top,bottom=axis
    roi=dark_mask(rgb[top+2:bottom+8,left:right+1])
    roi[roi.mean(1)>.7]=0
    matches=[]
    for t in templates:
        mask=np.array(Image.open(io.BytesIO(t['mask_png'])).convert('L'))//255
        # Embedded reports render icons at 300 pixels per PDF inch.
        if roi.shape[0]<mask.shape[0]:continue
        score=cv2.matchTemplate(roi,mask,cv2.TM_CCOEFF_NORMED)
        for _ in range(60):
            _,best,_,loc=cv2.minMaxLoc(score)
            if best<.46:break
            x,y=loc;w,h=mask.shape[1],mask.shape[0]
            matches.append({'type':t['event_type'],'template_id':t['id'],'score':float(best),
              'box':[left+x,top+2+y,left+x+w,top+2+y+h]})
            cv2.rectangle(score,(x-25,y-16),(x+25,y+16),-1,-1)
    # A circle can weakly resemble a different symbol. Retain the best candidate at each location.
    chosen=[]
    for hit in sorted(matches,key=lambda x:-x['score']):
        center=(hit['box'][0]+hit['box'][2])/2
        if any(abs(center-(k['box'][0]+k['box'][2])/2)<20 for k in chosen):continue
        chosen.append(hit)
    return sorted(chosen,key=lambda x:x['box'][0])


def minute(x,axis):return max(0,min(1440,(x-axis[0])*1440/(axis[1]-axis[0])))


def stamp(day,minutes):
    if day is None:return None
    return (datetime.fromisoformat(day)+timedelta(minutes=round(minutes))).isoformat(timespec='minutes')


def chart_words(conn,page_id,image_id,box,rgb,day,axis):
    row=conn.execute('SELECT ocr_json FROM pdf_pages WHERE id=?',(page_id,)).fetchone()
    if not row or not row[0]:raise ValueError('Falta OCR de la página; ejecutar ocr antes de extract-pdf')
    ocr=json.loads(row[0]);scale=ocr['dpi']/72
    width,height=rgb.shape[1],rgb.shape[0]
    index=0
    for line in ocr['result']['lines']:
        for word in line.get('words',[]):
            r=word['bounding_rect'];x=(r['x']+r['width']/2)/scale;y=(r['y']+r['height']/2)/scale
            if not box.contains(pymupdf.Point(x,y)):continue
            x0=(r['x']/scale-box.x0)/box.width*width;y0=(r['y']/scale-box.y0)/box.height*height
            x1=x0+r['width']/scale/box.width*width;y1=y0+r['height']/scale/box.height*height
            center_y=(y0+y1)/2;center_x=(x0+x1)/2
            role='graph_text'
            numeric=bool(re.fullmatch(r'[\d]+(?:[,.]\d+)?',word['text']))
            if center_y<85:role='daily_header'
            elif center_x<axis[0]-5 or center_x>axis[1]+5 or center_y>height-50:role='axis_label'
            elif numeric:
                if axis[2]<center_y<axis[2]+60:role='carbohydrate_annotation'
                elif axis[2]-100<center_y<axis[2]:role='bolus_annotation'
                elif center_y>axis[3]:role='basal_annotation'
                else:role='glucose_annotation'
            conn.execute('''INSERT OR IGNORE INTO chart_labels
              (image_id,word_index,label_type,text,bbox_json,local_date,minute_lower,minute_upper) VALUES(?,?,?,?,?,?,?,?)''',
              (image_id,index,role,word['text'],dumps([x0,y0,x1,y1]),day,minute(x0-35,axis),minute(x1+35,axis)))
            index+=1
    return index


def native_events(conn,page_id,page):
    charts=conn.execute("SELECT id,bbox_json,local_date FROM report_images WHERE page_id=? AND image_kind='daily_chart'",(page_id,)).fetchall()
    count=0
    expected=set()
    for block in page.get_text('dict')['blocks']:
        if block['type']!=0:continue
        text=' '.join(' '.join(span['text'] for span in line['spans']) for line in block['lines'])
        clock_notice=re.search(r'cambio de hora de la bomba de\s+(\d{1,2})\s+([a-z]+)\s+a\s+(\d{1,2}:\d{2})',text,re.I)
        if clock_notice:
            from .pdf import date_spanish
            r=conn.execute('SELECT a.period_start,a.period_end FROM pdf_pages p JOIN artifacts a ON a.id=p.artifact_id WHERE p.id=?',(page_id,)).fetchone()
            dates=[]
            if r['period_start'] and r['period_end']:
                for year in range(int(r['period_start'][:4]),int(r['period_end'][:4])+1):
                    try:date_value=date_spanish(clock_notice[1],clock_notice[2],str(year))
                    except (ValueError,KeyError):continue
                    if r['period_start']<=date_value<=r['period_end']:dates.append(date_value)
            day=dates[0] if len(dates)==1 else None
            conn.execute('''INSERT OR IGNORE INTO report_text_events
              (page_id,event_type,local_date,time_local,description,evidence_text,bbox_json,extraction_method,review_status)
              VALUES(?,?,?,?,?,?,?,?,?)''',(page_id,'clock_change_notice',day,day+'T'+clock_notice[3].zfill(5)+':00' if day else None,
              text,text,dumps(list(block['bbox'])),'pdf_native_clock_notice_year_from_requested_period','source_text' if day else 'date_unreviewed'))
            expected.add(('clock_change_notice',text,dumps(list(block['bbox']))))
        if not re.search(r'(Alertas? de MCG|Alarmas? de la bomba)\s*:',text):continue
        box=list(block['bbox'])
        eligible=[r for r in charts if json.loads(r['bbox_json'])[3]<=box[1]+5]
        preceding=max(eligible,key=lambda r:json.loads(r['bbox_json'])[3]) if eligible else None
        day=preceding['local_date'] if preceding else None
        headings=list(re.finditer(r'(Alertas? de MCG|Alarmas? de la bomba)\s*:',text))
        for index,heading in enumerate(headings):
            section=text[heading.end():headings[index+1].start() if index+1<len(headings) else len(text)]
            kind='cgm_alert' if 'MCG' in heading[1] else 'pump_alarm'
            for match in re.finditer(r'(\d{1,2}:\d{2})\s*-\s*(.*?)(?=(?:\d{1,2}:\d{2})\s*-|$)',section):
                clock,description=match.groups()
                try:datetime.strptime(clock,'%H:%M')
                except ValueError:continue
                evidence=match.group(0).strip()
                expected.add((kind,evidence,dumps(box)))
                conn.execute('''INSERT OR IGNORE INTO report_text_events
                  (page_id,image_id,event_type,local_date,time_local,description,evidence_text,bbox_json,extraction_method)
                  VALUES(?,?,?,?,?,?,?,?,?)''',(page_id,preceding['id'] if preceding else None,kind,day,
                  day+'T'+clock.zfill(5)+':00' if day else None,description.strip(),evidence,dumps(box),'pdf_native_text_with_ocr_panel_date'))
                count+=1
    # Remove obsolete, unreviewed parser candidates; preserve every original and reviewed decision.
    for old in conn.execute('SELECT id,event_type,evidence_text,bbox_json,review_status FROM report_text_events WHERE page_id=?',(page_id,)).fetchall():
        if (old['event_type'],old['evidence_text'],old['bbox_json']) not in expected and not old['review_status'].startswith('reviewed_'):
            conn.execute('DELETE FROM report_text_events WHERE id=?',(old['id'],))
    return count


def chart(conn,image_id,rgb,day,templates):
    active_blue=(rgb[:,:,0]<20)&(rgb[:,:,1]>100)&(rgb[:,:,1]<140)&(rgb[:,:,2]>150)&(rgb[:,:,2]<200)
    if active_blue[int(rgb.shape[0]*.58):int(rgb.shape[0]*.7)].sum()==0:
        magenta=(rgb[:,:,0]>180)&(rgb[:,:,1]<120)&(rgb[:,:,2]>180)
        if np.any(magenta.sum(0)>rgb.shape[0]*.4) and 965<=rgb.shape[0]<=985:
            # A fully faded, empty clock-change panel has no active treatment trace to digitize.
            h,w=rgb.shape[:2]
            return {'axis':[round(w*56/2432),round(w*2295/2432),round(h*.65),round(h*.758)],
                    'empty_clock_change_panel':True,'date':day,'icons':0,'bands':0,'unknown_icon_regions':0}
    axis=axes(rgb);left,right,top,bottom=axis
    hits=icon_matches(rgb,templates,axis)
    details={'axis_pixels':axis,'axis_minutes':[0,1440], 'time_accuracy':'estimated_from_pdf_plot',
             'physical_disconnection':'not_inferred','icon_layout_may_shift_to_avoid_overlap':True}
    def observe(key,kind,box,start=None,end=None,error=None,score=None,template=None,extra=None):
        x0,y0,x1,y1=[int(v) for v in box]
        conn.execute('''INSERT OR IGNORE INTO chart_observations
          (image_id,observation_key,observation_type,local_date,bbox_json,minute_start,minute_end,uncertainty_minutes,
           match_score,template_id,evidence_png,details_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
          (image_id,key,kind,day,dumps(box),start,end,error,score,template,png(rgb[max(0,y0-3):y1+4,max(0,x0-3):x1+4]),dumps({**details,**(extra or {})})))
        return conn.execute('SELECT id FROM chart_observations WHERE image_id=? AND observation_key=?',(image_id,key)).fetchone()[0]
    for n,hit in enumerate(hits):
        # Icon glyphs can be displaced by report collision layout. Preserve a bounded position, not an exact event time.
        a,b=minute(hit['box'][0]-30,axis),minute(hit['box'][2]+30,axis)
        observe(f'icon:{n}',hit['type'],hit['box'],a,b,max(20,(b-a)/2),hit['score'],hit['template_id'],{'meaning':'symbol_time_window_not_duration'})
    # Duration bands are light-gray rectangles in the event lane, confirmed against the legend.
    band_rgb=rgb[max(top+1,bottom-29):bottom-3,left:right+1]
    exact=(band_rgb.max(2)-band_rgb.min(2)<3)&(((band_rgb[:,:,0]>=224)&(band_rgb[:,:,0]<=228))|((band_rgb[:,:,0]>=207)&(band_rgb[:,:,0]<=211)))
    cols=(exact.sum(0)>=6).astype('uint8').reshape(1,-1)
    closed=cv2.morphologyEx(cols,cv2.MORPH_CLOSE,np.ones((1,12),np.uint8)).ravel()
    bands=[(a+left,b+left) for a,b in groups(np.where(closed)[0]) if b-a>=10]
    for n,(a,b) in enumerate(bands):
        near=[h for h in hits if h['type'] in ('sleep','exercise','manual_stop','power_off') and a-65<=h['box'][0]<=a+40]
        modes=[h for h in near if h['type'] in ('sleep','exercise')]
        hit=max(modes,key=lambda h:h['score']) if modes else min(near,key=lambda h:abs(h['box'][0]-a)) if near else None
        # An icon can obscure the first pixels of its own band. Never extend by an unbounded assumption.
        if hit:a=max(left,min(a,hit['box'][0]))
        start,end=minute(a,axis),minute(b,axis)
        kind=hit['type'] if hit else 'unclassified_event_duration'
        error=max(2,60*1440/(right-left)) if hit and a>left+3 else 2
        within=[h for h in hits if h['type'] in ('sleep','exercise') and a-65<=h['box'][0]<b-4]
        if len(within)>1 and len({h['type'] for h in within})>1:
            # Gray bands can overlap/merge. Keep the band as ambiguous evidence instead of fabricating a transition.
            kind='ambiguous_multi_mode_duration'
        oid=observe(f'band:{n}',kind,[a,top+1,b,bottom],start,end,error,
                    hit['score'] if hit else None,hit['template_id'] if hit else None,
                    {'meaning':'duration_band','boundary_error_minutes':error,'uncertain_classification':hit is None or kind=='ambiguous_multi_mode_duration',
                     'mode_symbols_in_band':[{'type':h['type'],'x':h['box'][0]} for h in within]})
        if day:
            conn.execute('''INSERT OR IGNORE INTO state_intervals
              (observation_id,state,local_date,start_local,end_local,start_minute,end_minute,uncertainty_minutes,
               left_censored,right_censored,time_basis) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
              (oid,kind,day,stamp(day,start),stamp(day,end),start,end,error,int(a<=left+3),int(b>=right-3),'pdf_axis_digitized'))
    # Keep every gray icon region even when matching is ambiguous or symbols overlap.
    region=rgb[top+2:bottom-3,left:right+1]
    gray=(region.max(2)-region.min(2)<3)&(region[:,:,0]>=190)&(region[:,:,0]<=211)
    n,labels,stats,centroids=cv2.connectedComponentsWithStats(gray.astype('uint8'))
    unknown=0
    for x,y,w,h,area in stats[1:]:
        if area<55 or w<7 or h<12:continue
        box=[int(left+x),int(top+2+y),int(left+x+w),int(top+2+y+h)]
        overlapping=[v for v in hits if min(v['box'][2],box[2])>max(v['box'][0],box[0])]
        kind='icon_region' if overlapping else 'unclassified_icon_region'
        if not overlapping:unknown+=1
        observe('region:'+':'.join(map(str,box)),kind,box,minute(box[0],axis),minute(box[2],axis),20,
                extra={'meaning':'all_gray_components_preserved','candidate_types':[x['type'] for x in overlapping]})
    # Red hatched regions in the basal lane denote automatic suspension; the event legend is retained separately.
    lower=rgb[bottom+3:rgb.shape[0]-45,left:right+1]
    red=(lower[:,:,0]>220)&(lower[:,:,1]>100)&(lower[:,:,1]<220)&(lower[:,:,2]>100)&(lower[:,:,2]<220)&(abs(lower[:,:,1].astype(int)-lower[:,:,2].astype(int))<25)
    marked=(red.sum(0)>=8).astype('uint8').reshape(1,-1)
    marked=cv2.morphologyEx(marked,cv2.MORPH_CLOSE,np.ones((1,5),np.uint8)).ravel()
    for n,(a,b) in enumerate(groups(np.where(marked)[0])):
        if b-a<3:continue
        a+=left;b+=left;start,end=minute(a,axis),minute(b,axis)
        oid=observe(f'auto_suspend:{n}','automatic_suspension',[a,bottom+3,b,rgb.shape[0]-45],start,end,2,
                    extra={'meaning':'red_hatching_in_basal_lane','classification_requires_visual_review':True})
        if day:conn.execute('''INSERT OR IGNORE INTO state_intervals
          (observation_id,state,local_date,start_local,end_local,start_minute,end_minute,uncertainty_minutes,left_censored,right_censored,time_basis)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(oid,'automatic_suspension',day,stamp(day,start),stamp(day,end),start,end,2,int(a<=left+3),int(b>=right-3),'pdf_axis_digitized'))
    # Magenta vertical lines are the report's clock-change boundaries, not treatment state changes.
    magenta=(rgb[:,:,0]>180)&(rgb[:,:,1]<120)&(rgb[:,:,2]>180)
    for n,(a,b) in enumerate(groups(np.where(magenta.sum(0)>rgb.shape[0]*.4)[0])):
        observe(f'clock:{n}','clock_change_marker',[a,45,b,rgb.shape[0]-45],minute((a+b)/2,axis),None,2,
                extra={'meaning':'clock_change_boundary; do_not_join_panels_across_clock_change'})
    # Preserve patterned connection-loss candidates only when several parallel stripes remain outside icons.
    pattern=dark_mask(rgb[top+3:bottom,left:right+1])*255
    for hit in hits:
        x0,y0,x1,y1=hit['box'];pattern[max(0,y0-top-6):y1-top+4,max(0,x0-left-5):x1-left+5]=0
    pattern[-5:]=0
    lines=cv2.HoughLinesP(pattern,1,np.pi/180,threshold=12,minLineLength=15,maxLineGap=2)
    diagonal=[]
    if lines is not None:
        for x0,y0,x1,y1 in lines[:,0]:
            if 0.6<abs((y1-y0)/(x1-x0 or 1))<1.5:diagonal.append((int(x0),int(y0),int(x1),int(y1)))
    if len(diagonal)>=6:
        xs=np.zeros(right-left+1,dtype='uint8')
        for x0,y0,x1,y1 in diagonal:xs[min(x0,x1):max(x0,x1)+1]=1
        for n,(a,b) in enumerate(groups(np.where(xs)[0],gap=15)):
            selected=[l for l in diagonal if a<=min(l[0],l[2])<=b]
            if len(selected)<6:continue
            observe(f'connection_pattern:{n}','cgm_connection_lost_pattern',[a+left,top+3,b+left,bottom],minute(a+left,axis),minute(b+left,axis),3,
                    extra={'meaning':'parallel_diagonal_pattern_candidate','pattern_segments':selected,'not_physical_pump_disconnection':True})
    # Basal/glucose curves and event data are preserved as complete raster series source; no false precision is invented.
    colors={'basal_blue':((rgb[:,:,2]>170)&(rgb[:,:,0]<130)&(rgb[:,:,1]>130)),
            'glucose_green':((rgb[:,:,1]>rgb[:,:,0].astype(int)+20)&(rgb[:,:,1]>rgb[:,:,2].astype(int)+20)),
            'glucose_orange':((rgb[:,:,0]>180)&(rgb[:,:,1]>60)&(rgb[:,:,1]<190)&(rgb[:,:,2]<100))}
    for name,mask in colors.items():
        start_y,end_y=(bottom+3,rgb.shape[0]-45) if name=='basal_blue' else (50,top-80)
        points=[]
        for x in range(left,right+1):
            ys=np.where(mask[start_y:end_y,x])[0]
            if len(ys):points.append([x,int(start_y+ys.min()),int(start_y+ys.max())])
        conn.execute('''INSERT OR IGNORE INTO visual_series(image_id,series_name,coordinate_system,points_json,interpretation_json)
          VALUES(?,?,?,?,?)''',(image_id,name,'embedded_image_pixels',dumps(points),dumps({'axis':axis,'values':'pixel_envelopes_not_clinical_samples','preferred_exact_values':'CSV','image_png':'report_images'})))
    return {'axis':axis,'icons':len(hits),'bands':len(bands),'unknown_icon_regions':unknown,'date':day}


def summary_series(conn,image_id,rgb):
    h,w=rgb.shape[:2]
    if not (600<h<700 and 2400<w<2500):return {'status':'layout_unrecognized','shape':[h,w]}
    gray=rgb[:,:,0]
    neutral=(rgb.max(2)-rgb.min(2)<3)
    grid=neutral&(gray==223)
    rows=[a for a,b in groups(np.where(grid.sum(1)>w*.75)[0]) if h*.2<a<h*.35]
    baseline=neutral&(gray==138)
    base=[a for a,b in groups(np.where(baseline.sum(1)>w*.75)[0]) if h*.75<a<h*.9]
    if not rows or not base:return {'status':'axis_not_calibrated'}
    top,bottom=min(rows),max(base)
    xs=np.where(grid[top])[0];left,right=int(xs[0]),int(xs[-1])
    points={name:[] for name in ['p10','p25','p50','p75','p90']}
    masks={'p50':neutral&(gray>=55)&(gray<=65),'iqr':neutral&(gray==213),'outer':neutral&(gray>=135)&(gray<=141)}
    def value(y):return max(0,min(400,(bottom-y)*400/(bottom-top)))
    for x in range(left,right+1,5):
        median=np.where(masks['p50'][top+3:bottom-5,x])[0]+top+3
        if not len(median):continue
        y=float(np.median(median));t=(x-left)*1440/(right-left)
        points['p50'].append([t,value(y)])
        band=np.where(masks['iqr'][top+3:bottom-5,x])[0]+top+3
        outer=np.where(masks['outer'][top+3:bottom-5,x])[0]+top+3
        if len(band):
            points['p75'].append([t,value(band.min())]);points['p25'].append([t,value(band.max())])
        upper=outer[outer<y-4];lower=outer[outer>y+4]
        if len(upper):points['p90'].append([t,value(upper.min())])
        if len(lower):points['p10'].append([t,value(lower.max())])
    for name,data in points.items():
        conn.execute('''INSERT OR IGNORE INTO visual_series(image_id,series_name,coordinate_system,points_json,interpretation_json)
          VALUES(?,?,?,?,?)''',(image_id,name,'minutes_mg_dl_digitized',dumps(data),dumps({'axis':[left,right,top,bottom],
           'glucose_scale':[400,0],'uncertainty_mg_dl':max(3,3*400/(bottom-top)),
           'meaning':'report_aggregate_percentiles; estimated_from_image_not_raw_measurements'})))
    return {'status':'digitized_unreviewed','points':{k:len(v) for k,v in points.items()}}


def jsonable(value):
    if value is None or isinstance(value,(str,float,int,bool)):return value
    if isinstance(value,dict):return {k:jsonable(v) for k,v in value.items()}
    return [jsonable(v) for v in value]


def enrich_assets(conn):
    """Complete cross-page classifications without rebuilding already indexed evidence."""
    ids=[r[0] for r in conn.execute("SELECT id FROM report_images WHERE image_kind='daily_chart'").fetchall()]
    for iid in ids:
        row=conn.execute('SELECT * FROM report_images WHERE id=?',(iid,)).fetchone()
        rgb=np.array(Image.open(io.BytesIO(row['image_png'])).convert('RGB'))
        try:axis=axes(rgb)
        except ValueError:continue
        left,right,top,bottom=axis
        # Repeated gray diagonal stripes occupy the low event lane. Unlike a missing glucose trace,
        # this is an explicit symbol in the report legend for lost CGM connection.
        roi=rgb[bottom-25:bottom-4,left:right+1]
        stripes=(roi.max(2)-roi.min(2)<3)&(roi[:,:,0]>=130)&(roi[:,:,0]<=145)
        cols=(stripes.sum(0)>=3).astype('uint8').reshape(1,-1)
        closed=cv2.morphologyEx(cols,cv2.MORPH_CLOSE,np.ones((1,9),np.uint8)).ravel()
        for n,(a,b) in enumerate(groups(np.where(closed)[0])):
            if b-a<12 or stripes[:,a:b].sum()<70:continue
            a+=left;b+=left
            start,end=minute(a,axis),minute(b,axis)
            with conn:
                conn.execute('''INSERT OR IGNORE INTO chart_observations
                  (image_id,observation_key,observation_type,local_date,bbox_json,minute_start,minute_end,uncertainty_minutes,evidence_png,details_json)
                  VALUES(?,?,?,?,?,?,?,?,?,?)''',(iid,f'cgm_stripes:{n}','cgm_connection_lost',row['local_date'],dumps([a,bottom-25,b,bottom-4]),start,end,3,
                  png(rgb[bottom-30:bottom+4,max(0,a-4):b+4]),dumps({'meaning':'gray_hatched_CGM_connection_lost_legend_pattern',
                  'not_physical_pump_disconnection':True,'time_basis':'pdf_axis_digitized','axis':axis})))
                oid=conn.execute('SELECT id FROM chart_observations WHERE image_id=? AND observation_key=?',(iid,f'cgm_stripes:{n}')).fetchone()[0]
                if row['local_date']:
                    conn.execute('''INSERT OR IGNORE INTO state_intervals
                      (observation_id,state,local_date,start_local,end_local,start_minute,end_minute,uncertainty_minutes,left_censored,right_censored,time_basis)
                      VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(oid,'cgm_connection_lost',row['local_date'],stamp(row['local_date'],start),stamp(row['local_date'],end),start,end,3,int(a<=left+3),int(b>=right-3),'pdf_axis_digitized'))
    # Wide pieces of profile-table backgrounds are not glucose-summary charts.
    with conn:
        conn.execute("""UPDATE report_images SET image_kind='profile_table' WHERE image_kind='summary_chart'
          AND page_id IN (SELECT id FROM pdf_pages WHERE native_text LIKE 'Configuración de la bomba%')""")


def verify_layout(conn):
    """Independently enumerate source primitives. Store masks/vectors, prove no block was omitted."""
    errors=[]
    artifact_ids=[r[0] for r in conn.execute("SELECT id FROM artifacts WHERE mime_type='application/pdf' AND status='imported'").fetchall()]
    for aid in artifact_ids:
        content=conn.execute('SELECT content FROM artifacts WHERE id=?',(aid,)).fetchone()[0]
        with pymupdf.open(stream=content,filetype='pdf') as doc:
            for page in doc:
                pid=conn.execute('SELECT id FROM pdf_pages WHERE artifact_id=? AND page_number=?',(aid,page.number+1)).fetchone()[0]
                source=page.get_text('dict')['blocks'];images=[b for b in source if b['type']==1];texts=[b for b in source if b['type']==0]
                drawings=page.get_drawings()
                with conn:
                    native_events(conn,pid,page)
                    for n,b in enumerate(images):
                        iid=conn.execute('SELECT id FROM report_images WHERE page_id=? AND block_number=?',(pid,n)).fetchone()
                        if iid and b.get('mask'):
                            conn.execute('INSERT OR IGNORE INTO report_image_masks VALUES(?,?,?)',(iid[0],b['mask'],digest(b['mask'])))
                    for n,d in enumerate(drawings):
                        conn.execute('INSERT OR IGNORE INTO native_drawings VALUES(?,?,?)',(pid,n,dumps(jsonable(d))))
                    actual=[conn.execute('SELECT count(*) FROM '+table+' WHERE page_id=?',(pid,)).fetchone()[0] for table in ('report_images','native_text_blocks','native_drawings')]
                    expected=[len(images),len(texts),len(drawings)]
                    valid=actual==expected
                    conn.execute('INSERT OR REPLACE INTO pdf_layout_verifications VALUES(?,?,?,?,?,?,?,?,?)',
                      (pid,now(),expected[0],actual[0],expected[1],actual[1],expected[2],actual[2],'complete' if valid else 'error'))
                    if not valid:errors.append({'page_id':pid,'source_blocks':expected,'stored_blocks':actual})
    return errors


def expand(conn,force=False):
    summary={'pages':0,'images':0,'fields':0,'charts':0,'errors':[]}
    if force:
        reviewed_tables=('chart_observations','state_intervals','report_text_events','chart_labels','report_fields','report_metrics','legend_symbol_hits','quantitative_layers','extended_bolus_spans','basal_rate_annotations')
        if any(conn.execute('SELECT count(*) FROM '+t+" WHERE review_status LIKE 'reviewed_%'").fetchone()[0] for t in reviewed_tables):
            raise ValueError('Hay datos revisados: no se permite reconstrucción automática destructiva')
        # Rebuild only this extractor's derived tables; original/CSV/OCR/profile tables remain intact.
        with conn:
            for table in ('extended_bolus_spans','basal_rate_annotations','quantitative_layers','plot_calibrations','quantitative_runs','legend_feature_links','legend_symbol_hits','legend_chart_scans','state_intervals','chart_observations','visual_series','chart_labels','report_text_events','native_text_blocks','native_drawings','pdf_layout_verifications','report_metrics','sleep_schedules','report_fields','report_image_masks','report_images','legend_templates','pdf_extractions'):
                conn.execute('DELETE FROM '+table)
    pages=conn.execute('''SELECT p.id,p.artifact_id,p.page_number,p.native_text FROM pdf_pages p
      WHERE NOT EXISTS(SELECT 1 FROM pdf_extractions e WHERE e.page_id=p.id AND e.extractor='full_pdf' AND e.version=? AND e.status='complete')
      ORDER BY p.artifact_id,p.page_number''',(VERSION,)).fetchall()
    for row in pages:
        try:
            content=conn.execute('SELECT content FROM artifacts WHERE id=?',(row['artifact_id'],)).fetchone()[0]
            with pymupdf.open(stream=content,filetype='pdf') as doc,conn:
                page=doc[row['page_number']-1]
                for number,block in enumerate(page.get_text('dict')['blocks']):
                    if block['type']!=0:continue
                    text_block='\n'.join(''.join(s['text'] for s in line['spans']) for line in block['lines'])
                    conn.execute('''INSERT OR IGNORE INTO native_text_blocks(page_id,block_number,text,bbox_json,spans_json)
                      VALUES(?,?,?,?,?)''',(row['id'],number,text_block,dumps(list(block['bbox'])),dumps(block['lines'])))
                text=row['native_text'];scope='summary_period' if text.startswith('Resumen general') else 'latest_upload_settings' if text.startswith('Configuración de la bomba') else 'timeline'
                dates=conn.execute('SELECT DISTINCT as_of_date FROM profiles p JOIN pdf_pages pg ON pg.id=p.page_id WHERE pg.artifact_id=? AND as_of_date IS NOT NULL',(row['artifact_id'],)).fetchall()
                asof=dates[0][0] if scope=='latest_upload_settings' and dates else None
                legend(conn,row['id'],page)
                templates=conn.execute('SELECT * FROM legend_templates WHERE page_id IN (SELECT id FROM pdf_pages WHERE artifact_id=?)',(row['artifact_id'],)).fetchall()
                # Other documents may not repeat the legend if the timeline is empty. Those charts remain explicit pending work.
                panels=conn.execute('SELECT * FROM daily_panels WHERE page_id=?',(row['id'],)).fetchall()
                results=[]
                blocks=[b for b in page.get_text('dict')['blocks'] if b['type']==1]
                for n,block in enumerate(blocks):
                    box=pymupdf.Rect(block['bbox']);im=Image.open(io.BytesIO(block['image']))
                    kind='daily_chart' if block['width']>1500 and scope=='timeline' else 'summary_chart' if block['width']>1500 and scope=='summary_period' else 'profile_table' if block['width']>1500 else 'table_background' if block['width']>700 else 'legend_asset'
                    panel=min(panels,key=lambda p:abs(json.loads(p['bbox_json'])[1]-box.y0*150/72)) if panels and kind=='daily_chart' else None
                    day=panel['local_date'] if panel and abs(json.loads(panel['bbox_json'])[1]-box.y0*150/72)<100 else None
                    encoded=png(np.array(im))
                    conn.execute('''INSERT OR IGNORE INTO report_images
                      (page_id,block_number,image_kind,bbox_json,width,height,sha256,image_png,local_date,panel_id)
                      VALUES(?,?,?,?,?,?,?,?,?,?)''',(row['id'],n,kind,dumps(list(box)),im.width,im.height,digest(encoded),encoded,day,panel['id'] if day else None))
                    iid=conn.execute('SELECT id FROM report_images WHERE page_id=? AND block_number=?',(row['id'],n)).fetchone()[0]
                    summary['images']+=1
                    if kind=='table_background':summary['fields']+=native_fields(conn,row['id'],iid,page,box,scope,asof)
                    elif kind=='summary_chart':results.append({'summary_chart':summary_series(conn,iid,np.array(im.convert('RGB')))})
                    elif kind=='daily_chart':
                        if not templates:raise ValueError('Falta leyenda para interpretar gráficos diarios')
                        rgb=np.array(im.convert('RGB'))
                        result=chart(conn,iid,rgb,day,templates)
                        result['labels']=chart_words(conn,row['id'],iid,box,rgb,day,result['axis'])
                        results.append(result);summary['charts']+=1
                native_events(conn,row['id'],page)
                conn.execute('''INSERT OR REPLACE INTO pdf_extractions(page_id,extractor,version,status,extracted_at,details_json)
                  VALUES(?,'full_pdf',?,'complete',?,?)''',(row['id'],VERSION,now(),dumps({'scope':scope,'chart_results':results,
                  'image_block_count':len(blocks),'native_block_count':sum(b['type']==0 for b in page.get_text('dict')['blocks']),
                  'meaning':'all_image_blocks_and_native_table_rows_indexed; graphical observations require review'})))
            summary['pages']+=1
            print(f"PDF ampliado página {row['id']} ({summary['pages']}/{len(pages)})",flush=True)
        except Exception as exc:
            with conn:conn.execute('''INSERT OR REPLACE INTO pdf_extractions VALUES(?,'full_pdf',?,'error',?,?)''',(row['id'],VERSION,now(),dumps({'error':str(exc)})))
            summary['errors'].append({'page_id':row['id'],'error':str(exc)})
    enrich_assets(conn)
    summary['layout_coverage_errors']=verify_layout(conn)
    summary['errors']+=summary['layout_coverage_errors']
    from .legend import catalogue,scan_charts
    summary['legend_catalogue']=catalogue(conn)
    summary['errors']+=summary['legend_catalogue']['errors']
    if not summary['legend_catalogue']['errors']:
        summary['legend_scan']=scan_charts(conn)
        summary['errors']+=summary['legend_scan']['errors']
    return summary
