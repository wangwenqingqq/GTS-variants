#!/usr/bin/env python3
"""Exactly24 authorized primaries after the immutable4+44 prefix; no retry loop."""
import argparse,fcntl,json,math,os,shutil,subprocess,sys,time
from pathlib import Path
import static_campaign as c
import static_second_stop
from static_guard import classify_apps
from static_preflight import inspect,TREE,FAISS
from static_check import check,read,requests
from qualify import cpu
HERE=Path(__file__).resolve().parent

def jobs():return c.jobs('primary')[48:]
def sources():
    names=['STATIC_RECOVERY2.json','static_recovery2.py','static_guard.py','static_second_stop.py','test_static_guard.py','test_static_recovery2.py','evidence/STATIC_SECOND_STOP.json']
    return {**c.sources(),**{n:cpu.sha(HERE/n) for n in names}}

def prior_public(path):
    assert cpu.sha(path)==read(HERE/'STATIC_RECOVERY2.json')['published_second_stop_sha256']
    return read(path)

def live_guard(path,expected):assert cpu.sha(path)==expected

def structure(rows,attempts,guards,complete):
    labels=[j['label'] for j in jobs()]
    assert list(rows)==labels[:len(rows)] and len(rows)<=24
    assert attempts==guards==set(labels[:len(attempts)]) and len(attempts)<=24
    assert len(rows)<=len(attempts)<=min(24,len(rows)+1)
    if complete:assert list(rows)==labels and attempts==set(labels)

def guard_check(folder):
    hashes=c.guard_check(folder);receipt=read(folder/'receipt.json')
    assert receipt['observer']=='two-sided-starttime-v1' and receipt['child_pid']>0
    for row in read(folder/'checks.json'):
        before={int(k):v for k,v in row['owned_before'].items()};after={int(k):v for k,v in row['owned_after'].items()}
        live={r['pid']:r['current_starttime'] for r in row['identities']}
        foreign,observations=classify_apps(row['apps'],before,after,live)
        assert foreign==row['foreign']==[] and observations==row['identities']
        assert math.isfinite(row['seconds']) and row['seconds']>=0
    return hashes

def old_args(a):return argparse.Namespace(**{**vars(a),'guard':a.prior_guard})

def preflight(a):
    contract=read(HERE/'STATIC_RECOVERY2.json');assert len(jobs())==contract['new_attempts']==24
    assert jobs()[0]['label']==contract['first_label'] and cpu.sha(HERE/'STATIC_CONTRACT.json')==contract['original_contract_sha256']
    public=prior_public(HERE/'evidence/STATIC_SECOND_STOP.json')
    assert cpu.sha(a.prior_proof)==public['private_verification_sha256']
    prior=static_second_stop.inspect(old_args(a));assert prior==read(a.prior_proof)
    dependencies=dict(tree=inspect(a.cpu_python,TREE),faiss=inspect(a.gpu_python,FAISS))
    assert dependencies==read(a.work/'recovery/DEPENDENCIES_PREFLIGHT.json')
    tests={}
    for name in ('test_static_guard.py','test_static_recovery2.py'):
        r=subprocess.run([sys.executable,str(HERE/name)],text=True,capture_output=True,check=True)
        tests[name]=dict(source_sha256=cpu.sha(HERE/name),stdout=r.stdout,stderr=r.stderr)
    assert cpu.sha(a.guard)==cpu.sha(HERE/'static_guard.py')
    return dict(passed=True,scope='offline full48-row binding, import-only dependencies and CPU-only guard tests; zero native/GPU primaries',prior_proof_sha256=cpu.sha(a.prior_proof),source_sha256=sources(),guard_sha256=cpu.sha(a.guard),prior_guard_sha256=cpu.sha(a.prior_guard),dependencies=dependencies,interpreters={str(p):cpu.sha(p) for p in (Path(sys.executable),a.cpu_python,a.gpu_python)},tests=tests,gpu=a.gpu,numa_node=a.numa_node)

