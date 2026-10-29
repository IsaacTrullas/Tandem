from __future__ import annotations
import io
import re
from datetime import date
from pypdf import PdfReader
from .db import dumps,issue

MONTHS={'ene':1,'enero':1,'feb':2,'febrero':2,'mar':3,'marzo':3,'abr':4,'abril':4,'may':5,'mayo':5,
 'jun':6,'junio':6,'jul':7,'julio':7,'ago':8,'agosto':8,'sept':9,'sep':9,'septiembre':9,
 'oct':10,'octubre':10,'nov':11,'noviembre':11,'dic':12,'diciembre':12}
DATE=re.compile(r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})',re.I)

def decimal(value):
    return float(value.replace(',','.'))

def date_spanish(day,month,year):
    return date(int(year),MONTHS[month.lower().strip('.')],int(day)).isoformat()

def profile_extract(conn,page_id,text):
    asof=re.search(r'Configuración de la bomba\s+(\d{1,2})\s+([a-z]+)\s+(\d{4})',text,re.I)
    asof=date_spanish(*asof.groups()) if asof else None
    headings=list(re.finditer(r'Configuración del perfil de la bomba\s*-\s*([^\n]+)',text))
    row_pattern=re.compile(r'(?m)^\s*(\d{1,2}:\d{2})\s+([\d,\.]+)\s+1:([\d,\.]+)\s+1:([\d,\.]+)\s+(\d+)\s*$')
    for n,heading in enumerate(headings):
        chunk=text[heading.end():headings[n+1].start() if n+1<len(headings) else len(text)]
        name=heading.group(1).split('Activo en la subida')[0].strip()
        active='Activo en la subida' in heading.group(1) or 'Activo en la subida' in chunk[:100]
        daily=re.search(r'Basal diario total:\s*([\d,\.]+)',chunk)
        duration=re.search(r'Duración de insulina:\s*([\d,\.]+)\s*h',chunk)
        conn.execute('''INSERT OR IGNORE INTO profiles(page_id,name,active_at_upload,as_of_date,duration_hours,daily_basal_units,source_text)
          VALUES(?,?,?,?,?,?,?)''',(page_id,name,int(active),asof,decimal(duration.group(1)) if duration else None,
                                  decimal(daily.group(1)) if daily else None,heading.group(0)+'\n'+chunk))
        pid=conn.execute('SELECT id FROM profiles WHERE page_id=? AND name=?',(page_id,name)).fetchone()[0]
        matches=list(row_pattern.finditer(chunk))
        for match in matches:
            clock,basal,cf,ic,target=match.groups()
            conn.execute('INSERT OR IGNORE INTO profile_segments VALUES(?,?,?,?,?,?)',
                         (pid,clock.zfill(5),decimal(basal),decimal(cf),decimal(ic),float(target)))
        if not matches: issue(conn,'profile_segments_not_parsed',{'profile':name},page_id=page_id)

def ingest_pdf(conn,artifact_id,content):
    import pymupdf
    reader=PdfReader(io.BytesIO(content))
    doc=pymupdf.open(stream=content,filetype='pdf')
    for i,page in enumerate(reader.pages):
        text=page.extract_text() or ''
        rendered=doc[i]
        words=rendered.get_text('words')
        conn.execute('''INSERT OR IGNORE INTO pdf_pages
          (artifact_id,page_number,width_points,height_points,native_text,words_json,raster_image_count)
          VALUES(?,?,?,?,?,?,?)''',(artifact_id,i+1,float(page.mediabox.width),float(page.mediabox.height),text,dumps(words),len(rendered.get_images())))
        page_id=conn.execute('SELECT id FROM pdf_pages WHERE artifact_id=? AND page_number=?',(artifact_id,i+1)).fetchone()[0]
        profile_extract(conn,page_id,text)
        for n,part in enumerate(text.split('•')[1:]):
            warning=part.split('\nResumen de MCG')[0].strip()
            if warning:
                conn.execute('''INSERT OR IGNORE INTO pdf_facts
                  (page_id,category,name,value_json,evidence_text,extraction_method,review_status)
                  VALUES(?,?,?,?,?,?,?)''',(page_id,'report_warning',f'warning_{n}',dumps({'text':warning}),warning,'pdf_native_text','source_text'))
    doc.close()

def ocr_box(line):
    words=line.get('words',[])
    boxes=[w['bounding_rect'] for w in words]
    if not boxes: return [0,0,0,0]
    return [min(b['x'] for b in boxes),min(b['y'] for b in boxes),
            max(b['x']+b['width'] for b in boxes),max(b['y']+b['height'] for b in boxes)]

