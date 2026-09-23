#!/usr/bin/env python3
"""Curate portable numeric evidence from immutable run folders (no raw inputs)."""
import argparse
import csv
from collections import Counter
import re
import hashlib
import json
import math
from pathlib import Path
import random
import statistics as st

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quantile(v,p):
    s=sorted(v);x=(len(s)-1)*p;i=int(x);return s[i]*(1-(x-i))+s[min(i+1,len(s)-1)]*(x-i)
def dist(v):return {k:quantile(v,p) for k,p in [('p10',.1),('median',.5),('p90',.9)]}
def interval(logs):
    rng=random.Random(0);draws=[math.exp(st.mean(rng.choices(logs,k=len(logs)))) for _ in range(10000)]
    return [quantile(draws,.025),quantile(draws,.975)]

def analyze(root,out):
    out.mkdir(parents=True,exist_ok=False);result={'scope':'resident leaf-candidate operator; not full GTS','cases':{},'runs':{},'files':{},'source_sha256':{}}
    for p in sorted((root/'diagnostics/tc_leaf_probe').glob('*')):
        if p.is_file():result['source_sha256'][p.name]=sha(p)
    for name in ['probe','export3','export5']:result.setdefault('binary_sha256',{})[name]=sha(root/'bin'/name)
    for p in sorted((root/'logs').glob('*')):
        if p.is_file():result['files']['logs/'+p.name]=sha(p)
    for p in sorted((root/'fixtures').glob('*/manifest.json')):result.setdefault('fixtures',{})[p.parent.name]=json.loads(p.read_text())
    with (out/'samples.csv').open('w',newline='') as f:
        writer=csv.writer(f,lineterminator="\n");writer.writerow(['case','process','order','variant','batch','sample','event_us','host_us'])
        for q in [32,128]:
            for r in [300,500]:
                case=f'n65536_q{q}_r{r}';groups={b:{'A':[],'B':[]} for b in [1,64]};paired={b:[] for b in [1,64]};pm={b:[] for b in [1,64]};hosts={b:{'A':[],'B':[]} for b in [1,64]}
                for i in range(6):
                    run=root/'runs'/f'timing_{case}_{i}';rec=json.loads((run/'receipt.json').read_text());assert rec['exit_code']==0 and rec['post_clear'] and rec['binary_sha256']==result['binary_sha256']['probe']
                    rows=(run/'stdout.log').read_text().splitlines();assert 'pass' in rows and 'correct,full_oracle_native_sparse_A_B_exact' in rows
                    vals={b:{'A':[],'B':[]} for b in [1,64]}
                    for row in rows:
                        a=row.split(',')
                        if a[0]=='shape':shape={'n':int(a[1]),'q':int(a[2]),'radius':int(a[3]),'leaves':int(a[4]),'candidate_pairs':int(a[5]),'useful_distances':int(a[6]),'executed_tiles':int(a[7]),'launched_tiles':int(a[8]),'fill':float(a[9])}
                        if a[0]=='sample':
                            v,b,s=a[1],int(a[2]),int(a[3]);ev,host=map(float,a[4:]);vals[b][v].append(ev);groups[b][v].append(ev);hosts[b][v].append(host);writer.writerow([case,i,'AB' if i%2==0 else 'BA',v,b,s,ev,host])
                    for b in [1,64]:
                        assert all(len(vals[b][v])==(100 if b==1 else 20) for v in ['A','B'])
                        med={v:st.median(vals[b][v]) for v in ['A','B']};ratio=med['A']/med['B'];paired[b].append(math.log(ratio));pm[b].append({'process':i,'order':'AB' if i%2==0 else 'BA',**med,'A_over_B':ratio})
                native=root/'runs'/('extract_'+case)
                count_lines=(native/'cost.txt').read_text().splitlines()
                counts=list(map(int,count_lines[2].split()));assert len(counts)==q
                shape['result_count_sum']=sum(counts);shape['result_fraction']=sum(counts)/(65536*q)
                shape['leaf_size_histogram']=dict(Counter(int(line.split()[1]) for line in (native/'index.txt').read_text().splitlines()))
                shape['candidate_fraction']=shape['useful_distances']/(65536*q)
                shape['derived_hmma_warp_instructions']=16*shape['executed_tiles']
                shape['padded_distance_cells']=256*shape['executed_tiles']
                report={'shape':shape,'timing':{}}
                for b in [1,64]:
                    ratio=math.exp(st.mean(paired[b]));ci=interval(paired[b]);wins=sum(v>0 for v in paired[b])
                    report['timing'][str(b)]={'event_us':{v:dist(groups[b][v]) for v in ['A','B']},'host_us':{v:dist(hosts[b][v]) for v in ['A','B']},'marginal_A_over_B':st.median(groups[b]['A'])/st.median(groups[b]['B']),'paired_geomean_A_over_B':ratio,'paired_ci95':ci,'A_over_B_arithmetic_mean':st.mean(math.exp(v) for v in paired[b]),'B_process_wins':wins,'processes':pm[b],'order_ratio':{order:math.exp(st.mean(paired[b][i] for i in range(6) if ('AB' if i%2==0 else 'BA')==order)) for order in ['AB','BA']}}
                one,sus=report['timing']['1'],report['timing']['64']
                report['continuation_gate']=one['paired_geomean_A_over_B']>1.1 and one['paired_ci95'][0]>1 and one['B_process_wins']>=5 and sus['paired_geomean_A_over_B']>=1
                result['cases'][case]=report
    for run in sorted((root/'runs').iterdir()):
        if not run.is_dir():continue
        for p in run.iterdir():
            if p.is_file():result['files'][str(p.relative_to(root))]=sha(p)
        rec=json.loads((run/'receipt.json').read_text())
        # Raw command/environment/host identity remains only in the private receipt.
        row={k:rec[k] for k in ['exit_code','binary_sha256','wall_s','user_s','system_s','post_clear']}
        text=(run/'stdout.log').read_text()+(run/'stderr.log').read_text()
        row['correct_marker']='correct,full_oracle_native_sparse_A_B_exact' in text
        row['sanitizer_summaries']=[l for l in text.splitlines() if 'SUMMARY:' in l]
        result['runs'][run.name]=row
    sass=(root/'logs/probe.sass').read_text()
    result['static_sass']={}
    for part in sass.split('Function : ')[1:]:
        name=part.splitlines()[0].strip()
        ins=[re.sub(r'/\*.*?\*/','',line).strip() for line in part.splitlines() if re.match(r'\s*/\*[0-9a-f]+\*/',line)]
        result['static_sass'][name]={'normalized_instruction_sha256':hashlib.sha256(('\n'.join(ins)+'\n').encode()).hexdigest(),'instruction_count':len(ins),'hmma':sum('HMMA.' in line for line in ins),'ldl_stl':sum(bool(re.search(r'\b(?:LDL|STL)\b',line)) for line in ins)}
    profile=root/'runs/profile_n65536_q128_r500/trace_cuda_gpu_kern_sum.csv'
    if profile.exists():
        with profile.open() as f:result['profile_kernel_summary']=list(csv.DictReader(f))
    (out/'EVIDENCE.json').write_text(json.dumps(result,indent=2)+'\n')
    for case,x in result['cases'].items():
        t=x['timing']['1'];s=x['timing']['64'];print(case,'fill',x['shape']['fill'],'A/B us',t['event_us']['A']['median'],t['event_us']['B']['median'],'speedup',t['paired_geomean_A_over_B'],'CI',t['paired_ci95'],'sustained',s['paired_geomean_A_over_B'],'gate',x['continuation_gate'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args();analyze(a.root,a.out)
