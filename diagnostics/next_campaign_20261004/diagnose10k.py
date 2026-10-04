#!/usr/bin/env python3
"""Task-owned environment and bounded actual-kernel profiles; no formal timing."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from campaign10k import ROOT,BASE,commands,common,invoke,inventory,save,sha

def environment(a):
    import cupy as cp
    import numpy as np
    import importlib.metadata as m
    prop=cp.cuda.runtime.getDeviceProperties(0)
    libs=[]
    for pkg in ('faiss','cuvs','cupy'):
        try:
            module=__import__(pkg);directory=Path(module.__file__).parent
            for p in sorted(directory.rglob('*.so')):libs.append({'package':pkg,'file':p.name,'path':str(p),'sha256':sha(p)})
        except ImportError:pass
    packages={}
    for pkg in ('faiss','cuvs','cupy-cuda13x','numpy'):
        try:packages[pkg]=m.version(pkg)
        except m.PackageNotFoundError:pass
    save(ROOT/f'ENV_{a.family}.json',{'packages':packages,'library_sha256':libs,'numpy':np.__version__,'cupy':cp.__version__,
        'device':{k:str(prop[k]) for k in ('name','totalGlobalMem','major','minor')},
        'runtime_version':cp.cuda.runtime.runtimeGetVersion(),'driver_version':cp.cuda.runtime.driverGetVersion(),
        'memory_limit_bytes':80*(1<<30),'numa_node':3,'faiss_use_cuvs':False,'OMP_NUM_THREADS':__import__('os').environ.get('OMP_NUM_THREADS')})

def profiles(a):
    inventory(a);dest=ROOT/'profiles';dest.mkdir(exist_ok=True)
    qs=list(map(int,(ROOT/'fixtures/GIST_dev1024.qid').read_text().split()))[1:33]
    qp=ROOT/'fixtures/GIST_diagnostic32.qid';qp.write_text('32\n'+''.join(f'{q}\n' for q in qs))
    (ROOT/'runs').mkdir(exist_ok=True)
    for name,py in (('FAISS',a.faiss_python),('CUVS',a.cuvs_python)):
        invoke(a,f'environment_{name}',[py,ROOT/'diagnose10k.py','environment','--family',name,*common(a)])
    inputs={}
    for d in ('GIST','Deep'):
        for role,p in (('data',a.data_root/f'{d}/1000000/fixtures/data.f32bin'),('tree',BASE/f'{d}.index')):
            s=p.stat();inputs[f'{d}_{role}']={'path':str(p),'sha256':sha(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
    for p in [ROOT/'fixtures/seeds_1000000.i32',*ROOT.glob('*.index'),*(BASE/'gts/adapted/include').glob('*')]:
        if p.is_file():
            s=p.stat();inputs[str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)]={'path':str(p),'sha256':sha(p),'bytes':s.st_size,'mtime_ns':s.st_mtime_ns}
    save(ROOT/'INPUT_IDENTITIES.json',inputs)
    # Compatible smoke report before any metric matrix; previous CLI failures
    # stay in the P7 evidence directory and are never overwritten.
    helptext=subprocess.check_output(['/usr/local/bin/ncu','--help'],text=True)
    (dest/'ncu_help.txt').write_text(helptext)
    metrics=subprocess.check_output(['/usr/local/bin/ncu','--query-metrics','--devices','7'],text=True)
    (dest/'ncu_metrics.txt').write_text(metrics)
    out=dest/'ncu_smoke_output'
    cmd=commands(a,'GIST','O_BOUND',8,32,qp,out,{})
    smoke=['/usr/local/bin/ncu','--clock-control','none','--cache-control','none','--kernel-name-base','demangled',
           '--kernel-name','regex:verify_distances','--launch-count','1','--set','basic','--export',dest/'ncu_smoke',*cmd]
    status=[]
    try:
        invoke(a,'ncu_smoke',smoke)
        report=dest/'ncu_smoke.ncu-rep';assert report.stat().st_size>0
        r=subprocess.run(['/usr/local/bin/ncu','--import',str(report),'--csv','--page','raw'],text=True,capture_output=True,check=True)
        (dest/'ncu_smoke.csv').write_text(r.stdout);assert 'Kernel Name' in r.stdout
        status.append({'tool':'NCU','state':'measured','report_sha256':sha(report),'csv_sha256':sha(dest/'ncu_smoke.csv')})
    except Exception as e:
        status.append({'tool':'NCU','state':'unsupported_or_failed','error':str(e),'physical_counters':'unknown'})
    save(ROOT/'DIAGNOSTIC_STATUS.json',status)
    for b in (1,32):
        for m in ('GTS_ORIG','O_BOUND','O_MASK','FAISS_FLAT','IVF_ALL','CAGRA'):
            label=f'nsys_{m}_b{b}';out=dest/label
            c={'nlist':1024,'nprobe':1024} if m=='IVF_ALL' else {'itopk_size':1024,'search_width':4} if m=='CAGRA' else {}
            cmd=commands(a,'GIST',m,8,b,qp,out,c)
            args=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--cuda-graph-trace=node',
                  '--sample=process-tree','--cpuctxsw=process-tree','--cuda-um-cpu-page-faults=true','--cuda-um-gpu-page-faults=true',
                  '--capture-range=nvtx','--nvtx-capture=formal.query_pass','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
                  '--capture-range-end=stop','--force-overwrite=false','-o',out,*cmd]
            try:
                invoke(a,label,args)
                rep=Path(str(out)+'.nsys-rep');assert rep.stat().st_size>0
                subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--output',str(out)+'.sqlite',str(rep)],check=True)
                status.append({'tool':'NSYS','label':label,'state':'measured','report_sha256':sha(rep)})
            except Exception as e:status.append({'tool':'NSYS','label':label,'state':'unsupported_or_failed','error':str(e)})
            save(ROOT/'DIAGNOSTIC_STATUS.json',status)
    print('BOUNDED DIAGNOSTICS COMPLETE',flush=True)

def counters(a):
    dest=ROOT/'profiles'
    smoke=dest/'ncu_smoke.csv'
    assert smoke.exists() and 'Kernel Name' in smoke.read_text(),'smoke report must be nonempty before matrix'
    status=[]
    for m,kernel in [('O_FULL','verify_distances'),('O_BOUND','verify_distances'),('O_MASK','verify_distances'),
                     ('O_BOUND','seed_distances'),('O_BOUND','block_topk'),('O_MASK','knn_parent_walk'),
                     ('O_MASK','knn_mask'),('GTS_ORIG','dataProcessKnn')]:
        label=f'ncu_{m}_{kernel}';out=dest/label
        cmd=commands(a,'GIST',m,8,32,ROOT/'fixtures/GIST_diagnostic32.qid',out,{})
        args=['/usr/local/bin/ncu','--clock-control','none','--cache-control','none','--replay-mode','kernel',
              '--kernel-name-base','demangled','--kernel-name',f'regex:{kernel}','--launch-count','1','--set','full',
              '--export',out,*cmd]
        try:
            invoke(a,label,args)
            report=Path(str(out)+'.ncu-rep');assert report.stat().st_size>0
            r=subprocess.run(['/usr/local/bin/ncu','--import',str(report),'--csv','--page','raw'],text=True,capture_output=True,check=True)
            Path(str(out)+'.metrics.csv').write_text(r.stdout)
            assert 'Kernel Name' in r.stdout and kernel in r.stdout
            status.append({'label':label,'state':'measured','Q':32,'B':32,'profiled_launches':1,
                           'scope':'first matching development warmup launch; kernel replay, cache-control none, clock-control none; not formal pass',
                           'report_sha256':sha(report),'metrics_csv_sha256':sha(str(out)+'.metrics.csv')})
        except Exception as e:status.append({'label':label,'state':'unsupported_or_failed','error':str(e)})
        save(ROOT/'COUNTER_STATUS.json',status)
    print('BOUNDED COUNTERS COMPLETE',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('environment','profiles','counters'))
    p.add_argument('--family');p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--data-root',type=Path,required=True);p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True)
    a=p.parse_args();globals()[a.phase](a)

if __name__=='__main__':main()
