#!/usr/bin/env python3
"""Frozen clone/restore executor and short-trace generation; no dependency installation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import subprocess

if not __debug__:raise RuntimeError('Python assertions are required')
HERE=Path(__file__).resolve().parent
TARGET=HERE.parent
sys.path.insert(0,str(TARGET))
spec=importlib.util.spec_from_file_location('target_prepare',TARGET/'run.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
import validate
sha=base.sha
CPU_FLAGS=["-std=c++17","-O3","-fPIC","-shared","-fopenmp","-ffp-contract=off","-fno-fast-math","-fno-associative-math","-frounding-math"]


def prepare(work,upstream):
    manifest=base.prepare(work,upstream);source=work/'source';main=source/'src/main.cu'
    text=main.read_text();main.write_text(text[:text.index('int main(int argc,char** argv)')]+(HERE/'main.inc').read_text())
    manifest['sources']={str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*')) if p.is_file()}
    manifest['phase_b_files']={p.name:sha(p) for p in HERE.iterdir() if p.suffix in ('.py','.cpp','.inc') or p.name=='CONTRACT.json'}
    manifest['phase_b_parent']='0c8541ee0d791676822839eb16890f433464f574'
    (work/'PREPARED.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def short_operations(n):
    rng=random.Random(202610090242);physical=live=n;buffer=0;ops=[];queries=rebuilds=0
    def query():
        nonlocal queries
        ops.append((2+queries%2,rng.randrange(physical)));queries+=1
    def update(flag,index):
        nonlocal physical,live,buffer,rebuilds
        ops.append((flag,index))
        if flag==0:
            buffer+=1
            if buffer==10:physical=live+buffer;live=physical;buffer=0;rebuilds+=1
        elif index<live:live-=1
        else:assert index==live+buffer-1;buffer-=1
    for cycle in range(4):
        for _ in range(10):
            query()
            if cycle%2==0:
                update(1,rng.randrange(live));query();update(0,rng.randrange(physical));query()
            else:
                update(0,rng.randrange(physical));query();update(1,live+buffer-1);query()
        for _ in range(34):query()
        assert physical==live==n and buffer==0
    assert len(ops)==336 and queries==256 and rebuilds==2
    assert [sum(flag==k for flag,_ in ops) for k in range(4)]==[40,40,128,128]
    return ops


def cases(work,data):
    x=validate.verify_target_data(data)
    validate.case(x[:4096],work/'scope4096',[(2,0),(3,0),(0,0),(2,0),(3,0),(1,0),(2,0),(3,0)]+[(0,0)]*9+[(2,0),(3,0)])
    validate.case(x[:4096],work/'short4096',short_operations(4096))
    validate.event_case(work/'short1m',short_operations(1000000))
    validate.event_case(work/'warmup',[(2,0),(3,0),(0,0),(2,0),(3,0),(1,0),(2,0),(3,0)]+[(0,0)]*9+[(2,0),(3,0)])
    identities={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()}
    (work/'CASES.json').write_text(json.dumps(identities,indent=2)+'\n')



def cpu_build(work,data,compiler):
    validate.verify_target_data(data)
    library=work/'cpu_oracle.so';assert not library.exists()
    command=[compiler,*CPU_FLAGS,str(HERE/'cpu_oracle.cpp'),'-o',str(library)]
    subprocess.run(command,check=True)
    conformance=work.parent/'CPU_ORACLE.json';assert not conformance.exists()
    subprocess.run([sys.executable,str(HERE/'oracle.py'),'--library',str(library),'--data',str(data),'--output',str(conformance)],check=True)
    metadata=dict(library_sha256=sha(library),source_sha256=sha(HERE/'cpu_oracle.cpp'),compiler=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0],
                  flags=CPU_FLAGS,threads=8,oracle_conformance_sha256=sha(conformance))
    (work/'CPU_BUILD.json').write_text(json.dumps(metadata,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=('prepare','build','cases','self-test','cpu-oracle'))
    p.add_argument('--work',type=Path);p.add_argument('--upstream',type=Path);p.add_argument('--data',type=Path)
    p.add_argument('--nvcc',default='nvcc');p.add_argument('--cxx',default='g++');a=p.parse_args()
    if a.stage=='self-test':
        for n in (255,1000,4096,65536,1000000):assert short_operations(n)==short_operations(n)
        print('PASS deterministic 336 events, alternating queries, update counts and two rebuilds')
    else:
        if a.work is None:p.error('--work required')
        a.work=base.outside_repo(a.work)
        if a.stage=='prepare':prepare(a.work,a.upstream)
        elif a.stage=='cases':
            if a.data is None:p.error('--data required')
            cases(a.work,a.data)
        elif a.stage=='cpu-oracle':
            if a.data is None:p.error('--data required')
            cpu_build(a.work,a.data,a.cxx)
        else:
            manifest=json.loads((a.work/'PREPARED.json').read_text())
            assert all(sha(HERE/name)==digest for name,digest in manifest['phase_b_files'].items()),'phase B recipe changed'
            base.build(a.work,a.nvcc)
