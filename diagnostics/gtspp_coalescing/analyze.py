#!/usr/bin/env python3
"""Same-campaign paired query evidence, sustained batches and scoped profilers."""
import argparse
from collections import defaultdict
import csv
import importlib.util
import json
import math
from pathlib import Path
import statistics as st
HERE=Path(__file__).resolve().parent

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
stats=module('stats',HERE.parent/'tc_leaf_probe/analyze.py')
timeline=module('timeline',HERE.parent/'query_breakdown/analyze.py')
ncu=module('ncu',HERE.parent/'query_breakdown/ncu_privileged/analyze.py')

def observations(path):
    obs={};stages=defaultdict(dict);batch=None;flags=None
    for l in path.read_text().splitlines():
        a=l.split(',')
        if a[0]=='policy':assert a[1]=='D';flags=int(a[2]);assert flags&7==0
        elif a[0]=='sample':obs[int(a[1])]=list(map(float,a[2:]))
        elif a[0]=='stage':stages[int(a[1])][a[2]]=(int(a[3]),float(a[4]),float(a[5]))
        elif a[0]=='batch':assert a[1]=='64';batch=list(map(float,a[2:]))
    assert flags is not None
    return obs,stages,batch,flags

def paired(a,b):
    assert len(a)==len(b) and len(a)>=3 and all(v>0 for v in a+b)
    logs=[math.log(x/y) for x,y in zip(a,b)]
    return {'paired_geomean_A_over_B':math.exp(st.mean(logs)),'ci95':stats.interval(logs),'marginal_ratio_of_pair_observations':st.median(a)/st.median(b),'B_process_wins':sum(x>0 for x in logs),'pairs':[{'pair':i,'order':'AB' if i%2==0 else 'BA','A':a[i],'B':b[i],'ratio':a[i]/b[i]} for i in range(len(a))], 'order_ratio':{o:math.exp(st.mean(logs[i] for i in range(len(a)) if ('AB' if i%2==0 else 'BA')==o)) for o in ['AB','BA']}}

