#!/usr/bin/env python3
"""Bounded subtree experiment, using the frozen U10 data/oracle/guard."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np

MODES=('NATIVE','PAR_STRONG','REGION_SPLIT','REGION_FUSED')
ORDERS=((0,1,2,3),(3,2,1,0),(1,3,0,2),(2,0,3,1),(2,1,3,0),(0,3,1,2))
SEED=2026100431

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')

def prepare(a):
    dst=a.dest/'native_timed/source';src=a.workflow/'native_timed/source'
    assert not dst.exists(),'new development namespace required; measured source immutable'
    shutil.copytree(src,dst)
    for f in Path(__file__).parent.glob('*.cuh'):shutil.copy2(f,dst/'include'/f.name)
    for f in Path(__file__).parent.glob('*.hpp'):shutil.copy2(f,dst/'include'/f.name)
    f=dst/'include/update.cuh';s=f.read_text()
    pos=s.index('void searchIndexRnnUpdate(')
    s=s[:pos]+'#include "region_bridge.cuh"\n\n'+s[pos:]
    s=s.replace('void searchIndexRnnUpdate(', 'void searchIndexRnnUpdateNative(',1)
    pos=s.index('void updateIndexRnn(')
    wrapper='''void searchIndexRnnUpdate(short* data,TN* nodes,int* order,int* nn,int* qids,
    int qnum,float radius,int height,int* info,int*& empty,int*& counts,
    int*& prefix,int*& ids,float*& distances,char* strings,int* lengths) {
    if(rex::bridge.mode)rex::bridge.search(data,is_delete,qids,qnum,radius,info,counts,prefix,ids,distances);
    else searchIndexRnnUpdateNative(data,nodes,order,nn,qids,qnum,radius,height,info,empty,counts,prefix,ids,distances,strings,lengths);
}
'''
    s=s[:pos]+wrapper+s[pos:]
    s=s.replace('\t\t\t\tu10.end_rebuild();','\t\t\t\trex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);\n\t\t\t\tu10.end_rebuild();')
    assert s.count('rex::bridge.refresh(')==1
    f.write_text(s)
    f=dst/'src/main.cu';s=f.read_text()
    s=s.replace('u10_ck(cudaFree(nullptr));auto start=U10Clock::now();',
                'auto context_begin=U10Clock::now();u10_ck(cudaFree(nullptr));rex::bridge.context_ms=u10_ms(context_begin);auto setup_begin=U10Clock::now();auto start=setup_begin;')
    s=s.replace('    u10.begin();','    rex::bridge.refresh(node_list,empty_list,id_list,max_node_num[0],data_info[1],TREE_ORDER);\n    rex::bridge.setup_ms=u10_ms(setup_begin);\n    u10.begin();')
    s=s.replace('    for(void* p:', '    rex::bridge.finish();\n    for(void* p:')
    s=s.replace('u10.write(argv[5]);return 0;','u10.write(argv[5]);rex::bridge.write(argv[5]);return 0;')
    f.write_text(s)
    f=dst/'include/u10_trace.hpp';s=f.read_text()
    s=s.replace('bool tree_audit=', 'int expected_queries=0, expected_events=0;\n    bool tree_audit=')
    s=s.replace('if(n!=1000 || q!=10000 || events!=12000)', 'expected_queries=q;expected_events=events;\n        if(n!=1000 || q<1 || q>10000 || events<1 || events>12000)')
    s=s.replace('queries.size()!=10000 || (observe && operations.size()!=12000)', 'queries.size()!=size_t(expected_queries) || (observe && operations.size()!=size_t(expected_events))')
    f.write_text(s)
    binary=a.dest/'native_timed/region_exec'
    cmd=['/usr/local/cuda/bin/nvcc','-std=c++17','-O3','-arch=sm_120','-rdc=true','-lineinfo',
         '-Xnvlink=--ignore-host-info','--ptxas-options=-v','-I'+str(dst/'include'),str(dst/'src/main.cu'),'-o',str(binary)]
    with (a.dest/'BUILD.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    save(a.dest/'SOURCE.json',{'baseline_manifest_sha256':sha(a.workflow/'native_timed/SOURCE.json'),
         'binary_sha256':sha(binary),'sources':{str(p.relative_to(dst)):sha(p) for p in dst.rglob('*') if p.is_file()},
         'controller_sha256':sha(__file__),'build':cmd,'input_values':'integer; actual storage float via original #define short float'})
    (a.dest/'native').symlink_to(a.workflow/'native',target_is_directory=True)

def run(a,label,case,mode,observe=True,tool=None,audit=False):
    target=a.dest/'native_timed'/label;run_dir=a.dest/'runs'/label
    assert not run_dir.exists(),'prior run retained; never automatically replay failed/slow samples'
    binary=a.dest/'native_timed/region_exec'
    assert sha(binary)==read(a.dest/'SOURCE.json')['binary_sha256']
    env={'REGION_MODE':mode,'U10_OBSERVE':str(int(observe)),'U10_TREE_AUDIT':str(int(audit))}
    cmd=[str(binary),str(case/'data.txt'),str(case/'events.txt'),'2',str(read(case/'expected.json')['radius']),str(target)]
    if tool:cmd=['/usr/local/cuda/bin/compute-sanitizer','--tool',tool,'--error-exitcode','77',*cmd]
    (a.dest/'registrations').mkdir(exist_ok=True)
    registration={'label':label,'mode':mode,'observe':observe,'source_sha256':sha(a.dest/'SOURCE.json'),
                  'binary_sha256':sha(binary),'data_sha256':sha(case/'data.txt'),'events_sha256':sha(case/'events.txt'),
                  'oracle_sha256':sha(case/'expected.json'),'command':cmd,'environment':env}
    save(a.dest/'registrations'/(label+'.json'),registration)
    subprocess.run([sys.executable,str(a.raw/'run_locked.py'),'--gpu',a.gpu,'--output',str(run_dir),
                    '--timeout-seconds','1200','--',*cmd],env={**os.environ,**env},check=True,stdout=subprocess.DEVNULL)
    assert read(run_dir/'receipt.json')['runtime_valid']
    if tool:
        text=(run_dir/'stdout.log').read_text()+(run_dir/'stderr.log').read_text()
        assert 'ERROR SUMMARY: 0 errors' in text,text[-2000:]
    if case.parent==a.dest/'native':
        sys.path.insert(0,str(a.raw));import u10_native
        u10_native.ROOT=a.dest;result=u10_native.check_timed(a,case.name,label)
    else:
        sys.path.insert(0,str(a.helpers));from u_life_bridge import check_small
        result=check_small(a,case,target,run_dir,audit)
    result['mode']=mode;result['region']=read(str(target)+'.region.json')
    result['registration_sha256']=sha(a.dest/'registrations'/(label+'.json'))
    save(str(target)+'.CHECK.json',result)
    print(label,'PASS',round(result['summary']['trace_ms'],3),flush=True);return result

def equal_output(x,y):return all(x['outputs'][s]==y['outputs'][s] for s in ('.ids.i32','.dist.f32','.queries.csv'))

def qualify(a):
    sys.path.insert(0,str(a.helpers));from u_life_bridge import small_cases
    rows=[]
    for case in small_cases(a):
        results=[run(a,'boundary_'+case.name+'_'+m,case,m,audit=True) for m in MODES[:2]]
        assert equal_output(*results);rows+=results
    save(a.dest/'BOUNDARIES.json',rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('prepare','qualify'))
    for name in ('raw','workflow','dest','u0','helpers'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gpu',required=True);a=p.parse_args();a.dest.mkdir(parents=True,exist_ok=True)
    {'prepare':prepare,'qualify':qualify}[a.phase](a)

if __name__=='__main__':main()
