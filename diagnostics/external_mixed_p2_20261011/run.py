#!/usr/bin/env python3
"""Freeze exact P2/E inputs; serialize qualification, paired timing, diagnostics."""
if not __debug__:raise RuntimeError('Assertions must remain enabled')
import argparse,fcntl,hashlib,json,os,re,subprocess,sys,traceback
from pathlib import Path
from prepare import sha,read,save

def jobs(c,phase):
    if phase=='primary':return [dict(label=f'r{n}_{m}',method=m,case='target',tool=None,round=n,position=i) for n,o in enumerate(c['primary']['orders'],1) for i,m in enumerate(o)]
    if phase=='diagnostic':return [dict(label=m,method=m,case='target',tool=None,profile=True) for m in c['diagnostic']['order']]
    out=[]
    for m in ('P2','E'):out.append(dict(label=m+'_bounded',method=m,case='bounded',tool=None))
    for m in ('P2','E'):out.append(dict(label=m+'_empty',method=m,case='empty',tool=None))
    for m in ('P2','E'):
        for t in ('memcheck','racecheck','synccheck'):out.append(dict(label=m+'_'+t,method=m,case='bounded',tool=t))
    for m in ('P2','E'):out.append(dict(label=m+'_target',method=m,case='target',tool=None))
    assert [x['label'] for x in out]==c['qualification']['order'];return out

def verify(r,reg,a):
    assert all(sha(r/n)==h for n,h in reg['inputs'].items()),'input drift'
    assert all(sha(n)==h for n,h in reg['library_hashes'].items()),'library drift'
    assert all(sha(a.reference.parent/n)==h for n,h in reg['reference'].items()),'oracle drift'
    assert sha(a.data)==reg['data_sha256'],'data drift'

