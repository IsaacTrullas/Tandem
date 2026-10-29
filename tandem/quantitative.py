"""Separate daily-chart layers, calibrated in source pixels and linked to source CSV.

All graphical quantities are estimates or OCR transcriptions, never additional doses.
Overlapping profile/Control-IQ ink and unsupported geometry remain explicit evidence.
"""
from __future__ import annotations
import io,json,re
from datetime import datetime,timedelta
import cv2,numpy as np
from PIL import Image
from .db import dumps,now
from .visual import axes,groups,minute
from .legend import encode

VERSION='1.1'
KEYS=('basal_delivered','basal_setting','basal_temporary','basal_control_iq','bolus_extended')


def match_ink(rgb,color,tolerance=14):
    """Recognize a zero-red source stroke and its white antialias; exclude pale fill."""
    a=rgb.astype(float)
    alpha=1-a[:,:,0]/255
    valid=alpha>.35
    safe=np.maximum(alpha,.01)
    green=255+(a[:,:,1]-255)/safe
    blue=255+(a[:,:,2]-255)/safe
    return valid&(abs(green-color[1])<=tolerance)&(abs(blue-color[2])<=tolerance)


def baseline(rgb,axis):
    left,right,top,bottom=axis;h=rgb.shape[0]
    gray=(rgb.max(2)-rgb.min(2)<4)&(rgb[:,:,0]>110)&(rgb[:,:,0]<170)
    lines=[(a,b) for a,b in groups(np.where(gray[:,left:right].sum(1)>(right-left)*.75)[0]) if h*.82<a<h*.94]
    if not lines:raise ValueError('No hay eje basal cero verificable')
    a,b=lines[-1]
    return (a+b-1)/2


def fit_calibration(ticks,zero_y,grid_lines=None,readouts=None):
    # Tick text has a vertical font offset; use spacing for slope and drawn zero for origin.
    if len(ticks)==1 and grid_lines and readouts:
        tick=ticks[0]
        y=min(grid_lines,key=lambda y:abs(y-tick['y']))
        if abs(y-tick['y'])>12 or zero_y-y<20:return None
        factor=tick['value']/(zero_y-y)
        checks=[{'text':a['text'],'rate':a['rate'],'axis_rate':(zero_y-a['line_y'])*factor}
                for a in readouts if a['line_y'] is not None]
        if not checks or any(abs(a['rate']-a['axis_rate'])>max(.03,factor*5) for a in checks):return None
        return {'zero_y':float(zero_y),'units_per_pixel':float(factor),
          'uncertainty_units_per_hour':float(factor*max(4,abs(y-tick['y'])+1)),
          'method':'one_printed_tick_plus_drawn_zero_validated_against_profile_readouts',
          'tick_grid_y':float(y),'independent_readout_checks':checks}
    if len(ticks)<2:return None
    vals=np.array([t['value'] for t in ticks]);ys=np.array([t['y'] for t in ticks])
    if len(set(vals))<2:return None
    slope,intercept=np.polyfit(vals,ys,1)
    residual=float(np.max(abs(ys-(slope*vals+intercept))))
    if slope>=-3 or residual>3:return None
    unit_per_pixel=float(-1/slope)
    return {'zero_y':float(zero_y),'units_per_pixel':unit_per_pixel,
      'uncertainty_units_per_hour':unit_per_pixel*max(4.,residual+3),
      'tick_residual_pixels':residual,'text_zero_offset_pixels':float(intercept-zero_y)}


def focused_ocr(rgb,axis):
    import winocr
    left,right,top,bottom=axis;h,w=rgb.shape[:2]
    start=max(0,bottom-20)
    lane=winocr.recognize_pil_sync(Image.fromarray(rgb[start:]),'es')
    # Native resolution is deliberate: Windows OCR can miss isolated decimal ticks when enlarged.
    x0=max(0,right-15);x1=min(w,right+105)
    ticks=winocr.recognize_pil_sync(Image.fromarray(rgb[start:h-45,x0:x1]),'es')
    return {'lane':lane,'lane_y':start,'ticks':ticks,'ticks_x':x0,'ticks_y':start}


