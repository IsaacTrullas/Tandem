"""Mode-lane geometry from the already bounded timeline bundle.

No database access, timezone conversion, current settings or inference from PDF
colours. A segment represents the latest explicit mode observation until the
next mode, clock barrier or last available observation in this loaded window.
"""
from __future__ import annotations

from bisect import bisect_right
from datetime import datetime
import math

LABELS={'sleep':'Sueño','exercise':'Ejercicio','normal':'Estándar',
        'eating_soon':'Comida próxima','unknown':'Modo no confirmado'}
EPOCH=datetime(1970,1,1)


def _finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def _stamp(value):
    if _finite(value):return float(value)
    if isinstance(value,str):
        try:
            parsed=datetime.fromisoformat(value)
            if parsed.tzinfo is None:return (parsed-EPOCH).total_seconds()
        except ValueError:pass
    return None


def derive_mode_segments(bundle):
    """Return bounded mode segments, including explicit ambiguity spans.

    Required output keys: start/end, mode, label, source, uncertain. Additional
    provenance/boundary flags allow the UI to distinguish a clipped display from
    a confirmed mode end. The interval end is exclusive; zero-length spans are
    never returned. Both end-of-day extrapolation and clock-gap carry are avoided.
    """
    data=bundle.get('data',{});context=bundle.get('context',{})
    start=_stamp(bundle.get('view_start',bundle.get('cache_start',context.get('start'))))
    width=bundle.get('view_width')
    end=start+width if start is not None and _finite(width) else _stamp(bundle.get('cache_end',context.get('end')))
    cache_start=_stamp(bundle.get('cache_start',start));cache_end=_stamp(bundle.get('cache_end',end))
    if start is None or end is None or end<=start:return []
    if cache_start is not None:start=max(start,cache_start)
    if cache_end is not None:end=min(end,cache_end)

    # Only observation times in this loaded data bundle establish availability.
    # The requested window's right edge is not evidence of pump data there.
    observed=[]
    for key in ('glucose','boluses','carbs','basal','events','clock_changes'):
        observed.extend(float(p['x']) for p in data.get(key,[]) if _finite(p.get('x')))
    observed.extend(float(p['x']) for p in context.get('observed_iob',[]) if _finite(p.get('x')))
    if not observed:return []
    end=min(end,max(observed))
    if end<=start:return []

    groups={}
    for item in context.get('timelines',{}).get('mode',[]):
        x=_stamp(item.get('x',item.get('time')))
        if x is not None:groups.setdefault(x,[]).append(item)
    mode_xs=sorted(groups)
    if not mode_xs:return []
    clocks=sorted(set(float(c['x']) for c in context.get('clock_changes',[]) if _finite(c.get('x'))))
    # Some producers provide clock events only in the plot data; retain barriers
    # from either source without adding any new data query.
    clocks=sorted(set(clocks+[float(c['x']) for c in data.get('clock_changes',[]) if _finite(c.get('x'))]))
    ambiguous=[]
    for pair in context.get('ambiguous_clock_ranges',[]):
        if len(pair)==2 and all(_finite(v) for v in pair):
            a,b=sorted(map(float,pair))
            if a<b:ambiguous.append((a,b))

    cuts={start,end}
    cuts.update(x for x in mode_xs if start<x<end)
    cuts.update(x for x in clocks if start<x<end)
    for a,b in ambiguous:
        if start<a<end:cuts.add(a)
        if start<b<end:cuts.add(b)
    cuts=sorted(cuts);segments=[]
    for a,b in zip(cuts,cuts[1:]):
        if b<=a:continue
        index=bisect_right(mode_xs,a)-1
        if index<0:continue
        observed_at=mode_xs[index];items=groups[observed_at]
        values={item.get('value') for item in items}
        clock_index=bisect_right(clocks,a)-1
        clock=clocks[clock_index] if clock_index>=0 else float('-inf')
        reason=None
        if any(lo<=a<hi for lo,hi in ambiguous):reason='ambiguous_clock_interval'
        elif observed_at<=clock:reason='clock_barrier'
        elif len(values)!=1:reason='ambiguous_same_wall_time'
        elif next(iter(values)) not in LABELS or next(iter(values))=='unknown':reason='unconfirmed_mode'
        mode='unknown' if reason else next(iter(values))
        first=items[-1]
        next_mode=mode_xs[index+1] if index+1<len(mode_xs) else None
        confirmed_end=reason is None and next_mode is not None and abs(b-next_mode)<1e-6
        result={
            'start':a,'end':b,'mode':mode,'label':LABELS[mode],
            'source':first.get('source') or 'Observación de modo API',
            'source_id':first.get('id'),'observed_start':observed_at,
            'uncertain':reason is not None,'reason':reason,
            'clipped_start':a>observed_at,'clipped_end':not confirmed_end,
            'confirmed_end':confirmed_end,
        }
        # Extra cut points (for example the end of an unrelated clock interval)
        # should not turn one continuous mode into many tiny visual chips.
        if segments and all(segments[-1].get(k)==result.get(k) for k in ('mode','source_id','uncertain','reason')) and segments[-1]['end']==a:
            segments[-1]['end']=b
            segments[-1]['clipped_end']=result['clipped_end']
            segments[-1]['confirmed_end']=result['confirmed_end']
        else:segments.append(result)
    return segments
