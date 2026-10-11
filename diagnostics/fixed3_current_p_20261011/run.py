#!/usr/bin/env python3
"""Serial bounded current-P qualification -> same work -> profile -> gated formal."""
if not __debug__:raise RuntimeError('Assertions must remain enabled')
import argparse,fcntl,hashlib,json,os,re,shutil,subprocess,sys,traceback
from pathlib import Path
from analyze import save,work,trace,formal

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
    p=argparse.ArgumentParser()
    for key in ('root','parent','reference','checker','data'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--gpu',required=True);a=p.parse_args();r=a.root.resolve();c=read(r/'CONTRACT.json');b=read(r/'BUILD_GATE.json');assert b['passed']
    binding=c['hardware'];expected=binding.get('gpu_uuid_sha256') or hashlib.sha256(binding['gpu_uuid'].encode()).hexdigest()
    assert hashlib.sha256(a.gpu.encode()).hexdigest()==expected;sys.path.insert(0,str(a.checker/'artifacts/external_closure'));from pe_check import check
    local_lock=(r/'campaign.lock').open('a+');fcntl.flock(local_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    topology=subprocess.check_output(['nvidia-smi','topo','-m'],text=True);row=next(x.split() for x in topology.splitlines() if x.startswith('GPU1\t'));assert row[-2]=='0'
    locks=[]
    for path in c['hardware']['locks']:
        path=Path(path);f=path.open('r' if path.exists() else 'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
    fds=tuple(x.fileno() for x in locks);os.environ['GTS_CAMPAIGN_LOCK_FDS']=','.join(map(str,fds))
    assert not subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
    assert sha(a.data)==c['shape']['data_sha256'] and sha(a.parent/'campaign/cases/target/events.txt')==c['shape']['events_sha256']
    # Saved native oracle is bound to the prior registration, not an arbitrary similar output.
    prior=read(a.parent/'campaign/REGISTERED.json')['reference']
    assert all(sha(a.reference.parent/name)==h for name,h in prior.items())
    cases=r/'cases';shutil.copytree(a.parent/'campaign/cases',cases)
    inputs={str(x.relative_to(r)):sha(x) for x in r.rglob('*') if x.is_file() and not any(y in x.parts for y in ('keeper','__pycache__')) and (x.parts[len(r.parts)] in ('P0','P1','P2','cases','deps') or (x.parent==r and x.suffix in ('.py','.cu','.json'))) and x.name!='campaign.lock'}
    checkpins={str(x.relative_to(a.checker)):sha(x) for x in (a.checker/'artifacts').rglob('*') if x.is_file() and x.suffix in ('.py','.json') and '__pycache__' not in x.parts}
    for m in ('P0','P1','P2'):
        for kind,rec in b['modes'][m].items():assert sha(r/m/kind)==rec['binary_sha256']
        for branch,record in [('source',read(r/m/'SOURCE_PINS.json')['sources']),('count_source',read(r/m/'COUNT_PINS.json'))]:
            for name,h in record.items():assert sha(r/m/branch/name)==h
    identity=dict(inputs=inputs,checker=checkpins,reference=prior,data_sha256=sha(a.data),gpu=a.gpu,topology=topology)
    assert not (r/'REGISTERED.json').exists();save(r/'REGISTERED.json',identity)
    baseenv={**os.environ,'REGION_MODE':'PAR_STRONG','BUILD_MAPPING':'TILED','KNN_MODE':'FULL','TARGET_WARMUP':'1','U10_OBSERVE':'1','U10_TREE_AUDIT':'0','TARGET_RESTORE_AUDIT':'0','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    for phase in ('qualify','work','profile','formal'):
        if phase=='formal' and not read(r/'profile/GATE.json')['pass_gate_E']:print('STOP: Gate E failed; no formal processes',flush=True);break
        out=r/phase;out.mkdir();(out/'outputs').mkdir();save(out/'FROZEN.json',dict(identity_sha256=sha(r/'REGISTERED.json'),gpu=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-gpu=uuid,name,driver_version,clocks.sm,clocks.mem,power.limit','--format=csv,noheader'],text=True),environment={k:baseenv[k] for k in ('REGION_MODE','BUILD_MAPPING','KNN_MODE','TARGET_WARMUP','U10_OBSERVE','U10_TREE_AUDIT','TARGET_RESTORE_AUDIT','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')}))
        rows=[]
        def launch(label,cmd,tool=None,env=None,allow_counter_denial=False):
            report=out/'runs'/label
            if tool:cmd=['/usr/local/cuda-13.1/bin/compute-sanitizer','--tool',tool,'--error-exitcode','99',*map(str,cmd)]
            result=subprocess.run([sys.executable,r/'deps/locked.py','--gpu',a.gpu,'--numa-node','0','--output',report,'--',*map(str,cmd)],env=env or baseenv,pass_fds=fds)
            receipt=read(report/'receipt.json')
            probe_log=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
            denied=allow_counter_denial and 'ERR_NVGPUCTRPERM' in probe_log
            assert (result.returncode==0 and receipt['runtime_valid']) or denied,('runtime/isolation failure',label)
            assert all(not x['foreign'] for x in read(report/'checks.json'))
            log=(report/'stdout.log').read_text()+(report/'stderr.log').read_text()
            assert not re.search(r'\bFAIL\s*:|Error!!!|cuda.{0,60}(?:error|failed)',log,re.I),log[-1000:]
            if tool:assert ('RACECHECK SUMMARY: 0 hazards' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
            rec=dict(label=label,sanitizer=tool,receipt_sha256=sha(report/'receipt.json'));rows.append(rec);print('RUNTIME',phase,label,flush=True);return rec
        def quality(label,case,mode='P0',tool=None,profiler=None,count=False):
            case=cases/case;data=a.data if case.name=='target' else case/'data.f32bin';prefix=out/'outputs'/label
            env={**baseenv,'PE_TRACE':str(case/'trace')};cmd=[r/mode/('count' if count else 'bench'),data,case/'events.txt','2',str(c['shape']['radius']),prefix,'8']
            if count:
                dump=out/('work_'+mode);dump.mkdir();env['FIXED3_WORK_DIR']=str(dump)
            if profiler:cmd=[*profiler,*cmd]
            rec=launch(label,cmd,tool,env)
            ref=a.reference if case.name=='target' else None
            q={suffix or 'measured':check(data,case/events,str(case/'trace')+suffix,str(prefix)+suffix,'P',str(ref)+suffix if ref else None) for suffix,events in [('','events.txt'),('.warmup','warmup.events')]}
            save(str(prefix)+'.quality.json',q);rec['quality_sha256']=sha(str(prefix)+'.quality.json');print('VALIDATED',phase,label,flush=True)
        def equal(labels,unit=False):
            for suffix in (['.bin'] if unit else ['.ids.i32','.dist.f32','.final.i32','.warmup.ids.i32','.warmup.dist.f32','.warmup.final.i32']):assert len({sha(out/'outputs'/(x+suffix)) for x in labels})==1,('output drift',labels,suffix)
        try:
            if phase=='qualify':
                for m in ('P0','P1','P2'):launch('unit_'+m,[r/m/'unit',out/'outputs'/('unit_'+m+'.bin')])
                equal(['unit_'+m for m in ('P0','P1','P2')],True)
                for m in ('P1','P2'):
                    for tool in ('memcheck','racecheck','synccheck'):
                        label='unit_'+m+'_'+tool;launch(label,[r/m/'unit',out/'outputs'/(label+'.bin')],tool);equal(['unit_P0',label],True)
                for m in ('P0','P1','P2'):quality('bounded_'+m,'bounded',m)
                equal(['bounded_'+m for m in ('P0','P1','P2')])
                for m in ('P1','P2'):
                    for tool in ('memcheck','racecheck','synccheck'):
                        label='bounded_'+m+'_'+tool;quality(label,'bounded',m,tool);equal(['bounded_P0',label])
                for m in ('P0','P1','P2'):quality('target_'+m,'target',m)
                equal(['target_'+m for m in ('P0','P1','P2')])
            elif phase=='work':
                for m in ('P0','P1','P2'):quality(m,'target',m,count=True)
                equal(['P0','P1','P2'])
                files=sorted((out/'work_P0').glob('*.bin'),key=lambda x:int(x.stem));assert len(files)==132
                counts=[]
                for f in files:
                    assert sha(f)==sha(out/'work_P1'/f.name)==sha(out/'work_P2'/f.name),('work drift',f.name);counts.append(work(f))
                save(out/'WORK.json',dict(bit_identical=True,warmup_rows=counts[:4],measured_rows=counts[4:]))
            elif phase=='profile':
                # One counter-permission probe; diagnostic-only and no driver-policy change.
                probe=out/'ncu_probe';probe.mkdir();rec=launch('ncu_probe',['/usr/local/cuda-13.1/bin/ncu','--kernel-name-base','demangled','--kernel-name','regex:.*verify_materialized.*','--launch-count','1','--section','LaunchStats',r/'P0/unit',probe/'unit.bin'],allow_counter_denial=True)
                text=(out/'runs/ncu_probe/stdout.log').read_text()+(out/'runs/ncu_probe/stderr.log').read_text()
                denied='ERR_NVGPUCTRPERM' in text
                if not denied:assert 'Launch Statistics' in text or 'LaunchStats' in text,'NCU admission ambiguous'
                results={};expected=read(r/'work/WORK.json')['measured_rows']
                for number,order in enumerate(c['profile_orders'],1):
                    for m in order:
                        label=f'r{number}_{m}';prefix=['/usr/local/cuda-13.1/bin/nsys','profile','--trace=cuda,nvtx,osrt','--sample=none','--cpuctxsw=none','--force-overwrite=false','--env-var=NSYS_NVTX_PROFILER_REGISTER_ONLY=0','-o',out/label]
                        quality(label,'target',m,profiler=prefix)
                        subprocess.run(['/usr/local/cuda-13.1/bin/nsys','export','--type=sqlite','--output',out/(label+'.sqlite'),out/(label+'.nsys-rep')],check=True)
                        observed=results[label]=trace(out/(label+'.sqlite'))
                        for got,wanted in zip(observed['rows'],expected):assert got['ctas']==wanted[m+'_ctas'] and got['threads']==(256 if m=='P0' else 32)
                    equal([f'r{number}_{m}' for m in ('P0','P1','P2')])
                accepted=all(results[f'r{i}_P2']['leaf_inclusive_ms']<results[f'r{i}_P1']['leaf_inclusive_ms'] for i in (1,2))
                save(out/'MECHANISM.json',dict(results=results,NCU_denied=denied,unsupported=['issued instructions','DRAM/L2 traffic','hardware occupancy','branch efficiency'],physical_evidence='NSYS actual grid/block, same work, leaf duration; not scheduling-overhead hardware counter',P1_leaf_improves_both=all(results[f'r{i}_P1']['leaf_inclusive_ms']<results[f'r{i}_P0']['leaf_inclusive_ms'] for i in (1,2)),pass_gate_E=accepted))
            else:
                for number,order in enumerate(c['formal_orders'],1):
                    for m in order:quality(f'r{number}_{m}','target',m)
                    equal([f'r{number}_{m}' for m in ('P0','P1','P2')])
                save(out/'SUMMARY.json',formal(out,c))
            assert all(sha(r/name)==h for name,h in inputs.items()),'campaign input drift'
            assert all(sha(a.checker/name)==h for name,h in checkpins.items()),'checker drift'
            gate=dict(passed=True,rows=rows,outputs={str(x.relative_to(out)):sha(x) for x in out.rglob('*') if x.is_file()})
            if phase=='profile':gate['pass_gate_E']=accepted
            save(out/'GATE.json',gate);print('PASS',phase,flush=True)
        except Exception:
            (out/'FAILURE.txt').write_text(traceback.format_exc());save(out/'FAILED.json',dict(passed=False,rows=rows));raise
if __name__=='__main__':main()
