#!/usr/bin/env python3
"""Portable timing and scoped NSYS attribution; never add overlapping waits."""
import argparse
from collections import defaultdict
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics as st
HERE=Path(__file__).resolve().parent
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
stats=module('stats',HERE.parent/'tc_leaf_probe/analyze.py')
timeline=module('timeline',HERE.parent/'original_flow_20260923/analyze.py')

def trace(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")};names=dict(db.execute('SELECT id,value FROM StringIds'))
    def rows(table):return list(db.execute('SELECT * FROM '+table)) if table in tables else []
    nvtx=rows('NVTX_EVENTS')
    def text(r):return r['text'] or names.get(r['textId'],'')
    queries=sorted([r for r in nvtx if text(r).startswith('measured.query.') and r['end']],key=lambda r:r['start']);assert len(queries)==3
    kernels=rows('CUPTI_ACTIVITY_KIND_KERNEL');apis=rows('CUPTI_ACTIVITY_KIND_RUNTIME');copies=rows('CUPTI_ACTIVITY_KIND_MEMCPY');sets=rows('CUPTI_ACTIVITY_KIND_MEMSET')
    copy_names={r[0]:r[2] for r in db.execute('SELECT * FROM ENUM_CUDA_MEMCPY_OPER')}
    result=[]
    for qr in queries:
        lo,hi=qr['start'],qr['end'];ks=[r for r in kernels if lo<=r['start']<hi];api=[r for r in apis if lo<=r['start']<hi];cs=[r for r in copies if lo<=r['start']<hi];ss=[r for r in sets if lo<=r['start']<hi]
        ranges=[r for r in nvtx if text(r).startswith('stage.') and lo<=r['start']<hi and r['end']]
        stage=defaultdict(lambda:{'host_ms':0,'gpu_union_ms':0,'kernel_union_ms':0})
        for r in ranges:
            s=stage[text(r)];s['host_ms']+=(r['end']-r['start'])/1e6
            s['gpu_union_ms']+=timeline.length(timeline.clipped(ks+cs+ss,r['start'],r['end']))/1e6
            s['kernel_union_ms']+=timeline.length(timeline.clipped(ks,r['start'],r['end']))/1e6
        kd=defaultdict(lambda:{'calls':0,'ms':0,'grid_blocks':[],'block_threads':[],'registers':[]})
        for r in ks:
            k=kd[names[r['shortName']]];k['calls']+=1;k['ms']+=(r['end']-r['start'])/1e6
            for key,value in [('grid_blocks',r['gridX']*r['gridY']*r['gridZ']),('block_threads',r['blockX']*r['blockY']*r['blockZ']),('registers',r['registersPerThread'])]:k[key].append(value)
        ad=defaultdict(lambda:{'calls':0,'inclusive_ms':0});by_stage=defaultdict(lambda:defaultdict(lambda:{'calls':0,'inclusive_ms':0}))
        for r in api:
            owners=[s for s in ranges if s['globalTid']==r['globalTid'] and s['start']<=r['start']<s['end']];assert len(owners)<=1
            owner=text(owners[0]) if owners else 'unattributed'
            for d in [ad[names[r['nameId']]],by_stage[owner][names[r['nameId']]]]:d['calls']+=1;d['inclusive_ms']+=(r['end']-r['start'])/1e6
        cd=defaultdict(lambda:{'calls':0,'bytes':0,'ms':0})
        for r in cs:d=cd[copy_names[r['copyKind']]];d['calls']+=1;d['bytes']+=r['bytes'];d['ms']+=(r['end']-r['start'])/1e6
        busy=timeline.length(timeline.clipped(ks+cs+ss,lo,hi))/1e6
        result.append({'query':text(qr),'wall_ms':(hi-lo)/1e6,'gpu_union_ms':busy,'no_recorded_gpu_work_ms':(hi-lo)/1e6-busy,'gpu_temporal_fraction':busy/((hi-lo)/1e6),'stages':dict(stage),'kernels':dict(kd),'cuda_api':dict(ad),'cuda_api_by_stage':dict(by_stage),'copies':dict(cd),
                       'cpu_um_fault_events':sum(lo<=r['start']<hi for r in rows('CUDA_UM_CPU_PAGE_FAULT_EVENTS')) if 'CUDA_UM_CPU_PAGE_FAULT_EVENTS' in tables else None,
                       'gpu_um_fault_count':sum(r['numberOfPageFaults'] for r in rows('CUDA_UM_GPU_PAGE_FAULT_EVENTS') if lo<=r['start']<hi) if 'CUDA_UM_GPU_PAGE_FAULT_EVENTS' in tables else None})
    db.close();return {'scope':'Three measured NVTX query ranges only; excludes setup/warmup. Profiler-only diagnostic, not clean latency. API durations overlap GPU work; temporal coverage is not compute throughput. Missing UM counters mean uncollected, not zero. API stage attribution uses entry timestamp inside a same-thread NVTX stage; unmatched calls remain unattributed. GPU stage times use clipped interval union, not causal ownership.','queries':result}

def analyze(root,out):
    out.mkdir(exist_ok=False);e={'scope':'Warm original GTS query dispatch to CPU counts; staged host scopes include existing waits','cases':{},'runs':{},'files':{},'source_sha256':{},'binary_sha256':{b:stats.sha(root/'bin'/b) for b in ['bench3','bench5']}}
    for p in sorted((root/'diagnostics/query_breakdown').iterdir()):
        if p.is_file() and not p.name.startswith('._'):e['source_sha256'][p.name]=stats.sha(p)
    e['fixtures']={p.parent.name:json.loads(p.read_text()) for p in sorted((root/'fixtures').glob('*/manifest.json'))}
    e['generated_manifest_sha256']={f'source{h}':stats.sha(root/f'source{h}/INSTRUMENTED_SHA256.json') for h in [3,5]}
    e['static_functions']={}
    resources=(root/'logs/resources.txt').read_text()
    for part in (root/'logs/bench5.sass').read_text().split('Function : ')[1:]:
        name=part.splitlines()[0].strip()
        if not any(name.startswith(p) for p in ['_Z14dataProcessRnn','_Z14nodeProcessRnn','_Z11mergeResRnn']):continue
        ins=[re.sub(r'/\*.*?\*/','',l).strip() for l in part.splitlines() if re.match(r'\s*/\*[0-9a-f]+\*/',l)]
        resource_line=resources.split('Function '+name+':')[1].splitlines()[1]
        e['static_functions'][name]={'normalized_instruction_sha256':hashlib.sha256(('\n'.join(ins)+'\n').encode()).hexdigest(),'instruction_count':len(ins),'resources':{k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',resource_line)}}
    with (out/'samples.csv').open('w',newline='') as f,(out/'stages.csv').open('w',newline='') as sf:
        w=csv.writer(f,lineterminator='\n');sw=csv.writer(sf,lineterminator='\n');w.writerow(['case','pair','order','policy','sample','wall_s','thread_cpu_s','process_cpu_s','residual_s']);sw.writerow(['case','pair','order','policy','sample','stage','calls','wall_s','thread_cpu_s','wall_fraction'])
        for q in [32,128]:
            for radius in [300,500]:
                case=f'n65536_q{q}_r{radius}';data={p:[] for p in 'DB'};phase={p:defaultdict(list) for p in 'DB'};med={p:[] for p in 'DB'};cpu_med={p:[] for p in 'DB'}
                for pair in range(6):
                    order='DB' if pair%2==0 else 'BD'
                    for policy in order:
                        run=root/'runs'/f'timing_{case}_{pair}_{policy}';r=json.loads((run/'receipt.json').read_text());assert r['exit_code']==0 and r['correct'] and r['post_clear'] and r['binary_sha256']==e['binary_sha256']['bench5']
                        obs={};parts=defaultdict(dict);flags=None
                        for line in (run/'stdout.log').read_text().splitlines():
                            a=line.split(',')
                            if a[0]=='sample':obs[int(a[1])]=list(map(float,a[2:]))
                            elif a[0]=='stage':parts[int(a[1])][a[2]]=(int(a[3]),float(a[4]),float(a[5]))
                            elif a[0]=='policy':assert a[1]==policy;flags=int(a[2])
                        assert flags is not None and flags&7=={'D':0,'B':4}[policy],(policy,flags)
                        e.setdefault('observed_device_flags',{})[run.name]=flags
                        assert sorted(obs)==list(range(8)) and all(len(parts[i])==8 for i in obs)
                        for i,(wall,cpu,process) in obs.items():
                            residual=wall-sum(v[1] for v in parts[i].values());assert residual>=-1e-6
                            w.writerow([case,pair,order,policy,i,wall,cpu,process,residual]);data[policy].append({'wall_ms':wall*1000,'thread_cpu_ms':cpu*1000,'process_cpu_ms':process*1000,'thread_one_core_fraction':cpu/wall,'process_one_core_fraction':process/wall,'residual_ms':residual*1000})
                            for name,(calls,pw,pc) in parts[i].items():
                                sw.writerow([case,pair,order,policy,i,name,calls,pw,pc,pw/wall]);phase[policy][name].append({'wall_ms':pw*1000,'thread_cpu_ms':pc*1000,'wall_fraction':pw/wall})
                        med[policy].append(st.median(o[0] for o in obs.values()))
                        cpu_med[policy].append(st.median(o[1] for o in obs.values()))
                ratio=[med['D'][i]/med['B'][i] for i in range(6)];logs=list(map(math.log,ratio))
                e['cases'][case]={'timing':{p:{k:stats.dist([r[k] for r in data[p]]) for k in data[p][0]} for p in 'DB'},'stages':{p:{name:{k:stats.dist([r[k] for r in v]) for k in v[0]} for name,v in phase[p].items()} for p in 'DB'},'D_over_B':{'paired_geomean':math.exp(st.mean(logs)),'ci95':stats.interval(logs),'marginal':st.median([r['wall_ms'] for r in data['D']])/st.median([r['wall_ms'] for r in data['B']]),'blocking_pair_wins':sum(r>1 for r in ratio),'pairs':[{'pair':i,'order':'DB' if i%2==0 else 'BD','D_ms':med['D'][i]*1000,'B_ms':med['B'][i]*1000,'ratio':ratio[i]} for i in range(6)],'order_ratio':{o:math.exp(st.mean(logs[i] for i in range(6) if ('DB' if i%2==0 else 'BD')==o)) for o in ['DB','BD']}}}
                cpu_logs=[math.log(cpu_med['D'][i]/cpu_med['B'][i]) for i in range(6)]
                e['cases'][case]['thread_cpu_D_over_B']={'paired_geomean':math.exp(st.mean(cpu_logs)),'ci95':stats.interval(cpu_logs),'blocking_pair_wins':sum(v>0 for v in cpu_logs),'pairs':[{'pair':i,'D_ms':cpu_med['D'][i]*1000,'B_ms':cpu_med['B'][i]*1000,'ratio':math.exp(cpu_logs[i])} for i in range(6)],'order_ratio':{o:math.exp(st.mean(cpu_logs[i] for i in range(6) if ('DB' if i%2==0 else 'BD')==o)) for o in ['DB','BD']}}
    for run in sorted((root/'runs').iterdir()):
        if not run.is_dir():continue
        r=json.loads((run/'receipt.json').read_text());e['runs'][run.name]={k:r[k] for k in ['exit_code','binary_sha256','correct','counter_denied','post_clear','wall_s','user_s','system_s']}
        for when in ['before','after']:
            gpu=[v.strip() for v in next(csv.reader([json.loads((run/(when+'.json')).read_text())['gpu'].strip()]))]
            assert gpu[0]=='0'
            e['runs'][run.name][when+'_gpu']={k:gpu[i] for k,i in [('name',2),('driver',3),('memory_used',4),('utilization',5),('pstate',6),('power_draw',7),('graphics_clock',8),('memory_clock',9)]}
        text=(run/'stdout.log').read_text()+(run/'stderr.log').read_text();e['runs'][run.name]['sanitizer_summaries']=[l for l in text.splitlines() if 'SUMMARY:' in l]
        for p in run.iterdir():
            if p.is_file():e['files'][str(p.relative_to(root))]=stats.sha(p)
        if run.name.startswith('profile_'):e.setdefault('traces',{})[run.name]=trace(run/'trace.sqlite')
    for p in (root/'logs').iterdir():
        if p.is_file():e['files'][str(p.relative_to(root))]=stats.sha(p)
    (out/'EVIDENCE.json').write_text(json.dumps(e,indent=2)+'\n')
    for case,c in e['cases'].items():print(case,{p:{'wall_ms':c['timing'][p]['wall_ms']['median'],'cpu_ms':c['timing'][p]['thread_cpu_ms']['median'],'stages':{s:round(v['wall_fraction']['median']*100,2) for s,v in c['stages'][p].items()}} for p in 'DB'})

if __name__=='__main__':
    assert timeline.length([(1,4),(2,5),(8,9)])==5
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();analyze(a.root,a.out)
