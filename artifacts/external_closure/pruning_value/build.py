#!/usr/bin/env python3
"""Build a small Host harness without rewriting qualified CUDA source."""
import argparse,hashlib,json,subprocess
from pathlib import Path
if not __debug__:raise RuntimeError('Python assertions are required')
HERE=Path(__file__).resolve().parent

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def save(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def outside_repo(p):
    p=Path(p).resolve()
    for parent in (p,*p.parents):
        if (parent/'.git').exists():raise ValueError('raw evidence must stay outside Git repositories')
    return p

def main(a):
    a.output=outside_repo(a.output)
    a.output.mkdir(exist_ok=False)
    old=json.loads((a.parent/'PREPARED.json').read_text())
    assert sha(a.parent/'PREPARED.json')=='bcd1ad0b75406f7ee8a690bbc30d6f9543369118a383b82a5b9a751e39e7414f'
    assert {str(p.relative_to(a.parent/'source')):sha(p) for p in (a.parent/'source').rglob('*') if p.is_file()}==old['sources']
    commands={}
    for name in ('capture','timing'):
        commands[name]=['/usr/local/cuda-13.1/bin/nvcc','-std=c++17','-O3','-arch=sm_120','-lineinfo','-rdc=true','-Xnvlink=--ignore-host-info','--ptxas-options=-v',f'-I{a.parent}/source/include',f'-I{a.parent}/source/src']+(['-DPV_CAPTURE'] if name=='capture' else [])+[str(HERE/'probe.cu'),'-o',str(a.output/name)]
    save(a.output/'REGISTERED.json',dict(contract_sha256=sha(HERE/'CONTRACT.json'),probe_sha256=sha(HERE/'probe.cu'),parent_sources=old['sources'],commands=commands))
    for name,cmd in commands.items():
        with (a.output/(name+'.build.log')).open('x') as f:subprocess.run(cmd,stdout=f,stderr=f,check=True)
    save(a.output/'BUILD.json',{k:sha(a.output/k) for k in commands})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