def read_ticks(ocr,right):
    values=[]
    for line in ocr['ticks'].get('lines',[]):
        for word in line.get('words',[]):
            text=word['text'];r=word['bounding_rect']
            if not re.fullmatch(r'\d+(?:[,.]\d+)?',text):continue
            x=ocr['ticks_x']+r['x']
            if x<=right:continue
            value=float(text.replace(',','.'))
            if not 0<value<=100:continue
            values.append({'value':value,'y':ocr['ticks_y']+r['y']+r['height']/2,'source_text':text})
    # Different OCR fragments at one height are ambiguous, not extra axis ticks.
    result=[]
    for t in sorted(values,key=lambda t:t['y']):
        if not result or t['y']-result[-1]['y']>15:result.append(t)
    return result


def profile_line(rgb,axis,zero):
    left,right,top,bottom=axis
    mask=match_ink(rgb,(0,118,174),11)
    mask[:bottom+5]=False;mask[int(zero)+1:]=False
    # Text is darker, and short vertical bar edges cannot create a horizontal profile step.
    horizontal=cv2.morphologyEx(mask.astype('uint8'),cv2.MORPH_OPEN,np.ones((1,12),np.uint8)).astype(bool)
    points={}
    for x in range(left,right+1):
        ys=np.where(horizontal[:,x])[0]
        if len(ys):points[x]=float(np.median(ys))
    return points


def annotations(ocr,axis,line):
    left,right,top,bottom=axis;found=[]
    for item in ocr['lane'].get('lines',[]):
        for word in item.get('words',[]):
            text=word['text'];r=word['bounding_rect']
            if not re.fullmatch(r'\d+[,.]\d{2,4}',text):continue
            box=[r['x'],r['y']+ocr['lane_y'],r['x']+r['width'],r['y']+r['height']+ocr['lane_y']]
            if not left-4<=box[0]<right:continue
            nearby=[y for x,y in line.items() if box[0]-5<=x<=box[2]+5 and -5<=y-box[3]<=18]
            y=float(np.median(nearby)) if nearby else None
            found.append({'text':text,'rate':float(text.replace(',','.')),'box':box,'line_y':y,
                          'association':'step_label' if y is not None else 'unresolved_annotation_or_carry_in'})
    return found


def separate_layers(rgb,axis,calibration,labels):
    left,right,top,bottom=axis;zero=calibration['zero_y'];factor=calibration['units_per_pixel']
    nominal=profile_line(rgb,axis,zero)
    bright=match_ink(rgb,(0,145,220),15)
    bright[:bottom+5]=False;bright[int(zero)+1:]=False
    caps=cv2.morphologyEx(bright.astype('uint8'),cv2.MORPH_OPEN,np.ones((1,3),np.uint8)).astype(bool)
    fill=(rgb[:,:,2]>225)&(rgb[:,:,1]>200)&(rgb[:,:,0]>155)&(rgb[:,:,0]<230)&(rgb[:,:,2]>rgb[:,:,0].astype(int)+25)
    points={'basal_setting':[],'basal_delivered':[],'basal_control_iq':[]}
    for x in range(left,right+1):
        t=minute(x,axis)
        if x in nominal:
            y=nominal[x]
            estimate=max(0,(zero-y)*factor)
            options=[a for a in labels if a['line_y'] is not None and abs(a['line_y']-y)<=2
                     and abs(a['rate']-estimate)<=calibration['uncertainty_units_per_hour']*1.5+.01]
            if options:
                selected=min(options,key=lambda a:(abs(a['line_y']-y),abs(a['box'][0]-x)))
                value=selected['rate'];method='ocr_step_label'
            else:value=estimate;method='axis_digitized; no_consistent_readout'
            points['basal_setting'].append([x,t,y,value,method])
            # This is visible reference-profile fill, not an additional measured insulin delivery.
            band=fill[min(int(zero),int(y)+3):int(zero),x]
            if len(band) and band.mean()>.25:points['basal_delivered'].append([x,t,y,value,'visible_profile_fill; overlaps_possible'])
        ys=np.where(caps[:,x])[0]
        if len(ys):
            y=float(ys.min());points['basal_control_iq'].append([x,t,y,max(0,(zero-y)*factor),'bright_bar_top_digitized'])
    return points