def command(a,job,stage,inputs,write=False):
    label=job['label'];r=inputs['records'][job['snapshot']];schedule=requests(r['qids'],job['method'],job['order'])
    req=stage/'requests'/(label+'.txt');prefix=stage/'outputs'/label
    content=str(len(schedule))+'\n'+''.join(f"{0 if t=='knn' else 1} {q} 0.705625057220459 8\n" for t,q in schedule)
    if write:req.write_text(content)
    else:assert req.read_text()==content
    if job['method']=='GTSPP_P':
        events=stage/'requests'/(label+'.events');content='80\n'+''.join(f"{3 if t=='knn' else 2} {q}\n" for t,q in schedule)
        if write:events.write_text(content)
        else:assert events.read_text()==content
        native=[str(a.build/'bin/target'),r['data'],str(events),'2','0.705625057220459',str(prefix),'8']
    elif job['method']=='GPU_RANGE_COMPLETE':native=[str(a.build/'bin/range_static'),r['data'],str(req),str(prefix)]
    else:
        py=a.gpu_python if job['method'] in ('GPU_FLAT_KNN','CPU_FLAT') else a.cpu_python
        native=[str(py),str(HERE/'static_native.py'),'--method',job['method'],'--data',r['data'],'--snapshot',r['snapshot'],'--output',str(prefix),'--order',job['order']]
    return [sys.executable,str(HERE/'static_process.py'),'--record',str(stage/(label+'.process.json')),'--',*native],cpu.sha(req)

def row_check(a,job,stage,inputs,reg):
    label=job['label'];folder=stage/'guards'/label;hashes=guard_check(folder)
    receipt=read(folder/'receipt.json');attempt=read(stage/(label+'.attempt.json'))
    cmd,request_sha=command(a,job,stage,inputs)
    assert attempt['registration_sha256']==cpu.sha(stage/'REGISTERED.json')
    assert attempt['command']==receipt['command'][3:]==cmd and receipt['command']==read(folder/'command.json')
    assert attempt['request_sha256']==request_sha and attempt['environment']==reg['environment']
    assert receipt['command'][:3]==['numactl',f'--cpunodebind={a.numa_node}',f'--membind={a.numa_node}'] and receipt['gpu']==a.gpu
    assert receipt['binary_sha256']==cpu.sha(sys.executable)
    process=read(stage/(label+'.process.json'));assert process['returncode']==0
    assert all(math.isfinite(process[k]) and process[k]>=0 for k in ('wall_s','cpu_user_s','cpu_system_s','max_rss_bytes'))
    ref=a.work/'reference'/job['snapshot'];gold=read(ref/'REFERENCE.json');gold['folder']=ref
    r=inputs['records'][job['snapshot']];result=check(stage/'outputs'/label,job['method'],requests(r['qids'],job['method'],job['order']),gold)
    if job['method']=='GTSPP_P':assert result['canonical_sha256']==read(a.work/'qualification/ROWS.json')['P_'+job['snapshot']]['canonical_sha256']
    return result,hashes

def run(a):
    a.work=c.outside_repo(a.work);stage=a.work/'recovery2';assert not stage.exists()
    with (a.work/'campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        proof=preflight(a);assert proof==read(a.preflight)
        inputs=read(a.work/'INPUTS.json');old=read(a.work/'recovery/REGISTERED.json');built=read(a.build/'BUILD.json')
        assert (a.gpu,a.numa_node)==(old['gpu'],old['numa_node'])
        env={k:v for k,v in os.environ.items() if not k.startswith(('BUILD_','TARGET_','PAR_','KNN_','U10_','REGION_'))}
        libs=read(a.build/'BUILD_REGISTERED.json')['library_search_dirs'];env['LD_LIBRARY_PATH']=':'.join(libs+['/usr/local/cuda-13.1/lib64',env.get('LD_LIBRARY_PATH','')]);env.update(old['environment'])
        stage.mkdir();(stage/'requests').mkdir();(stage/'outputs').mkdir()
        reg=dict(jobs=jobs(),registered_unix=time.time(),contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),recovery_contract_sha256=cpu.sha(HERE/'STATIC_RECOVERY2.json'),source_sha256=sources(),preflight_sha256=cpu.sha(a.preflight),prior_proof_sha256=cpu.sha(a.prior_proof),build_sha256=cpu.sha(a.build/'BUILD.json'),binaries=built['binaries'],inputs_sha256=cpu.sha(a.work/'INPUTS.json'),guard_sha256=cpu.sha(a.guard),prior_guard_sha256=cpu.sha(a.prior_guard),environment=old['environment'],gpu=a.gpu,numa_node=a.numa_node,interpreters=proof['interpreters'])
        cpu.save(stage/'REGISTERED.json',reg);shutil.copyfile(__file__,stage/'EXECUTED.py');shutil.copyfile(a.preflight,stage/'PREFLIGHT.json');rows={};guards={}
        for job in jobs():
            live_guard(a.guard,reg['guard_sha256'])
            assert reg['source_sha256']==sources() and all(cpu.sha(p)==h for p,h in reg['interpreters'].items())
            assert reg['build_sha256']==cpu.sha(a.build/'BUILD.json') and all(cpu.sha(a.build/'bin'/n)==h for n,h in reg['binaries'].items())
            label=job['label'];cmd,request_sha=command(a,job,stage,inputs,True)
            cpu.save(stage/(label+'.attempt.json'),dict(started_unix=time.time(),registration_sha256=cpu.sha(stage/'REGISTERED.json'),command=cmd,request_sha256=request_sha,environment=reg['environment']))
            with (stage/(label+'.outer.log')).open('x') as log:
                rc=subprocess.run([sys.executable,str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(stage/'guards'/label),'--',*cmd],env=env,stdout=log,stderr=log).returncode
            if rc:raise RuntimeError(f'{label} failed; retain all evidence, no automatic replacement')
            live_guard(a.guard,reg['guard_sha256'])
            assert reg['source_sha256']==sources()
            rows[label],guards[label]=row_check(a,job,stage,inputs,reg);cpu.save(stage/'ROWS.json',rows)
            print('PASS',label,{k:v for k,v in rows[label]['timing'].items() if k.endswith('_pass_ms')},flush=True)
        verify(a,require_complete=False)
        cpu.save(stage/'COMPLETE.json',dict(passed=True,registration_sha256=cpu.sha(stage/'REGISTERED.json'),rows=rows,guard_hashes=guards))

