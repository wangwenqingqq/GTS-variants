#!/usr/bin/env python3
"""Derive tails and nested maintenance/memory/CPU inventories from formal rows."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'region_exec_20261008'))
from audit_closure import read,sha


def summarize(root):
    rows=read(root/'FORMAL_ROWS.json'); assert len(rows)==30
    admitted=read(root/'FORMAL_TIMER.json')['tails_admitted']
    result=dict(formal_rows_raw_sha256=sha(root/'FORMAL_ROWS.json'),tails_admitted=admitted,
                scope='Per-process raw values and across-six-process medians; no pooled percentiles or new timing',
                accounting='Rebuild/refresh/stage intervals are nested in trace or setup, never added again',modes={})
    for mode in read(root/'REGISTERED.json')['modes']:
        selected=[x for x in rows if x['mode']==mode];assert len(selected)==6
        getters=dict(setup_ms=lambda x:x['region']['setup_ms'],
                     context_ms=lambda x:x['region']['context_ms'],
                     cpu_user_s=lambda x:x['summary']['cpu_user_s'],
                     cpu_system_s=lambda x:x['summary']['cpu_system_s'],
                     cpu_total_s=lambda x:x['summary']['cpu_user_s']+x['summary']['cpu_system_s'],
                     sampled_device_peak_bytes=lambda x:x['summary']['sampled_device_peak_bytes'],
                     region_peak_owned_bytes=lambda x:x['region']['peak_owned_bytes'],
                     region_allocations=lambda x:x['region']['allocations'],
                     region_allocated_bytes=lambda x:x['region']['allocated_bytes'],
                     region_transferred_bytes=lambda x:x['region']['transferred_bytes'],
                     rebuild_refresh_sum_ms=lambda x:sum(r['ms'] for r in x['region']['refresh_rows'][1:]),
                     initial_refresh_ms=lambda x:x['region']['refresh_rows'][0]['ms'])
        if admitted:
            for operation in ('query','insert','delete','rebuild'):
                for metric in ('p99','sum'):
                    getters[operation+'_'+metric+'_ms']=lambda x,o=operation,m=metric:x['summary']['latency_ms'][o][m]
            names={s['name'] for x in selected for s in x['summary']['stages']}
            for name in sorted(names):
                getters['stage_'+name+'_ms']=lambda x,n=name:next(s['inclusive_host_ms'] for s in x['summary']['stages'] if s['name']==n)
        result['modes'][mode]={key:dict(raw=[getter(x) for x in selected],
                                             median=float(np.median([getter(x) for x in selected])))
                              for key,getter in getters.items()}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--raw',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
    a.output.write_text(json.dumps(summarize(a.raw),indent=2)+'\n')