def temporary_regions(rgb,axis,zero):
    """Require orange interior and the legend's dashed-top/solid-side boundary pattern."""
    left,right,top,bottom=axis
    roi=rgb[bottom+3:int(zero),left:right+1]
    fill=np.abs(roi.astype(int)-np.array([255,240,216])).max(2)<=5
    n,_,stats,_=cv2.connectedComponentsWithStats(fill.astype('uint8'))
    regions=[]
    for x,y,w,h,area in stats[1:]:
        if w<12 or h<5 or area<w*h*.6:continue
        x0,y0=int(left+x),int(bottom+3+y);x1,y1=x0+int(w),y0+int(h)
        expanded=rgb[max(bottom+2,y0-4):min(int(zero)+2,y1+5),max(left,x0-4):min(right+1,x1+5)]
        orange=(expanded[:,:,0]>180)&(expanded[:,:,1]>=80)&(expanded[:,:,1]<205)&(expanded[:,:,2]<155)&(expanded[:,:,0]>expanded[:,:,1].astype(int)+35)
        good_edges=0;solid_edges=0
        for edge in (orange[:5].any(0),orange[-5:].any(0),orange[:,:5].any(1),orange[:,-5:].any(1)):
            runs=groups(np.where(edge)[0]);gaps=[runs[i+1][0]-runs[i][1] for i in range(len(runs)-1)]
            if len(runs)>=2 and any(g>=2 for g in gaps):good_edges+=1
            if edge.mean()>=.7:solid_edges+=1
        valid=good_edges>=2 or (good_edges>=1 and solid_edges>=2)
        regions.append({'box':[x0,y0,x1,y1],'dashed_edges':good_edges,'solid_edges':solid_edges,
          'classification':'temporary_fill_and_dashes' if valid else 'ambiguous_orange_fill_border_unresolved'})
    return regions


def extended_rectangles(rgb,axis):
    left,right,top,bottom=axis
    roi=rgb[max(0,top-28):top,left:right+1]
    # Extended bars have a muted pale-blue fill, distinct from blue drop interiors and basal ink.
    fill=(roi[:,:,0]>=175)&(roi[:,:,0]<=218)&(roi[:,:,1]>=210)&(roi[:,:,1]<=237)&(roi[:,:,2]>=228)&(roi[:,:,2]<=252)
    col=(fill.sum(0)>=3).astype('uint8').reshape(1,-1)
    joined=cv2.morphologyEx(col,cv2.MORPH_CLOSE,np.ones((1,8),np.uint8)).ravel()
    return [[a+left,top-28,b+left,top] for a,b in groups(np.where(joined)[0]) if b-a>=8]


def expected_extended(row,day):
    start=datetime.fromisoformat(row['extended_start_local']);end=datetime.fromisoformat(row['extended_end_local'])
    midnight=datetime.fromisoformat(day);stop=midnight+timedelta(days=1)
    if start>=stop or end<=midnight:return None
    a,b=max(start,midnight),min(end,stop)
    return a,b,(a-midnight).total_seconds()/60,(b-midnight).total_seconds()/60


