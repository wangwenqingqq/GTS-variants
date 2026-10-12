#!/usr/bin/env python3
"""Build one matched diagnostic without modifying the qualified parent source."""
import argparse,json,os,subprocess
from pathlib import Path
from prepare import HERE,EXT,read,sources
from pruning_value.build import sha,save,outside_repo

def build(a):
    out=outside_repo(a.output);out.mkdir(exist_ok=False)
    parent=EXT/'pruning_value/probe.cu';s=parent.read_text();marker='\nint main(int argc,char** argv) try {';assert s.count(marker)==1
    support=out/'support.cuh';support.write_text(s.split(marker)[0]+'\n')
    original=read(a.parent_registration);cmd=original['commands']['timing'];cmd=[str(HERE/'matched.cu') if v.endswith('/probe.cu') else str(out/'matched') if v==original['commands']['timing'][-1] else v for v in cmd]
    cmd+=['-DMATCHED_SUPPORT="'+str(support)+'"']
    env={**os.environ,**read(a.prepared_registration)['environment']}
    save(out/'REGISTERED.json',dict(before_compilation=True,source_hashes=sources(),parent_sha256=sha(parent),generated_support_sha256=sha(support),command=cmd,scope='diagnostic-only ordered FP64; no tree query'))
    with (out/'compile.log').open('x') as f:subprocess.run(cmd,env=env,stdout=f,stderr=f,check=True)
    save(out/'BUILD.json',dict(binary_sha256=sha(out/'matched'),registration_sha256=sha(out/'REGISTERED.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('output','parent-registration','prepared-registration'):p.add_argument('--'+k,type=Path,required=True)
    build(p.parse_args())