def analyze(root,out):
    out.mkdir(exist_ok=False);p=json.loads((root/'logs/provenance.json').read_text())
    e={'experiment':'gtspp_20260923_aggregation_coalescing','scope':'Warm complete GTSPP range dispatch to CPU counts; unchanged default wait; not a whole-process/build/update claim','provenance':p,'runs':{},'cases':{},'sustained':{},'traces':{},'ncu':{},'raw_files':{},'delivery_source_sha256':{name:stats.sha(HERE/name) for name in ['CONTRACT.md','prepare.py','driver.cu','aggregate_block.cuh','run.py','analyze.py','test_prepare.py','test_analysis.py','README.md']}}
    for v in 'AB':assert p['binaries'][v]==stats.sha(root/'bin'/v)
    for run in sorted((root/'runs').iterdir()):
        if not run.is_dir():continue
        r=json.loads((run/'receipt.json').read_text());assert r['exit_code']==0 and r['correct'] and r['post_clear']
        expected=p['binaries']['preflightA' if run.name.startswith('pre_') else r['variant']];assert r['binary_sha256']==expected
        e['runs'][run.name]={k:r[k] for k in ['exit_code','correct','post_clear','binary_sha256','variant','n','q','r','mode','tool','wall_s']}
        o,s,b,f=observations(run/'stdout.log');e['runs'][run.name]['observed_device_flags']=f
        if r['mode']=='stress':assert len(o)==64
        e['runs'][run.name]['sanitizer_summaries']=[l for l in (run/'stderr.log').read_text().splitlines() if 'SUMMARY:' in l]
        for file in run.iterdir():
            if file.is_file():e['raw_files'][str(file.relative_to(root))]={'bytes':file.stat().st_size,'sha256':stats.sha(file)}
        if r['tool']=='nsys':e['traces'][run.name]=timeline.trace(run/'trace.sqlite')
    with (out/'samples.csv').open('w',newline='') as f,(out/'stages.csv').open('w',newline='') as sf:
        w=csv.writer(f,lineterminator='\n');w.writerow(['q','radius','pair','order','variant','sample','wall_s','thread_cpu_s','process_cpu_s','residual_s'])
        sw=csv.writer(sf,lineterminator='\n');sw.writerow(['q','radius','pair','order','variant','sample','stage','calls','wall_s','thread_cpu_s','wall_fraction'])
        for q in [32,128]:
            for radius in [300,500]:
                data={v:[] for v in 'AB'};phases={v:defaultdict(list) for v in 'AB'};med={v:[] for v in 'AB'};cpu={v:[] for v in 'AB'}
                for pair in range(6):
                    order='AB' if pair%2==0 else 'BA'
                    for v in order:
                        name=f'timing_{q}_{radius}_{pair}_{v}';o,s,b,flags=observations(root/'runs'/name/'stdout.log');assert sorted(o)==list(range(8)) and all(len(s[i])==8 for i in o)
                        for i,(wall,thread,process) in o.items():
                            residual=wall-sum(x[1] for x in s[i].values());assert residual>=-1e-6
                            w.writerow([q,radius,pair,order,v,i,wall,thread,process,residual]);data[v].append({'wall_ms':wall*1000,'thread_cpu_ms':thread*1000,'process_cpu_ms':process*1000,'thread_one_core_fraction':thread/wall,'residual_ms':residual*1000})
                            for name,(calls,pw,pc) in s[i].items():sw.writerow([q,radius,pair,order,v,i,name,calls,pw,pc,pw/wall]);phases[v][name].append({'wall_ms':pw*1000,'thread_cpu_ms':pc*1000,'wall_fraction':pw/wall})
                        med[v].append(st.median(x[0] for x in o.values()));cpu[v].append(st.median(x[1] for x in o.values()))
                c={'timing':{v:{k:stats.dist([x[k] for x in data[v]]) for k in data[v][0]} for v in 'AB'},'stages':{v:{name:{k:stats.dist([x[k] for x in values]) for k in values[0]} for name,values in phases[v].items()} for v in 'AB'},'wall_ratio':paired(med['A'],med['B']),'cpu_ratio':paired(cpu['A'],cpu['B'])}
                c['wall_ratio']['sample_marginal_A_over_B']=c['timing']['A']['wall_ms']['median']/c['timing']['B']['wall_ms']['median']
                c['wall_ratio']['pair_observation']='process median of eight retained queries'
                c['short_query_gate']=c['wall_ratio']['ci95'][0]>1.02 and c['wall_ratio']['B_process_wins']>=5;e['cases'][f'q{q}_r{radius}']=c
    for q,radius in [(32,300),(128,500)]:
        vals={v:[] for v in 'AB'};cpu={v:[] for v in 'AB'}
        for pair in range(3):
            for v in ('AB' if pair%2==0 else 'BA'):
                _,_,batch,_=observations(root/'runs'/f'sustained_{q}_{radius}_{pair}_{v}'/'stdout.log');assert batch is not None
                vals[v].append(batch[0]);cpu[v].append(batch[1])
        e['sustained'][f'q{q}_r{radius}']={'wall_ratio':paired(vals['A'],vals['B']),'cpu_ratio':paired(cpu['A'],cpu['B']),'batch_64_wall_ms':{v:stats.dist([x*1000 for x in vals[v]]) for v in 'AB'},'per_query_wall_ms':{v:stats.dist([x*1000/64 for x in vals[v]]) for v in 'AB'},'scope':'64 complete queries; includes retaining CPU counts in a preallocated history; all checks outside batch timer'}
    with (out/'ncu_metrics.csv').open('w',newline='') as f,(out/'instruction_ledger.csv').open('w',newline='') as lf:
        w=csv.writer(f,lineterminator='\n');w.writerow(['variant','metric','unit','value']);lw=csv.writer(lf,lineterminator='\n');lw.writerow(['variant','function','opcode']+list(ncu.COUNTS))
        for v in 'AB':
            run=root/'runs'/f'ncu_{v}';units,rows=ncu.raw_metrics(run/'raw.csv');assert len(rows)==1;d=rows[0];assert d['Kernel Name'].startswith('mergeResRnn') and units['gpu__time_duration.sum'] in ['ns','nsecond']
            e['ncu'][v]={'kernel':d['Kernel Name'],'grid':d['Grid Size'],'block':d['Block Size'],'source':[]}
            for key,value in d.items():
                if key.startswith(ncu.PREFIXES) and key!='launch__function_pcs' and not key.endswith('_id'):w.writerow([v,key,units[key],value])
            for g in ncu.source_groups(run/'source.csv'):
                s=ncu.summarize_group(g)
                for op,counts in s.pop('opcodes').items():
                    if any(counts.values()):lw.writerow([v,s['function'],op]+[counts[k] for k in ncu.COUNTS])
                e['ncu'][v]['source'].append(s)
            assert sum(s['totals']['warp_instructions'] for s in e['ncu'][v]['source'])==int(d['smsp__inst_executed.sum'])
    for file in (root/'logs').iterdir():
        if file.is_file():e['raw_files'][str(file.relative_to(root))]={'bytes':file.stat().st_size,'sha256':stats.sha(file)}
    e['fixtures']={f'n{n}':json.loads((root/f'fixtures/n{n}/manifest.json').read_text()) for n in [2000,65536]}
    e['decision']={'all_short_gates':all(c['short_query_gate'] for c in e['cases'].values()),'sustained_nonregression':all(c['wall_ratio']['ci95'][0]>1 for c in e['sustained'].values()),'scope':'bounded count-only warm range-query prototype; not production/all metrics'}
    (out/'EVIDENCE.json').write_text(json.dumps(e,indent=2)+'\n')
    for name,c in e['cases'].items():print(name,{v:c['timing'][v]['wall_ms']['median'] for v in 'AB'},c['wall_ratio']['paired_geomean_A_over_B'],c['wall_ratio']['ci95'])
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();analyze(a.root,a.out)