def match_extended(rectangles,rows,day,axis,tolerance_minutes=4):
    matches=[]
    for row in rows:
        if not row['extended_start_local'] or not row['extended_end_local']:continue
        expected=expected_extended(row,day)
        if not expected:continue
        start,end,a,b=expected
        candidates=[]
        eligible=[r for r in rectangles if minute(r[2],axis)>=a-tolerance_minutes and minute(r[0],axis)<=b+tolerance_minutes]
        eligible.sort(key=lambda r:r[0])
        for i,first in enumerate(eligible):
            for j in range(i,len(eligible)):
                pieces=eligible[i:j+1]
                if any(pieces[k+1][0]-pieces[k][2]>60 for k in range(len(pieces)-1)):break
                rect=[first[0],min(p[1] for p in pieces),pieces[-1][2],max(p[3] for p in pieces)]
                lower,upper=minute(rect[0],axis),minute(rect[2],axis)
                error=max(abs(lower-a),abs(upper-b))
                visible=sum(p[2]-p[0] for p in pieces)/max(1,rect[2]-rect[0])
                if error<=tolerance_minutes and visible>=.6:candidates.append((error,rect,lower,upper))
        if len(candidates)!=1:continue
        error,rect,lower,upper=candidates[0]
        matches.append({'row':row,'slice_start':start.isoformat(),'slice_end':end.isoformat(),'box':rect,
                        'lower':lower,'upper':upper,'error':error})
    return matches


