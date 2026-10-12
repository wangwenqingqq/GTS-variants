#!/usr/bin/env python3
"""Independent diagnostic captures; all primary denominators remain unprofiled."""
import argparse,json,os,subprocess,sys,sqlite3
from pathlib import Path
from campaign import check_static,table,verify_stage
from prepare import HERE,EXT,read,sources
from pruning_value.build import sha,save,outside_repo
from pe_check import check as check_dynamic

def capture(a):
    w=outside_repo(a.work);reg=read(w/'REGISTERED.json');ready=read(a.ready);verify_stage(w,'qualification',a.ready,a.gpu,a.numa_node);verify_stage(w,'keeper',a.ready,a.gpu,a.numa_node);assert ready['prepared_sha256']==sha(w/'PREPARED.json');assert ready['contract_sha256']==sha(HERE/'CONTRACT.json');out=w/a.stage;out.mkdir(exist_ok=False)
    env={**os.environ,**reg['environment'],'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','MKL_NUM_THREADS':'1'};binary=w/'build/probe';r=ready['calibration']['960']['mid']['radius']
    if a.stage=='nsys_dynamic':
        verify_stage(w,'dynamic',a.ready,a.gpu,a.numa_node);binary=w/'build/dynamic';selected=[('dynamic',[str(binary),reg['data'],str(a.trace),str(r),str(out/'out')])]
    elif a.stage=='nsys_static':selected=[('FULL_OUTPUT',[str(binary),reg['data'],str(w/'qids.txt'),'1000000','960',str(r),'FULL_OUTPUT',str(out/'out'),'1'])]
    else:
        assert read(w/'nsys_static/PROOF.json')['passed'];q=sqlite3.connect(w/'nsys_static/report.sqlite');names=[x[0] for x in q.execute('select distinct s.value from CUPTI_ACTIVITY_KIND_KERNEL k join StringIds s on k.demangledName=s.id')];q.close()
        native=[n for n in names if 'pairwise' in n.lower() or 'distance' in n.lower()];assert len(native)==1,native
        selected=[]
        for m in ('READ_ONLY','DISTANCE_ONLY','FULL_OUTPUT'):
            selected.append((m,[str(binary),reg['data'],str(w/'qids.txt'),'1000000','960',str(r),m,str(out/m),'1']))
    assert sha(binary)==read(w/'build/BUILD.json')['binaries']['dynamic' if a.stage=='nsys_dynamic' else 'probe']
    save(out/'REGISTERED.json',dict(before_execution=True,source_hashes=sources(),binary_sha256=sha(binary),ready_sha256=sha(a.ready),selected=selected,scope='diagnostic-only; NCU replay/NSYS overhead excluded from primary latency',registered_stage=a.stage))
    for m,cmd in selected:
        if a.stage.startswith('nsys'):
            report=out/'report';launcher=['/usr/local/bin/nsys','profile','--trace=cuda,nvtx','--sample=none','--cpuctxsw=none','--capture-range=cudaProfilerApi','--capture-range-end=stop','-o',str(report),*cmd]
        else:
            metrics=Path(a.metrics).read_text().strip().split(',');assert metrics and all(v for v in metrics)
            kernel='regex:.*coordinate_read.*' if m=='READ_ONLY' else 'regex:.*'+__import__('re').escape(native[0])+'.*'
            launcher=['/usr/bin/sudo','-n','env','CUDA_VISIBLE_DEVICES='+a.gpu,'LD_LIBRARY_PATH='+env['LD_LIBRARY_PATH'],'/usr/local/bin/ncu','--profile-from-start','off','--kernel-name-base','demangled','--kernel-name',kernel,'--launch-count','1','--cache-control','none','--clock-control','none','--section','LaunchStats','--metrics',','.join(metrics),'-o',str(out/m),*cmd]
        guard=[sys.executable,str(EXT/'static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(out/('guard_'+m)),'--',*launcher]
        result=subprocess.run(guard,env=env,capture_output=True,text=True);(out/(m+'.outer.log')).write_text(result.stdout+result.stderr);assert result.returncode==0,'diagnostic runtime/isolation failure'
        assert read(out/('guard_'+m)/'receipt.json')['runtime_valid']
        if a.stage=='nsys_dynamic':
            quality={suffix or 'measured':check_dynamic(Path(reg['data']),a.trace.parent/('warmup.events' if suffix else 'events.txt'),str(a.trace)+suffix,str(out/'out')+suffix,'E',str(a.dynamic_reference)+suffix) for suffix in ('','.warmup')}
        else:
            import numpy as np
            x=np.memmap(reg['data'],dtype='<f4',offset=12,shape=(1000000,960));read_sum=float(x.sum(dtype=np.float64)) if m=='READ_ONLY' else None
            job=dict(kind='probe',mode=m,label=m,N=1000000,D=960,radius=r,diagnostic=1)
            quality=check_static(out/('out' if a.stage=='nsys_static' else m),job,w,reg['qids'],read_sum)
        save(out/(m+'.checked.json'),quality)
        if a.stage.startswith('nsys'):
            subprocess.run(['/usr/local/bin/nsys','export','--type','sqlite','--output',str(out/'report.sqlite'),str(out/'report.nsys-rep')],env=env,check=True,stdout=(out/'export.log').open('x'),stderr=subprocess.STDOUT)
        else:
            with (out/(m+'.csv')).open('x') as f:subprocess.run(['/usr/local/bin/ncu','--import',str(out/(m+'.ncu-rep')),'--csv','--page','raw'],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
        print('CAPTURED',m,flush=True)
    assert read(out/'REGISTERED.json')['source_hashes']==sources();save(out/'PROOF.json',dict(passed=True,registration_sha256=sha(out/'REGISTERED.json'),raw_files={p.name:sha(p) for p in out.iterdir() if p.is_file()},scope='diagnostic-only; selected-function traffic/counters, no promotion'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['nsys_static','ncu','nsys_dynamic'],required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True)
    for k in ('work','ready','trace','dynamic-reference','metrics'):p.add_argument('--'+k,type=Path,required=True)
    capture(p.parse_args())
