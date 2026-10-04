#!/usr/bin/env python3
"""Task-owned environment and bounded actual-kernel profiles; no formal timing."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from campaign10k import ROOT,BASE,commands,common,invoke,inventory,save,sha,audit_output

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

def cold(a):
    """Unchanged original adapter, fresh owned caches, one legal build/data."""
    import numpy as np
    from qualification import native_ivf
    dest=ROOT/'profiles';dest.mkdir(exist_ok=True);rows=[]
    for d in ('GIST','Deep'):
        ref=json.loads((ROOT/f'oracle_{d}_dev1024.json').read_text())
        ref={**ref,'Q':32,'records':ref['records'][:32]}
        qp=ROOT/f'fixtures/{d}_diagnostic32.qid'
        if not qp.exists():qp.write_text('32\n'+''.join(f'{r["qid"]}\n' for r in ref['records']))
        cache=dest/f'cold_{d}.index';out=dest/f'cold_{d}'
        label=f'cold_{d}';run=ROOT/'runs'/label
        # A build artifact is an expected output, not a pre-existing index input.
        assert not cache.exists() or run.exists(),'cold cache already exists without its receipt'
        cmd=commands(a,d,'GTS_ORIG',8,1,qp,out,{})
        cmd[6]=cache
        args=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=process-tree','--cpuctxsw=process-tree',
              '--capture-range=nvtx','--nvtx-capture=static.index_build','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0',
              '--capture-range-end=stop','--force-overwrite=false','-o',out,*cmd]
        # The generated cache is the sole declared output excluded from the
        # before/after input identity. Keep every measured source/data/command.
        from campaign10k import run_identity
        identity=run_identity(a,args,identity_files=list((BASE/'gts/adapted/include').glob('*.cuh')))
        if run.exists():
            receipt=json.loads((run/'receipt.json').read_text());assert receipt['runtime_valid']
            saved=json.loads((run/'identity.json').read_text())
            identity['files'].pop(str(cache.resolve()),None)
            assert saved==identity
            previous=dest/f'cold_{d}.AUDIT.json'
            if previous.exists():assert sha(cache)==json.loads(previous.read_text())['index_sha256']
        else:
            save(ROOT/f'cold_{d}.REGISTERED.json',identity)
            locked=[sys.executable,ROOT/'run_locked.py','--gpu',a.gpu,'--output',run,'--timeout-seconds',7200,'--',*args]
            subprocess.run(list(map(str,locked)),check=True)
            after=run_identity(a,args,identity_files=list((BASE/'gts/adapted/include').glob('*.cuh')))
            after['files'].pop(str(cache.resolve()),None);assert after==identity
            save(run/'identity.json',identity);receipt=json.loads((run/'receipt.json').read_text())
        rep=Path(str(out)+'.nsys-rep');sql=Path(str(out)+'.sqlite')
        if not sql.exists():subprocess.run(['/usr/local/bin/nsys','export','--type=sqlite','--output',str(sql),str(rep)],check=True)
        with cache.open('rb') as f:
            n,dim,height,nodes=map(int,np.fromfile(f,'<i4',4));order=np.fromfile(f,'<i4',n)
            topology=np.fromfile(f,dtype=np.dtype([('pid','<i4'),('lo','<f4'),('size','<i4'),('lid','<i4'),('leaf','<i4')]),count=nodes)
            empty=np.fromfile(f,'<i4',nodes);assert not f.read(1)
        assert n==1000000 and np.array_equal(np.sort(order),np.arange(n))
        active=np.flatnonzero(empty==0);leaves=[i for i in active if topology[i]['leaf']]
        cursor=0
        for i in sorted(leaves,key=lambda j:int(topology[j]['lid'])):
            node=topology[i];assert int(node['lid'])==cursor and 0<int(node['size'])<=20;cursor+=int(node['size'])
        assert cursor==n
        for i in active:
            if i==0:continue
            parent=topology[(i-1)//10];node=topology[i]
            assert parent['lid']<=node['lid'] and node['lid']+node['size']<=parent['lid']+parent['size']
        meta=json.loads(next(s[7:] for s in (run/'stdout.log').read_text().splitlines() if s.startswith('RESULT ')))
        assert not meta['cache_loaded']
        quality=audit_output(str(out)+'.bin',native_ivf.load_data(a.data_root/f'{d}/1000000/fixtures/data.f32bin'),ref,8)
        assert quality['complete_gate_pass'],'cold adapter post-build query output failure'
        row={'dataset':d,'N':n,'D':dim,'height':height,'active_nodes':len(active),'leaf_nodes':len(leaves),
             'capacity_permutation_disjoint_coverage_and_parent_intervals':True,'index_sha256':sha(cache),
             'setup':meta,'build_scope':'NSYS static.index_build ends after original constructor and device synchronization; setup index time additionally includes coverage audit/cache write',
             'pivot_object_distances':sum(int(topology[i]['size']) for i in active if not topology[i]['leaf']),
             'node_boundary_distances':len(active)-1,'sorts_full_N':height-1,
             'quality':quality,'receipt':receipt,'report_sha256':sha(rep),'sqlite_sha256':sha(sql)}
        save(dest/f'cold_{d}.AUDIT.json',row);rows.append(row);save(ROOT/'COLD_BUILD.json',rows)
        print('COLD LEGAL BUILD',d,n,dim,height,flush=True)

def pass_counters(a):
    """New measured-pass launches; prior warmup-only reports remain intact."""
    dest=ROOT/'profiles';dest.mkdir(exist_ok=True);status=[]
    for m,kernel in (('O_FULL','verify_distances'),('O_BOUND','verify_distances'),('O_MASK','verify_distances'),('GTS_ORIG','dataProcessKnn')):
        label=f'ncu_pass_{m}_{kernel}';out=dest/label
        cmd=commands(a,'GIST',m,8,32,ROOT/'fixtures/GIST_diagnostic32.qid',out,{})
        args=['/usr/local/bin/ncu','--clock-control','none','--cache-control','none','--replay-mode','kernel',
              '--nvtx','--nvtx-include','formal.query_pass/','--kernel-name-base','demangled',
              '--kernel-name',f'regex:{kernel}','--launch-count','1','--set','full','--export',out,*cmd]
        invoke(a,label,args,identity_files=list((BASE/'gts/adapted/include').glob('*.cuh')))
        report=Path(str(out)+'.ncu-rep');assert report.stat().st_size>0
        r=subprocess.run(['/usr/local/bin/ncu','--import',str(report),'--csv','--page','raw'],text=True,capture_output=True,check=True)
        Path(str(out)+'.metrics.csv').write_text(r.stdout);assert 'Kernel Name' in r.stdout and kernel in r.stdout
        work={'query_object_pairs':32*1000000,'distance_coordinates':32*1000000*960,'early_exit':False} if m=='O_FULL' else {
              'exact_distance_coordinates':'pending per-launch dynamic work ledger; do not infer them from traffic or compare iterative launches as equal work'}
        status.append({'label':label,'state':'measured','scope':'first matching kernel inside actual post-warmup formal.query_pass; diagnostic replay, not formal timing',
                       'Q':32,'B':32,'work':work,'report_sha256':sha(report),'metrics_csv_sha256':sha(str(out)+'.metrics.csv')})
        save(ROOT/'PASS_COUNTER_STATUS.json',status)
        print('ACTUAL QUERY PASS COUNTERS',m,kernel,flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=('environment','profiles','counters','cold','pass_counters'))
    p.add_argument('--family');p.add_argument('--gpu',required=True);p.add_argument('--p7',type=Path,required=True)
    p.add_argument('--data-root',type=Path,required=True);p.add_argument('--faiss-python',required=True);p.add_argument('--cuvs-python',required=True)
    a=p.parse_args();globals()[a.phase](a)

if __name__=='__main__':main()
