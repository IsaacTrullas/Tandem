"""Last recorded observations, selected in memory without inferring current values."""
from bisect import bisect_left,bisect_right


def previous_observation(points,xs,x):
    index=bisect_right(xs,x)-1
    if index<0:return None
    selected=points[index];group=points[bisect_left(xs,selected['x']):index+1]
    result=dict(selected);details=dict(selected.get('details',{}));result['details']=details
    values={p.get('value') for p in group}
    revisions=max(((p.get('details',{}).get('revision_count') or 0) for p in group),default=0)
    variants=max((len(p.get('details',{}).get('revision_ids') or ()) for p in group),default=0)
    if len(values)>1 or revisions>1 or variants>1:
        details['ambiguous']=True;details['alternatives']=sorted(str(value) for value in values)
        result['value']=None
    details['observation_count']=max(len(group),revisions,variants)
    return result


def elapsed_label(point,x,clock_changes=(),ambiguous_ranges=()):
    if point is None:return ''
    start=point['x'];details=point.get('details',{})
    if (details.get('clock_change_between') or any(start<c['x']<=x for c in clock_changes)
            or any(start<=b and x>=a for a,b in ambiguous_ranges)):
        return 'Reloj modificado'
    age=max(0,int(x-start))
    if age==0:return 'En este instante'
    if age<60:return f'Hace {age} s'
    minutes=age//60
    if minutes<60:return f'Hace {minutes} min'
    hours=minutes//60
    if hours<24:return f'Hace {hours} h'+(f' {minutes%60} min' if minutes%60 else '')
    return f'Hace {hours//24} d'+(f' {hours%24} h' if hours%24 else '')
