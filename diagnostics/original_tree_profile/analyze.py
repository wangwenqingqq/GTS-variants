#!/usr/bin/env python3
"""Summarize clean paired CPU/wall observations and separate diagnostic traces."""
import argparse
from collections import Counter,defaultdict
import json
import math
from pathlib import Path
import sqlite3
import statistics as st


def paired(root):
    out={}
    for kind,phase in [('range','query.range'),('knn','query.knn'),('update','update.total')]:
        pairs=[]
        for i in range(6):
            a=root/'runs'/f'pair{i}_gts_{kind}_b0/receipt.json';b=root/'runs'/f'pair{i}_gts_{kind}_b1/receipt.json'
            if not a.exists() or not b.exists():continue
            ds=[json.loads(p.read_text()) for p in [a,b]]
            assert all(d['exit_code']==0 and d['validation']['pass'] and d['post_gpu_clear'] for d in ds)
            pairs.append([d['phases'][phase] for d in ds])
        if not pairs:continue
        item={'pairs':len(pairs),'phase':phase,'scope':'clean phase timers; blocking/default ratios; no profiler durations'}
        for metric in ['wall_s','main_thread_cpu_s']:
            av=[x[0][metric] for x in pairs];bv=[x[1][metric] for x in pairs]
            logs=[math.log(b/a) for a,b in zip(av,bv)]
            assert len(logs)==6
            mean=st.mean(logs);half=2.57058183661474*st.stdev(logs)/math.sqrt(6)
            item[metric]={'default_median_ms':1000*st.median(av),'blocking_median_ms':1000*st.median(bv),
                'geometric_ratio':math.exp(mean),'paired_log_t_95ci':[math.exp(mean-half),math.exp(mean+half)],
                'blocking_lower_pairs':sum(b<a for a,b in zip(av,bv)),'default_samples_s':av,'blocking_samples_s':bv}
        out[kind]=item
    return out


def trace(path):
    db=sqlite3.connect(path);db.row_factory=sqlite3.Row
    tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    names=dict(db.execute('select id,value from StringIds'))
    copy_names={r[0]:r[2] for r in db.execute('select * from ENUM_CUDA_MEMCPY_OPER')}
    groups=defaultdict(list)
    for r in db.execute('select * from NVTX_EVENTS where end is not null'):
        name=r['text'] or names.get(r['textId'],'')
        if name: groups[name].append((r['start'],r['end']))
    api=list(db.execute('select * from CUPTI_ACTIVITY_KIND_RUNTIME'))
    kernels=list(db.execute('select * from CUPTI_ACTIVITY_KIND_KERNEL'))
    copies=list(db.execute('select * from CUPTI_ACTIVITY_KIND_MEMCPY')) if 'CUPTI_ACTIVITY_KIND_MEMCPY' in tables else []
    memset=list(db.execute('select * from CUPTI_ACTIVITY_KIND_MEMSET')) if 'CUPTI_ACTIVITY_KIND_MEMSET' in tables else []
    cpu_faults=list(db.execute('select * from CUDA_UM_CPU_PAGE_FAULT_EVENTS')) if 'CUDA_UM_CPU_PAGE_FAULT_EVENTS' in tables else []
    gpu_faults=list(db.execute('select * from CUDA_UM_GPU_PAGE_FAULT_EVENTS')) if 'CUDA_UM_GPU_PAGE_FAULT_EVENTS' in tables else []
    out={}
    for name,ranges in groups.items():
        apis=defaultdict(lambda:{'calls':0,'inclusive_ms':0});ks=defaultdict(lambda:{'calls':0,'ms':0})
        mem=defaultdict(lambda:{'calls':0,'bytes':0,'ms':0});disjoint=Counter();cf=gf=0
        for lo,hi in ranges:
            edges=defaultdict(Counter);edges[lo];edges[hi]
            for r in api:
                if lo<=r['start']<hi:
                    a=apis[names[r['nameId']]];a['calls']+=1;a['inclusive_ms']+=(r['end']-r['start'])/1e6
            for r in kernels:
                a,b=max(lo,r['start']),min(hi,r['end'])
                if a<b:
                    k=ks[names[r['shortName']]];k['calls']+=1;k['ms']+=(b-a)/1e6
                    edges[a]['kernel']+=1;edges[b]['kernel']-=1
            for rows,label in [(copies,'copy'),(memset,'memset')]:
                for r in rows:
                    a,b=max(lo,r['start']),min(hi,r['end'])
                    if a<b:
                        key=copy_names[r['copyKind']] if label=='copy' else 'Device memset'
                        m=mem[key];m['calls']+=1;m['bytes']+=r['bytes'];m['ms']+=(b-a)/1e6
                        edges[a][label]+=1;edges[b][label]-=1
            cf+=sum(lo<=r['start']<hi for r in cpu_faults)
            gf+=sum(r['numberOfPageFaults'] for r in gpu_faults if lo<=r['start']<hi)
            last=lo;active=Counter()
            for t,change in sorted(edges.items()):
                cats=[k for k,v in active.items() if v>0]
                cat='gap' if not cats else cats[0] if len(cats)==1 else 'overlap'
                disjoint[cat]+=(t-last)/1e6;active.update(change);last=t
        duration=sum(b-a for a,b in ranges)/1e6
        assert abs(sum(disjoint.values())-duration)<1e-5
        out[name]={'ranges':len(ranges),'profile_wall_ms':duration,'cuda_api':dict(apis),'kernels':dict(ks),
            'memory':dict(mem),'cpu_um_fault_events':cf,'gpu_um_fault_count':gf,'disjoint_timeline_ms':dict(disjoint)}
    return {'phases':out,'um_cpu_table_present':'CUDA_UM_CPU_PAGE_FAULT_EVENTS' in tables,
        'um_gpu_table_present':'CUDA_UM_GPU_PAGE_FAULT_EVENTS' in tables,
        'warning':'Nested phases overlap. CUDA API duration overlaps GPU work and is NOT extra CPU compute time. Gaps are unattributed, not pure CPU overhead. Trace costs are not clean latency.'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path)
    a=ap.parse_args();root=a.root
    profiles={p.parent.name:trace(p) for p in sorted((root/'runs').glob('profile*/trace.sqlite'))}
    result={'paired':paired(root),'profiles':profiles}
    (root/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['paired'],indent=2))
    for name,d in profiles.items():
        print('\nPROFILE',name)
        for phase,v in d['phases'].items():
            if phase.startswith(('query.','update.')) or phase=='index.node_allocations':
                top=sorted(v['cuda_api'].items(),key=lambda x:x[1]['inclusive_ms'],reverse=True)[:6]
                kernels=sorted(v['kernels'].items(),key=lambda x:x[1]['ms'],reverse=True)[:5]
                print(phase, v['profile_wall_ms'],'API',top,'kernels',kernels,'memory',v['memory'],'UM faults',v['cpu_um_fault_events'],v['gpu_um_fault_count'])


if __name__=='__main__':main()