def process(conn):
    from .legend import seed
    with conn:seed(conn)
    summary={'charts':0,'calibrated':0,'extended_spans':0,'errors':[],'unscaled':[]}
    rows=conn.execute("""SELECT i.id,i.local_date FROM report_images i WHERE image_kind='daily_chart'
      AND (NOT EXISTS(SELECT 1 FROM quantitative_runs r WHERE r.image_id=i.id AND r.version=? AND r.status='complete')
           OR EXISTS(SELECT 1 FROM plot_calibrations p WHERE p.image_id=i.id AND p.status='unscaled'))""",(VERSION,)).fetchall()
    extended=conn.execute("SELECT * FROM boluses WHERE delivery_method='Extendido'").fetchall()
    for row in rows:
        iid=row['id']
        try:
            data=conn.execute('SELECT image_png FROM report_images WHERE id=?',(iid,)).fetchone()[0]
            rgb=np.array(Image.open(io.BytesIO(data)).convert('RGB'))
            try:axis=axes(rgb)
            except ValueError:
                previous=conn.execute('SELECT details_json FROM legend_chart_scans WHERE image_id=?',(iid,)).fetchone()
                if previous and json.loads(previous[0]).get('no_active_axis_clock_panel'):
                    with conn:conn.execute('INSERT OR REPLACE INTO quantitative_runs VALUES(?,?,?,?,?)',(iid,VERSION,'complete',now(),dumps({'empty_clock_panel':True})))
                    continue
                raise
            zero=baseline(rgb,axis)
            cached=conn.execute("SELECT focused_ocr_json FROM plot_calibrations WHERE image_id=? AND status='calibrated'",(iid,)).fetchone()
            ocr=json.loads(cached[0]) if cached else focused_ocr(rgb,axis)
            ticks=read_ticks(ocr,axis[1])
            line=profile_line(rgb,axis,zero);labels=annotations(ocr,axis,line)
            # Clock-split charts fade the unused side, including grid lines. Keep those faint
            # neutral lines for calibration, while excluding white (255) and coloured traces.
            neutral=(rgb.max(2)-rgb.min(2)<4)&(rgb[:,:,0]>=130)&(rgb[:,:,0]<=252)
            grid=[(a+b-1)/2 for a,b in groups(np.where(neutral[:,axis[0]:axis[1]].sum(1)>(axis[1]-axis[0])*.65)[0]) if axis[3]<=a<=zero]
            cal=fit_calibration(ticks,zero,grid,labels)
            rects=extended_rectangles(rgb,axis)
            matches=match_extended(rects,extended,row['local_date'],axis) if row['local_date'] else []
            with conn:
                conn.execute('''INSERT OR REPLACE INTO plot_calibrations VALUES(?,?,?,?,?,?,?,?,?)''',
                  (iid,VERSION,'calibrated' if cal else 'unscaled',zero,cal['units_per_pixel'] if cal else None,
                   cal['uncertainty_units_per_hour'] if cal else None,dumps(ticks),dumps(ocr),dumps(cal or {'reason':'insufficient_or_inconsistent_ticks'})))
                for label in labels:
                    conn.execute('''INSERT OR IGNORE INTO basal_rate_annotations(image_id,text,rate_units_per_hour,bbox_json,line_y,minute_position,association)
                      VALUES(?,?,?,?,?,?,?)''',(iid,label['text'],label['rate'],dumps(label['box']),label['line_y'],
                      minute(label['box'][0],axis) if label['line_y'] is not None else None,label['association']))
                if cal:
                    for key,points in separate_layers(rgb,axis,cal,labels).items():
                        box=[axis[0],axis[3],axis[1],int(zero)+1]
                        conn.execute('''INSERT INTO quantitative_layers
                          (image_id,definition_key,layer_key,unit,points_json,bbox_json,evidence_png,details_json) VALUES(?,?,?,?,?,?,?,?)
                          ON CONFLICT(image_id,layer_key) DO UPDATE SET points_json=excluded.points_json,
                          bbox_json=excluded.bbox_json,evidence_png=excluded.evidence_png,details_json=excluded.details_json
                          WHERE quantitative_layers.review_status NOT LIKE 'reviewed_%' ''',
                          (iid,key,key,'U/h',dumps(points),dumps(box),encode(rgb[box[1]:box[3],box[0]:box[2]+1]),
                           dumps({'version':VERSION,'axis':axis,'calibration':cal,'source':'PDF; not additional CSV doses',
                            'profile_fill_and_line_are_nonadditive_attributes':True,'not_a_proven_CIQ_enabled_interval':True,'points_columns':['x','minute','y','rate','method']})))
                    summary['calibrated']+=1
                else:summary['unscaled'].append(iid)
                temps=temporary_regions(rgb,axis,zero)
                for n,temp in enumerate(temps):
                    b=temp['box'];value=(zero-b[1])*cal['units_per_pixel'] if cal else None
                    conn.execute('''INSERT OR IGNORE INTO quantitative_layers(image_id,definition_key,layer_key,unit,points_json,bbox_json,evidence_png,details_json)
                      VALUES(?,?,?,?,?,?,?,?)''',(iid,'basal_temporary',f'temporary:{n}','U/h',
                      dumps([[b[0],minute(b[0],axis),b[1],value,'orange_fill_and_border'],[b[2],minute(b[2],axis),b[1],value,'orange_fill_and_border']]),
                      dumps(b),encode(rgb[max(0,b[1]-5):b[3]+6,max(0,b[0]-5):b[2]+6]),dumps(temp)))
                for m in matches:
                    b=m['box'];record=m['row']
                    conn.execute('''INSERT OR IGNORE INTO extended_bolus_spans
                      (bolus_record_id,image_id,slice_start_local,slice_end_local,plot_start_minute,plot_end_minute,duration_minutes_csv,
                       total_units_csv,extended_units_csv,endpoint_error_minutes,bbox_json,evidence_png,details_json)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)''',(record['record_id'],iid,m['slice_start'],m['slice_end'],m['lower'],m['upper'],record['duration_minutes'],
                       record['delivered_units'],record['extended_units'],m['error'],dumps(b),encode(rgb[b[1]:b[3]+3,max(0,b[0]-3):b[2]+4]),
                       dumps({'method':'unique_two_endpoint_match_to_CSV','quantity_source':'CSV; not bar width',
                              'not_an_additional_bolus':True,'slice_can_cross_or_end_at_midnight':True})))
                summary['extended_spans']+=len(matches)
                conn.execute('INSERT OR REPLACE INTO quantitative_runs VALUES(?,?,?,?,?)',(iid,VERSION,'complete',now(),
                  dumps({'calibration':'calibrated' if cal else 'unscaled','annotations':len(labels),'temporary_regions':len(temps),'extended_candidates':len(rects),'extended_matches':len(matches)})))
            summary['charts']+=1
            print(f'Capas cuantitativas: gráfico {iid} ({summary["charts"]}/{len(rows)})',flush=True)
        except Exception as exc:
            with conn:conn.execute('INSERT OR REPLACE INTO quantitative_runs VALUES(?,?,?,?,?)',(iid,VERSION,'error',now(),dumps({'error':str(exc)})))
            summary['errors'].append({'image_id':iid,'error':str(exc)})
    return summary
