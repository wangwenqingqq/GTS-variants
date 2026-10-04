#!/usr/bin/env python3
"""Fresh paired observer-cost controls, including rejected native outputs."""
import argparse
import csv
import json
import math
from pathlib import Path
import random
import shutil
import subprocess
from campaign10k import ROOT,BASE,commands,common,invoke,save,sha,audit_output
from qualification import native_ivf

def bootstrap_upper(ratios):
    rng=random.Random(2026100441);logs=list(map(math.log,ratios))
    means=sorted(math.exp(sum(rng.choice(logs) for _ in logs)/len(logs)) for _ in range(10000))
    return math.exp(sum(logs)/len(logs)),means[9750]

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--data-root',type=Path,required=True);p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);a=p.parse_args()
    dest=ROOT/'hook_control';dest.mkdir(exist_ok=True)
    for name in ('opt_knn_bench.cu','gts_bench_p7.cu','knn_cutoff.cuh','knn_select.cuh','knn_verify.cuh','native_knn.py'):
        shutil.copy2(ROOT/name,dest/name)
    (dest/'query_trace.hpp').write_text('#pragma once\n#include <string>\nstruct QueryTrace {explicit QueryTrace(std::string){} void begin(){} void sample(int,int){} void finish(double){} };\n')
    (dest/'query_trace.py').write_text('class QueryTrace:\n    def __init__(self,out):pass\n    def begin(self):pass\n    def sample(self,q,total):pass\n    def finish(self,total_ms):pass\n')
    path=dest/'native_knn.py';text=path.read_text()
    needle='from qualification import native_ivf,check_output'
    assert text.count(needle)==1
    path.write_text(text.replace(needle,'import sys\nsys.path.append(str(Path(__file__).resolve().parent.parent))\n'+needle))
    for path in ROOT.glob('*.index'):
        link=dest/path.name
        if not link.exists():link.symlink_to(path)
    for original in (False,True):
        name='gts_bench_p7' if original else 'opt_knn_bench'
        build=['/usr/local/cuda/bin/nvcc','-O3','-std=c++17','-arch=sm_120','-lineinfo']
        build+=['-I'+str(BASE/'gts/adapted/include')] if original else ['--fmad=false']
        build+=[dest/(name+'.cu'),'-o',dest/name]
        with (dest/(name+'.BUILD.log')).open('w') as log:subprocess.run(list(map(str,build)),stdout=log,stderr=subprocess.STDOUT,check=True)
    refs={d:{pool:json.loads((ROOT/f'oracle_{d}_{pool}.json').read_text()) for pool in ('dev1024','bulkdev10000')} for d in ('GIST','Deep')}
    # Fast Deep paths bound relative observer cost; original GIST and the
    # rejected GIST Flat path are explicit bridge controls. No final inputs.
    cases=[('GIST','GTS_ORIG',b,'diagnostic32') for b in (1,32)]
    cases += [('Deep',m,b,'dev1024') for m in ('O_BOUND','O_MASK') for b in (1,32)]
    cases += [('Deep','O_FULL',32,'dev1024'),('GIST','O_MASK',32,'dev1024'),('GIST','FAISS_FLAT',32,'dev1024')]
    cases += [('Deep',m,b,'bulkdev10000' if b==10000 else 'dev1024') for m in ('FAISS_FLAT','IVF_ALL','CAGRA') for b in (1,32,10000)]
    registration={'cases':cases,'pairs_each':6,'alternating_directions_each':3,'bootstrap_seed':2026100441,
                  'material_limit_ratio':1.03,'admission':'all output hashes identical; upper95 paired on/off ratio <=1.03 in each case',
                  'quality_rejection':'reported; does not stop observer-cost collection',
                  'sources':{p.name:sha(p) for p in dest.iterdir() if p.suffix in ('.cu','.cuh','.hpp','.py')},
                  'off_binaries':{n:sha(dest/n) for n in ('gts_bench_p7','opt_knn_bench')}}
    prereg=ROOT/'HOOK_CONTROL_REGISTERED.json'
    if prereg.exists():assert json.loads(prereg.read_text())==json.loads(json.dumps(registration))
    else:save(prereg,registration)
    sources={d:native_ivf.load_data(a.data_root/f'{d}/1000000/fixtures/data.f32bin') for d in ('GIST','Deep')}
    rows=[];summaries=[]
    for case_no,(d,m,b,pool) in enumerate(cases):
        ref=refs[d]['dev1024' if pool=='diagnostic32' else pool]
        if pool=='diagnostic32':ref={**ref,'Q':32,'records':ref['records'][:32]}
        qs=ROOT/f'fixtures/{d}_{pool}.qid'
        if not qs.exists():qs.write_text(str(ref['Q'])+'\n'+''.join(f'{r["qid"]}\n' for r in ref['records']))
        reference=dest/f'{d}_{pool}.reference.json'
        if not reference.exists():save(reference,ref)
        ratios=[];hashes_identical=True
        for round_no in range(1,7):
            pair=[]
            for variant in (('on','off') if round_no%2 else ('off','on')):
                label=f'hook_c{case_no}_r{round_no}_{variant}';out=dest/label
                c={'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {'itopk_size':1024,'search_width':4} if m=='CAGRA' else {}
                cmd=commands(a,d,m,8,b,qs,out,c)
                if variant=='off':
                    if m in ('GTS_ORIG','O_BOUND','O_MASK','O_FULL'):cmd[0]=dest/('gts_bench_p7' if m=='GTS_ORIG' else 'opt_knn_bench')
                    else:cmd[1]=dest/'native_knn.py'
                receipt=invoke(a,label,cmd,identity_files=[reference])
                meta=json.loads(Path(str(out)+'.json').read_text()) if m!='GTS_ORIG' else next(csv.DictReader(Path(str(out)+'.csv').read_text().splitlines()))
                quality=audit_output(str(out)+'.bin',sources[d],ref,8)
                row={'label':label,'case':case_no,'round':round_no,'dataset':d,'method':m,'B':b,'Q':ref['Q'],'pool':pool,
                     'variant':variant,'pass_ms':float(meta['pass_ms'] if m!='GTS_ORIG' else meta['total_ms']),
                     'quality':quality,'result_sha256':sha(str(out)+'.bin'),'receipt':receipt}
                rows.append(row);pair.append(row);save(ROOT/'HOOK_CONTROL.json',rows)
            same=pair[0]['result_sha256']==pair[1]['result_sha256'];hashes_identical &= same
            by={r['variant']:r for r in pair};ratios.append(by['on']['pass_ms']/by['off']['pass_ms'])
        point,upper=bootstrap_upper(ratios)
        summaries.append({'case':case_no,'dataset':d,'method':m,'B':b,'Q':ref['Q'],'paired_ratios':ratios,
                          'on_off_geomean':point,'upper95':upper,'output_hashes_identical':hashes_identical,
                          'timer_admitted':hashes_identical and upper<=1.03})
        save(ROOT/'HOOK_CONTROL_SUMMARY.json',summaries)
        print(f'HOOK {case_no} {d}/{m}/B{b}/Q{ref["Q"]}: ratio {point:.6f} upper95 {upper:.6f} hashes={hashes_identical}',flush=True)
    result={'state':'collection_complete','processes':len(rows),'cases':len(cases),'summary':summaries,
            'observer_admitted':all(s['timer_admitted'] for s in summaries),'rows_sha256':sha(ROOT/'HOOK_CONTROL.json'),
            'registration_sha256':sha(prereg),'scope':'representative fast B1/B32/bulk and original adapter; actual Host-ready boundaries; no final quality/timing inputs'}
    save(ROOT/'HOOK_CONTROL_COMPLETE.json',result)
    if result['observer_admitted']:save(ROOT/'HOOK_CONTROL_ADMITTED.json',result)

if __name__=='__main__':main()