def parse_ocr_page(conn,page_id,result,width,height):
    lines=[{'text':x['text'],'box':ocr_box(x)} for x in result.get('lines',[])]
    date_lines=[]
    for line in lines:
        match=DATE.search(line['text'])
        if not match: continue
        try: local_date=date_spanish(*match.groups())
        except (ValueError,KeyError): continue
        date_lines.append({**line,'date':local_date})
    date_lines.sort(key=lambda x:(x['box'][1],x['box'][0]))
    panels=[]
    for n,line in enumerate(date_lines):
        y=line['box'][1]
        bottom=date_lines[n+1]['box'][1]-2 if n+1<len(date_lines) else height-45
        header_lines=sorted((l for l in lines if abs(l['box'][1]-y)<16),key=lambda x:x['box'][0])
        header=' '.join(l['text'] for l in header_lines)
        facts={}
        for key,pattern,unit in [
          ('time_in_range',r'Tiempo\s+en\s+el\s+rango:\s*([\d,.]+)\s*%','percent'),
          ('average_glucose',r'Promedio:\s*([\d,.]+)\s*mg','mg/dL'),
          ('glucose_sd',r'SD:\s*([\d,.]+)\s*mg','mg/dL'),
          ('daily_insulin',r'DTI:\s*([\d,.]+)\s*unidades','U'),
          ('carbohydrates',r'Carbos:\s*([\d,.]+)\s*g','g')]:
            hit=re.search(pattern,header,re.I)
            if hit: facts[key]={'value':decimal(hit.group(1)),'unit':unit}
        bbox=[0,max(0,y-4),width,max(y+4,bottom)]
        conn.execute('''INSERT OR IGNORE INTO daily_panels
          (page_id,local_date,panel_index,bbox_json,header_text,facts_json) VALUES(?,?,?,?,?,?)''',
          (page_id,line['date'],n,dumps(bbox),header,dumps(facts)))
        pid=conn.execute('SELECT id FROM daily_panels WHERE page_id=? AND panel_index=?',(page_id,n)).fetchone()[0]
        panels.append({'id':pid,'date':line['date'],'y':y,'bottom':bottom})
        for key,value in facts.items():
            conn.execute('''INSERT OR IGNORE INTO pdf_facts
              (page_id,category,name,local_date,value_json,evidence_text,bbox_json,extraction_method,review_status)
              VALUES(?,?,?,?,?,?,?,?,?)''',(page_id,'daily_statistic',key,line['date'],dumps(value),header,
              dumps(bbox),'windows_ocr','ocr_unreviewed'))
    # Only explicit text describing an alert becomes an event. Legend icons or labels never do.
    for line in lines:
        if not re.search(r'(Alertas?\s+de\s+MCG|Alarmas?\s+de\s+la\s+bomba)\s*:',line['text'],re.I): continue
        y=line['box'][1]
        panel=next((p for p in reversed(panels) if p['y']<=y<=p['bottom']),None)
        d=panel['date'] if panel else None
        clock=re.search(r'(?<!\d)(\d{1,2}:\d{2})(?!\d)',line['text'])
        start=f'{d}T{clock.group(1).zfill(5)}:00' if d and clock else None
        conn.execute('''INSERT OR IGNORE INTO therapy_events
          (page_id,panel_id,event_type,local_date,start_local,evidence_text,bbox_json,extraction_method,review_status,details_json)
          VALUES(?,?,?,?,?,?,?,?,?,?)''',(page_id,panel['id'] if panel else None,'cgm_alert' if 'MCG' in line['text'] else 'pump_alarm',
          d,start,line['text'],dumps(line['box']),'windows_ocr','ocr_unreviewed',dumps({'date_assignment':'preceding_daily_panel' if panel else 'unresolved'})))
    return len(panels)

def run_ocr(conn,limit=None,language='es',dpi=150):
    import pymupdf
    import winocr
    from PIL import Image
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    if not OcrEngine.is_language_supported(Language(language)):
        raise RuntimeError('No está instalado el OCR de Windows para '+language+'. No se han cambiado idiomas del sistema.')
    query="SELECT p.id,p.page_number,a.id artifact_id,a.filename FROM pdf_pages p JOIN artifacts a ON a.id=p.artifact_id WHERE p.ocr_status IN ('pending','error') ORDER BY a.id,p.page_number"
    rows=conn.execute(query).fetchall()
    if limit is not None: rows=rows[:limit]
    summary={'processed_pages':0,'panels':0,'errors':[]}
    for row in rows:
        try:
            content=conn.execute('SELECT content FROM artifacts WHERE id=?',(row['artifact_id'],)).fetchone()[0]
            with pymupdf.open(stream=content,filetype='pdf') as doc:
                pix=doc[row['page_number']-1].get_pixmap(dpi=dpi,alpha=False)
                image=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
                if max(image.size)>OcrEngine.max_image_dimension:
                    raise ValueError('La imagen excede el tamaño máximo del motor OCR')
                result=winocr.recognize_pil_sync(image,language)
                buffer=io.BytesIO()
                image.save(buffer,format='PNG',optimize=True)
            text='\n'.join(line['text'] for line in result.get('lines',[]))
            with conn:
                panels=parse_ocr_page(conn,row['id'],result,image.width,image.height)
                conn.execute('''UPDATE pdf_pages SET rendered_png=?,ocr_text=?,ocr_json=?,ocr_engine=?,ocr_status='complete',ocr_error=NULL WHERE id=?''',
                  (buffer.getvalue(),text,dumps({'width':image.width,'height':image.height,'dpi':dpi,'result':result}),
                   'Windows.Media.Ocr via winocr 0.0.15 / '+language,row['id']))
            summary['processed_pages']+=1
            summary['panels']+=panels
            print(f"OCR {row['filename']} página {row['page_number']} ({summary['processed_pages']}/{len(rows)})",flush=True)
        except Exception as exc:
            with conn: conn.execute("UPDATE pdf_pages SET ocr_status='error',ocr_error=? WHERE id=?",(str(exc),row['id']))
            summary['errors'].append({'page_id':row['id'],'error':str(exc)})
    return summary
