"""Step regions between observed commanded/profile rates; gaps stay empty."""
import math
def regions(points,clocks=()):
    output=[]
    for point,nxt in zip(points,points[1:]):
        a,b=point['x'],nxt['x'];rate=point.get('value');profile=point.get('details',{}).get('profile_rate')
        if not 0<b-a<=720 or any(a<c['x']<=b for c in clocks):continue
        if any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in (rate,profile)) or rate==profile:continue
        output.append((a,b,min(rate,profile),max(rate,profile),'above' if rate>profile else 'below'))
    return output
