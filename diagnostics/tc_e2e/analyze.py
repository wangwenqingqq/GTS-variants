#!/usr/bin/env python3
"""Curate same-round query-to-CPU-count latency; retain every sample/order."""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import statistics as st
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('parent_analysis',HERE.parent/'tc_leaf_probe/analyze.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
ORDERS=['OSTD','TDOS','SODT','DTSO','DSOT','TOSD']
COMPARISONS={'TC_vs_SIMT':('S','T'),'dense_vs_tree_TC':('T','D'),'SIMT_vs_original':('O','S'),'TC_vs_original':('O','T'),'dense_vs_original':('O','D')}

def portable_profile(rows):
    return [{k:('unresolved instruction' if re.fullmatch(r'0x[0-9A-Fa-f]+',v) else v)
             for k,v in row.items() if k not in ['Minimum Virtual Address','Maximum Virtual Address']}
            for row in rows]

def analyze(root,out):
    out.mkdir(parents=True,exist_ok=False)
    result={'scope':'warm query dispatch to CPU counts; resident inputs; excludes index build and one-time setup','batch16_scope':'mean of sixteen separately timed and validated CPU-delivered queries; not uninterrupted throughput','cases':{},'runs':{},'files':{},'source_sha256':{}}
    for p in sorted((root/'diagnostics/tc_e2e').glob('*')):
        if p.is_file() and not p.name.startswith('._'):result['source_sha256'][p.name]=parent.sha(p)
    result['binary_sha256']={name:parent.sha(root/'bin'/name) for name in ['bench3','bench5']}
    result['source_generation_manifest_sha256']={f'source{h}':parent.sha(root/f'source{h}/INSTRUMENTED_SHA256.json') for h in [3,5]}
    result['fixtures']={p.parent.name:json.loads(p.read_text()) for p in sorted((root/'fixtures').glob('*/manifest.json'))}
    with (out/'samples.csv').open('w',newline='') as f:
        wr=csv.writer(f,lineterminator='\n');wr.writerow(['case','process','order','variant','batch','sample','wall_us','thread_cpu_us','event_us'])
        for q in [32,128]:
            for radius in [300,500]:
                case=f'n65536_q{q}_r{radius}';samples={b:{v:[] for v in 'OSTD'} for b in [1,16]};all_cpu={b:{v:[] for v in 'OSTD'} for b in [1,16]};all_event={b:{v:[] for v in 'OSTD'} for b in [1,16]};medians={b:[] for b in [1,16]};phases={}
                for i,order in enumerate(ORDERS):
                    run=root/'runs'/f'timing_{case}_{i}';rec=json.loads((run/'receipt.json').read_text())
                    assert rec['exit_code']==0 and rec['correct'] and rec['post_clear'] and rec['binary_sha256']==result['binary_sha256']['bench5']
                    text=(run/'stdout.log').read_text();assert 'pass' in text.splitlines()
                    vals={b:{v:[] for v in 'OSTD'} for b in [1,16]}
                    actual_order=[]
                    for line in text.splitlines():
                        a=line.split(',')
                        if a[0]=='phase':phases.setdefault(a[1],[]).append(float(a[2]))
                        if a[0]=='sample':
                            v,b,s=a[1],int(a[2]),int(a[3]);wall,cpu,event=map(float,a[4:]);assert v in 'OSTD' and b in [1,16]
                            if v not in actual_order:actual_order.append(v)
                            vals[b][v].append(wall);samples[b][v].append(wall);all_cpu[b][v].append(cpu);all_event[b][v].append(event);wr.writerow([case,i,order,v,b,s,wall,cpu,event])
                    assert ''.join(actual_order)==order
                    for b in [1,16]:
                        assert all(len(vals[b][v])==(20 if b==1 else 5) for v in 'OSTD')
                        medians[b].append({v:st.median(vals[b][v]) for v in 'OSTD'})
                c={'shape':{'n':65536,'q':q,'radius':radius},'phase_ms':{p:parent.dist(v) for p,v in phases.items()},'timing':{},'comparisons':{}}
                for b in [1,16]:
                    c['timing'][str(b)]={v:{'wall_us':parent.dist(samples[b][v]),'thread_cpu_us':parent.dist(all_cpu[b][v]),'event_us':parent.dist(all_event[b][v])} for v in 'OSTD'}
                    for name,(a,z) in COMPARISONS.items():
                        ratios=[m[a]/m[z] for m in medians[b]];logs=list(map(math.log,ratios));geo=math.exp(st.mean(logs));ci=parent.interval(logs)
                        r={'marginal_ratio':st.median(samples[b][a])/st.median(samples[b][z]),'paired_geomean_ratio':geo,'paired_ci95':ci,'arithmetic_mean_ratio':st.mean(ratios),'denominator_process_wins':sum(x>1 for x in ratios),'processes':[{'process':i,'order':ORDERS[i],'numerator_us':medians[b][i][a],'denominator_us':medians[b][i][z],'ratio':ratios[i]} for i in range(6)],'precedence_ratio':{key:math.exp(st.mean(logs[i] for i,o in enumerate(ORDERS) if (o.index(a)<o.index(z))==flag)) for key,flag in [('numerator_first',True),('denominator_first',False)]}}
                        c['comparisons'].setdefault(name,{})[str(b)]=r
                def win(name):
                    r=c['comparisons'][name]['1'];repeat=c['comparisons'][name]['16']
                    return r['paired_geomean_ratio']>1.1 and r['paired_ci95'][0]>1 and r['denominator_process_wins']>=5 and repeat['paired_geomean_ratio']>=1
                c['dense_control_gate']=win('dense_vs_tree_TC')
                c['tree_TC_continuation_gate']=win('TC_vs_SIMT') and c['comparisons']['dense_vs_tree_TC']['1']['paired_geomean_ratio']<=1
                result['cases'][case]=c
    for p in sorted((root/'logs').glob('*')):
        if p.is_file():result['files'][str(p.relative_to(root))]=parent.sha(p)
    for run in sorted((root/'runs').iterdir()):
        if not run.is_dir():continue
        for p in run.iterdir():
            if p.is_file():result['files'][str(p.relative_to(root))]=parent.sha(p)
        rec=json.loads((run/'receipt.json').read_text());row={k:rec[k] for k in ['exit_code','binary_sha256','wall_s','user_s','system_s','post_clear','correct']}
        text=(run/'stdout.log').read_text()+(run/'stderr.log').read_text();row['sanitizer_summaries']=[l for l in text.splitlines() if 'SUMMARY:' in l];result['runs'][run.name]=row
    result['static_sass']={}
    for part in (root/'logs/bench5.sass').read_text().split('Function : ')[1:]:
        name=part.splitlines()[0].strip()
        if not any(name.startswith(p) for p in ['_Z6tensor','_Z4simt','_Z10make_masks','_Z15translate_pairs','_Z14nodeProcessRnn','_Z11mergeResRnn']):continue
        ins=[re.sub(r'/\*.*?\*/','',line).strip() for line in part.splitlines() if re.match(r'\s*/\*[0-9a-f]+\*/',line)]
        result['static_sass'][name]={'normalized_instruction_sha256':hashlib.sha256(('\n'.join(ins)+'\n').encode()).hexdigest(),'instruction_count':len(ins),'hmma':sum('HMMA.' in l for l in ins),'local':sum(bool(re.search(r'\b(?:LDL|STL)\b',l)) for l in ins)}
    for p in sorted((root/'runs/profile_n65536_q128_r500').glob('*_sum.csv')):
        with p.open() as f:result.setdefault('diagnostic_profile',{})[p.stem]=portable_profile(csv.DictReader(f))
    (out/'EVIDENCE.json').write_text(json.dumps(result,indent=2)+'\n')
    for case,c in result['cases'].items():
        print(case,{v:round(c['timing']['1'][v]['wall_us']['median']/1000,4) for v in 'OSTD'},'S/T',round(c['comparisons']['TC_vs_SIMT']['1']['paired_geomean_ratio'],4),'T/D',round(c['comparisons']['dense_vs_tree_TC']['1']['paired_geomean_ratio'],4),'dense_gate',c['dense_control_gate'],'TC_gate',c['tree_TC_continuation_gate'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();analyze(a.root,a.out)