def verify(a,require_complete=True):
    stage=a.work/'recovery2';reg=read(stage/'REGISTERED.json');rows=read(stage/'ROWS.json')
    complete=(stage/'COMPLETE.json').exists();assert not require_complete or complete
    structure(rows,{p.name[:-len('.attempt.json')] for p in stage.glob('*.attempt.json')},c.guard_labels(stage/'guards'),complete)
    assert len(rows)==24 and reg['jobs']==jobs() and reg['source_sha256']==sources()
    assert cpu.sha(stage/'EXECUTED.py')==cpu.sha(__file__) and cpu.sha(stage/'PREFLIGHT.json')==reg['preflight_sha256']==cpu.sha(a.preflight)
    assert read(a.preflight)==preflight(a)
    for k,v in dict(guard_sha256=cpu.sha(a.guard),prior_guard_sha256=cpu.sha(a.prior_guard),prior_proof_sha256=cpu.sha(a.prior_proof),build_sha256=cpu.sha(a.build/'BUILD.json'),inputs_sha256=cpu.sha(a.work/'INPUTS.json'),recovery_contract_sha256=cpu.sha(HERE/'STATIC_RECOVERY2.json'),contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),gpu=a.gpu,numa_node=a.numa_node).items():assert reg[k]==v
    assert reg['environment']==read(a.work/'recovery/REGISTERED.json')['environment'] and reg['binaries']==read(a.build/'BUILD.json')['binaries']
    inputs=read(a.work/'INPUTS.json');guards={}
    for job in jobs():
        actual,guards[job['label']]=row_check(a,job,stage,inputs,reg);assert actual==rows[job['label']]
    if complete:assert read(stage/'COMPLETE.json')==dict(passed=True,registration_sha256=cpu.sha(stage/'REGISTERED.json'),rows=rows,guard_hashes=guards)
    return dict(passed=True,new_primary_attempts=24,preserved_valid=48,retained_failures=2,valid_total=72,total_primary_attempts_including_RTP=92,registration_sha256=cpu.sha(stage/'REGISTERED.json'),rows_sha256=cpu.sha(stage/'ROWS.json'),guard_hashes=guards,source_sha256=sources())

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preflight','run','verify'])
    for k in ('work','build','guard','prior-guard','prior-proof','qualification-source','original-source','cpu-python','gpu-python','preflight'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--output',type=Path);p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True);a=p.parse_args();assert __debug__
    if a.action=='run':run(a)
    else:
        out=c.outside_repo(a.preflight if a.action=='preflight' else a.output);assert not out.exists()
        cpu.save(out,(preflight if a.action=='preflight' else verify)(a));print('PASS',a.action,flush=True)
