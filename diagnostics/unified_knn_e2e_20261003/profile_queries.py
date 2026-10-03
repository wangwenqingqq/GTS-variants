#!/usr/bin/env python3
"""Separate query-only traces; no profiler number substitutes formal latency."""
import argparse
import json
from pathlib import Path
import subprocess
from campaign import command,run
from qualification import BASE,native_ivf

ROOT=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--gpu',required=True);p.add_argument('--data-root',type=Path,required=True)
    p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True);a=p.parse_args()
    qids=native_ivf.read_qids(BASE/'fixtures/GIST_dev128.qid')[:32]
    qp=ROOT/'fixtures/GIST_profile32.qid';qp.write_text('32\n'+''.join(f'{q}\n' for q in qids))
    frozen=json.loads((ROOT/'FROZEN_CONFIG.json').read_text())
    points=[x for x in frozen['selected']['GIST_k8_b32'] if x['method']=='CAGRA']
    best=max(points,key=lambda c:max(float(s.split('@')[1]) for s in c['anchors'])) if points else frozen['diagnostic_best']['GIST_k8_b32']['CAGRA']
    rows=[];dest=ROOT/'profiles';dest.mkdir(exist_ok=True)
    for method in ('GTS_ORIG','O_FULL','O_BOUND','O_MASK','FAISS_FLAT','IVF_ALL','CAGRA'):
        config={'nlist':1024,'nprobe':1024} if method=='IVF_ALL' else best['config'] if method=='CAGRA' else {}
        trace=dest/method
        cmd=command(a,'GIST',method,8,32,qp,trace,config)
        args=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--cuda-graph-trace=node','--sample=none','--cpuctxsw=none',
              '--capture-range=nvtx','--nvtx-capture=formal.query_pass','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
              '--capture-range-end=stop','--force-overwrite=false','-o',trace,*cmd]
        run(a,'profile_'+method,args)
        subprocess.run(['nsys','export','--type=sqlite','--output',str(trace)+'.sqlite',str(trace)+'.nsys-rep'],check=True)
        rows.append({'method':method,'config':config,'Q':32,'source_queries':'first32 seen development IDs',
                     'scope':'one post-warmup formal.query_pass; build/load/capture excluded; diagnostic only'})
    (ROOT/'PROFILE_RUNS.json').write_text(json.dumps(rows,indent=2)+'\n')

if __name__=='__main__':main()
