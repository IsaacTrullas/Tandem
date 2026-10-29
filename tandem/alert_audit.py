"""Read-only alert/CGM comparison. At most one sensor day is held in memory."""
from bisect import bisect_left,bisect_right
from collections import defaultdict
from contextlib import closing
from datetime import datetime,timedelta
from pathlib import Path
import json,sqlite3,statistics

SOURCE='https://www.tandemdiabetes.com/support-center/software-updates/tslimx2-insulin-pump/article/control-iq-alerts-on-tslimx2'

def audit(db,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    groups=defaultdict(lambda:{'events':0,'matched':0,'missing':0,'ambiguous':0,'values':[]})
    cached=None;count=0
    with closing(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)) as c, (output/'alertas_glucosa.jsonl').open('w',encoding='utf-8') as out:
        c.execute('PRAGMA query_only=ON');c.execute('BEGIN')
        for eid,serial,stamp,code,raw in c.execute('SELECT id,pump_serial,local_timestamp,event_code,values_json FROM api_events WHERE event_code IN(4,5,369) AND local_timestamp IS NOT NULL ORDER BY pump_serial,local_timestamp,id'):
            dt=datetime.fromisoformat(stamp);day=dt.date();key=(serial,day)
            if cached!=key:
                lo=datetime.combine(day,datetime.min.time())-timedelta(minutes=10);hi=lo+timedelta(days=1,minutes=10)
                samples=list(c.execute("""SELECT json_extract(values_json,'$.measurement_local_timestamp'),value,id,
                    (SELECT count(*) FROM api_events r WHERE r.device_id=e.device_id AND r.identity_key=e.identity_key)
                    FROM api_events e WHERE pump_serial=? AND kind='cgm' AND unit='mg/dL'
                    AND json_extract(values_json,'$.measurement_local_timestamp')>=?
                    AND json_extract(values_json,'$.measurement_local_timestamp')<?
                    ORDER BY json_extract(values_json,'$.measurement_local_timestamp'),id""",(serial,lo.isoformat(),hi.isoformat())))
                xs=[s[0] for s in samples]
                clocks=[r[0] for r in c.execute('SELECT local_timestamp FROM api_events WHERE pump_serial=? AND event_code IN(13,14) AND local_timestamp>=? AND local_timestamp<?',(serial,lo.isoformat(),hi.isoformat()))]
                cached=key
            data=json.loads(raw);field={4:'alertId',5:'alarmId',369:'dalertId'}[code]
            identifier=data.get('properties',{}).get(field);label=data.get('labels',{}).get(field,'Sin etiqueta')
            group=groups[(code,str(identifier),label)];group['events']+=1
            result={'event_id':eid,'time':stamp,'event_code':code,'identifier':identifier,'label':label,'glucose':None}
            i=bisect_right(xs,stamp)-1
            if i>=0 and 0<=(dt-datetime.fromisoformat(xs[i])).total_seconds()<=600:
                sample=samples[i];same=samples[bisect_left(xs,sample[0]):i+1]
                ambiguous=sample[3]>1 or len({s[1] for s in same})>1 or any(sample[0]<=clock<=stamp for clock in clocks)
                if ambiguous:group['ambiguous']+=1;result['match_status']='ambiguous_clock_or_revision'
                elif sample[1] is not None:
                    group['matched']+=1;group['values'].append(sample[1]);result.update(glucose=sample[1],glucose_time=sample[0],sample_id=sample[2],age_seconds=(dt-datetime.fromisoformat(sample[0])).total_seconds(),match_status='prior_cgm_within_10min')
                else:group['missing']+=1;result['match_status']='no_numeric_cgm'
            else:group['missing']+=1;result['match_status']='no_prior_cgm_within_10min'
            out.write(json.dumps(result,ensure_ascii=False)+'\n');count+=1
        summary=[]
        for (code,identifier,label),group in sorted(groups.items()):
            values=group.pop('values')
            summary.append(dict(event_code=code,identifier=identifier,label=label,**group,
                min=min(values) if values else None,median=statistics.median(values) if values else None,max=max(values) if values else None,
                above_200=sum(v>200 for v in values),below_70=sum(v<70 for v in values)))
    report={'events':count,'method':'Latest prior numeric CGM within 600 seconds using measurement time, no interpolation or future values; same-wall-time revisions/clock barriers excluded. Association is not a causal or threshold determination.', 'official_reference':SOURCE,'summary':summary}
    (output/'resumen_alertas.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--db',required=True);p.add_argument('--output',required=True)
    args=p.parse_args();print(json.dumps(audit(args.db,args.output),ensure_ascii=False))
