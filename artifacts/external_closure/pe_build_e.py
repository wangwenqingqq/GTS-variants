#!/usr/bin/env python3
"""Build the dynamic scan adapter with the already installed, qualified libraries."""
import argparse,json,os,subprocess
from pathlib import Path
from common import outside_repo
from qualify import cpu
HERE=Path(__file__).resolve().parent

def main(a):
    w=outside_repo(a.work);w.mkdir(parents=True,exist_ok=False)
    parent=json.loads((a.range_build/'BUILD_REGISTERED.json').read_text())
    cmd=parent['commands']['range_static'];cmd=[str(HERE/'pe_e.cu') if v.endswith('/static_range.cu') else str(w/'scan') if v.endswith('/bin/range_static') else v for v in cmd]
    cmd+=['-I'+str(a.faiss_source),str(a.faiss_archive),'-L'+str(a.cuda/'lib64'),'-lcublas','-lcublasLt','-lopenblas','-lgomp','-lpthread','-ldl']
    env={**os.environ,'LD_LIBRARY_PATH':':'.join(parent['library_search_dirs']+[str(a.cuda/'lib64')])}
    headers=['faiss/gpu/GpuDistance.h','faiss/gpu/GpuDistance.cu','faiss/gpu/impl/FlatIndex.cu','faiss/gpu/impl/L2Norm.cuh','faiss/gpu/impl/L2Norm.cu']
    cpu.save(w/'REGISTERED.json',dict(command=cmd,environment={'LD_LIBRARY_PATH':env['LD_LIBRARY_PATH']},dependencies={'libfaiss.a':cpu.sha(a.faiss_archive)},
        upstream_headers={p:cpu.sha(a.faiss_source/p) for p in headers},source={p.name:cpu.sha(p) for p in (HERE/'pe_e.cu',HERE/'pe_common.hpp',HERE/'range_service.cu')},builder_sha256=cpu.sha(__file__)))
    with (w/'compile.log').open('x') as f:subprocess.run(cmd,env=env,stdout=f,stderr=f,check=True)
    ldd=subprocess.check_output(['ldd',str(w/'scan')],env=env,text=True);assert 'not found' not in ldd;(w/'ldd.txt').write_text(ldd)
    cpu.save(w/'BUILD.json',dict(binary_sha256=cpu.sha(w/'scan'),registration_sha256=cpu.sha(w/'REGISTERED.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('work','range-build','faiss-source','faiss-archive','cuda'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
