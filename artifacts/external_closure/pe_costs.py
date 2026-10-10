#!/usr/bin/env python3
"""Reuse admitted raw process records; never add medians or manufacture a new timer."""
import json,statistics
from pathlib import Path
from qualify import cpu
HERE=Path(__file__).resolve().parent

def collect():
    source=HERE/'evidence/RTP_RESULTS.json';j=json.loads(source.read_text());rows=[r for r in j['rows'] if r['mode']=='P'];assert len(rows)==6
    items=[]
    for i,s in enumerate(rows[0]['inclusive_stages']):
        values=[r['inclusive_stages'][i]['inclusive_host_ms'] for r in rows]
        items.append(dict(name=s['name'],calls=[r['inclusive_stages'][i]['calls'] for r in rows],per_process_ms=values,median_ms=statistics.median(values),median_fraction_of_own_trace=statistics.median(v/r['trace_ms'] for v,r in zip(values,rows))))
    for name,get in [('safe_refit_update',lambda r:sum(r['numeric_refit']['refresh_ms'][1:])),('PAR_plan_update',lambda r:sum(s['ms'] for s in r['parallel_refresh'][1:]))]:
        values=[get(r) for r in rows];items.append(dict(name=name,calls=[2]*6,per_process_ms=values,median_ms=statistics.median(values),median_fraction_of_own_trace=statistics.median(v/r['trace_ms'] for v,r in zip(values,rows))))
    return dict(source_sha256=cpu.sha(source),labels=[r['label'] for r in rows],trace_ms=[r['trace_ms'] for r in rows],stages=items,scope='inclusive existing per-process Host intervals; overlaps, not independent GPU times or removable-cost estimates',radius_upper_calls='unknown; source confirms one per active parent CTA',distinct_radius_dimension_pairs=1,multiplications_per_radius_call=963)

if __name__=='__main__':
    print(json.dumps(collect(),indent=2))