def main():
    p=argparse.ArgumentParser()
    for k in ('root','reference','data'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--gpu',required=True);a=p.parse_args();r=a.root;c=read(r/'CONTRACT.json');reg=read(r/'INPUTS.json')
    assert hashlib.sha256(a.gpu.encode()).hexdigest()==c['hardware']['gpu_uuid_sha256'];assert not (r/'REGISTERED.json').exists()
    local=(r/'campaign.lock').open('a+');fcntl.flock(local,fcntl.LOCK_EX|fcntl.LOCK_NB)
    locks=[]
    for n in c['hardware']['locks']:
        q=Path(n);f=q.open('r' if q.exists() else 'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    fds=tuple(f.fileno() for f in locks);os.environ['GTS_CAMPAIGN_LOCK_FDS']=','.join(map(str,fds))
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    topo=subprocess.check_output(['nvidia-smi','topo','-m'],text=True);assert next(x.split() for x in topo.splitlines() if x.startswith('GPU1\t'))[-2]=='0'
    verify(r,reg,a)
    sys.path.insert(0,str(r/'checker/artifacts/external_closure'));from pe_check import check
    base={**os.environ,**read(r/'E/REGISTERED.json')['environment'],'REGION_MODE':'PAR_STRONG','BUILD_MAPPING':'TILED','KNN_MODE':'FULL','TARGET_WARMUP':'1','U10_OBSERVE':'1','U10_TREE_AUDIT':'0','TARGET_RESTORE_AUDIT':'0','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    save(r/'REGISTERED.json',dict(inputs_sha256=sha(r/'INPUTS.json'),contract_sha256=sha(r/'CONTRACT.json'),before_execution=True,topology=topo,environment={k:base[k] for k in ('LD_LIBRARY_PATH','REGION_MODE','BUILD_MAPPING','KNN_MODE','TARGET_WARMUP','U10_OBSERVE','U10_TREE_AUDIT','TARGET_RESTORE_AUDIT','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},gpu=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid,name,driver_version,clocks.sm,clocks.mem,power.limit','--format=csv,noheader'],text=True),jobs={phase:jobs(c,phase) for phase in ('qualification','primary','diagnostic')}))
    for phase in ('qualification','primary','diagnostic'):
        if phase!='qualification':assert read(r/('qualification' if phase=='primary' else 'primary')/'GATE.json')['passed']
        out=r/phase;out.mkdir();(out/'outputs').mkdir();rows=[];selected=jobs(c,phase)
        save(out/'FROZEN.json',dict(parent_sha256=sha(r/'REGISTERED.json'),jobs=selected))
        try:
            for j in selected:
                case=r/'cases'/j['case'];data=a.data if j['case']=='target' else case/'data.f32bin';prefix=out/'outputs'/j['label'];m=j['method'];env={**base,'PE_TRACE':str(case/'trace')}
                binary=r/m/('bench' if m=='P2' else 'scan');assert sha(binary)==c['binaries'][m]
                cmd=[binary,data,case/'events.txt','2',str(c['shape']['radius']),prefix,'8'] if m=='P2' else [binary,data,case/'trace',str(c['shape']['radius']),prefix]
                if j['tool']:cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',j['tool'],'--error-exitcode','99',*cmd]
                if j.get('profile'):cmd=['/usr/local/cuda-13.1/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--force-overwrite=false','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0','-o',out/m,*cmd]
                result=subprocess.run([sys.executable,r/'deps/locked.py','--gpu',a.gpu,'--numa-node','0','--output',out/'runs'/j['label'],'--',*map(str,cmd)],env=env,pass_fds=fds)
                receipt=read(out/'runs'/j['label']/'receipt.json');assert result.returncode==0 and receipt['runtime_valid'],('runtime/isolation',j)
                assert all(not x['foreign'] for x in read(out/'runs'/j['label']/'checks.json'))
                log=''.join((out/'runs'/j['label']/n).read_text() for n in ('stdout.log','stderr.log'))
                assert not re.search(r'\bFAIL\s*:|Error!!!|cuda.{0,60}(?:error|failed)',log,re.I)
                if j['tool']:assert ('RACECHECK SUMMARY: 0 hazards' if j['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
                ref=a.reference if j['case']=='target' else None
                q={s or 'measured':check(data,case/e,str(case/'trace')+s,str(prefix)+s,'P' if m=='P2' else 'E',str(ref)+s if ref else None) for s,e in [('','events.txt'),('.warmup','warmup.events')]}
                save(str(prefix)+'.quality.json',q)
                if j.get('profile'):subprocess.run(['/usr/local/cuda-13.1/bin/nsys','export','--type=sqlite','--output',out/(m+'.sqlite'),out/(m+'.nsys-rep')],check=True)
                row={**j,'passed':True,'receipt_sha256':sha(out/'runs'/j['label']/'receipt.json'),'quality_sha256':sha(str(prefix)+'.quality.json')};rows.append(row);save(out/'PROGRESS.json',rows);print('PASS',phase,j['label'],flush=True)
            verify(r,reg,a)
            save(out/'GATE.json',dict(passed=True,rows=rows,files={str(x.relative_to(out)):sha(x) for x in out.rglob('*') if x.is_file()}))
        except Exception:
            (out/'FAILURE.txt').write_text(traceback.format_exc());save(out/'FAILED.json',dict(passed=False,passed_rows=rows,failed_job=j,unexecuted_after_stop=selected[len(rows)+1:]));raise
    verify(r,reg,a)
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    count=payloads=0
    for phase in ('qualification','primary','diagnostic'):
        gate=read(r/phase/'GATE.json');assert gate['passed'] and len(gate['rows'])==len(jobs(c,phase));count+=len(gate['rows'])
        assert all(sha(r/phase/n)==h for n,h in gate['files'].items())
        for row in gate['rows']:
            q=read(r/phase/'outputs'/(row['label']+'.quality.json'))
            for suffix,quality in q.items():
                assert quality['passed'];stem=r/phase/'outputs'/(row['label']+('.warmup' if suffix=='.warmup' else ''))
                for s,h in quality['payload_hashes'].items():assert sha(str(stem)+s)==h;payloads+=1
    assert count==26
    save(r/'CLOSURE.json',dict(passed=True,processes=count,qualified_payload_files=payloads,contract_sha256=sha(r/'CONTRACT.json'),inputs_sha256=sha(r/'INPUTS.json'),registration_sha256=sha(r/'REGISTERED.json'),gpu_clear_after=True,all_frozen_inputs_libraries_oracles_reverified=True))
    print('CLOSURE PASS',count,flush=True)
if __name__=='__main__':main()
