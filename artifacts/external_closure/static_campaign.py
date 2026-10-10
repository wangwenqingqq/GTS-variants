#!/usr/bin/env python3
"""Frozen six-method static matrix; fail closed and retain every fresh process."""
import argparse,csv,fcntl,json,os,shutil,subprocess,sys,time
from pathlib import Path
from common import outside_repo
from qualify import cpu
from static_check import requests,reference,check,read
HERE=Path(__file__).resolve().parent
CONTRACT=read(HERE/'STATIC_CONTRACT.json')
SOURCES=['STATIC_CONTRACT.json','static_campaign.py','static_check.py','static_native.py','static_process.py','native_cpu.py','qualify.py','common.py','../rebuild_tree_baselines/cpu.py','../unified_target_workflow/validate.py']
def sources():return {name:cpu.sha(HERE/name) for name in SOURCES}

def jobs(stage):
    if stage=='qualification':
        return [dict(label=name,method='GTSPP_P' if name.startswith('P_') else 'GPU_RANGE_COMPLETE',snapshot='initial' if name=='P_initial' else 'first_rebuilt' if name=='P_first_rebuilt' else 'bounded',order='knn,range',tool=next((t for t in ('memcheck','racecheck','synccheck') if name.endswith(t)),None)) for name in CONTRACT['qualifiers']]
    return [dict(label=f'{snap}_r{r}_{m}',method=m,snapshot=snap,round=r,order=CONTRACT['task_orders'][r-1],tool=None) for snap in CONTRACT['snapshots'] for r,order in enumerate(CONTRACT['orders'],1) for m in order if m!='GPU_TREE_ADAPT']

def prepare(a):
    a.work=outside_repo(a.work);a.work.mkdir(parents=True,exist_ok=False)
    (a.work/'requests').mkdir();records={}
    original=read(a.snapshots/'REGISTERED.json')
    for r in original['records']:
        folder=Path(r['folder']);spec=read(folder/'SNAPSHOT.json');data=Path(r['data'])
        assert cpu.sha(data)==spec['data_sha256'] and cpu.sha(folder/'lineage.npy')==spec['lineage_sha256']
        records[r['name']]=dict(data=str(data),snapshot=str(folder),data_sha256=spec['data_sha256'],snapshot_sha256=cpu.sha(folder/'SNAPSHOT.json'),qids=[q['physical_qid'] for q in spec['queries']])
    data=a.bounded;records['bounded']=dict(data=str(data),data_sha256=cpu.sha(data),qids=list(range(32)))
    for name,r in records.items():
        reference(Path(r['data']),r['qids'],a.library,a.work/'reference'/name)
        r['reference_sha256']=cpu.sha(a.work/'reference'/name/'REFERENCE.json')
    cpu.save(a.work/'INPUTS.json',dict(records=records,source_snapshot_registration_sha256=cpu.sha(a.snapshots/'REGISTERED.json'),contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json')))
    print('PASS frozen snapshots and exhaustive independent reference',flush=True)

def verify_inputs(work):
    inputs=read(work/'INPUTS.json');assert inputs['contract_sha256']==cpu.sha(HERE/'STATIC_CONTRACT.json')
    for name,r in inputs['records'].items():
        assert cpu.sha(r['data'])==r['data_sha256']
        if 'snapshot' in r:assert cpu.sha(Path(r['snapshot'])/'SNAPSHOT.json')==r['snapshot_sha256']
        folder=work/'reference'/name;ref=read(folder/'REFERENCE.json');assert cpu.sha(folder/'REFERENCE.json')==r['reference_sha256'] and ref['data_sha256']==r['data_sha256']
        assert all(cpu.sha(folder/(q+'.f64'))==h for q,h in ref['files'].items())
    return inputs

def guard_check(folder):
    receipt=read(folder/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
    assert read(folder/'before.json')['apps']==read(folder/'after.json')['apps']==''
    checks=read(folder/'checks.json');assert checks and all(not r['foreign'] for r in checks)
    return {p.name:cpu.sha(p) for p in folder.iterdir() if p.is_file()}

def guard_labels(folder):
    return {p.name for p in folder.iterdir() if p.is_dir()}

def admission_structure(admitted,reg,actual_labels,binding):
    expected={j['label'] for j in jobs('qualification')}
    assert admitted['passed'] and admitted['jobs']==reg['jobs']==jobs('qualification')
    assert set(admitted['rows'])==set(admitted['guard_hashes'])==actual_labels==expected
    assert all(row['passed'] for row in admitted['rows'].values())
    for key in ('contract_sha256','build_sha256','source_sha256'):assert admitted[key]==reg[key]
    for key,value in binding.items():
        if key=='registration_sha256':assert admitted[key]==value
        else:assert reg[key]==value,(key,reg.get(key),value)

def qualification_gate(a):
    folder=a.work/'qualification';admitted=read(folder/'ADMISSION.json');reg=read(folder/'REGISTERED.json')
    source=sources()
    for name in ('static_campaign.py','static_check.py'):source[name]=cpu.sha(a.qualification_source/name)
    assert source['static_campaign.py']==cpu.sha(folder/'EXECUTED.py')
    admission_structure(admitted,reg,guard_labels(folder/'guards'),
        dict(registration_sha256=cpu.sha(folder/'REGISTERED.json'),inputs_sha256=cpu.sha(a.work/'INPUTS.json'),
             contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),build_sha256=cpu.sha(a.build/'BUILD.json'),
             guard_sha256=cpu.sha(a.guard),gpu=a.gpu,numa_node=a.numa_node,source_sha256=source))
    assert read(folder/'ROWS.json')==admitted['rows']
    inputs=read(a.work/'INPUTS.json')['records']
    for job in jobs('qualification'):
        label=job['label'];guard=folder/'guards'/label
        assert guard_check(guard)==admitted['guard_hashes'][label]
        receipt=read(guard/'receipt.json');command=read(folder/(label+'.command.json'))
        assert receipt['gpu']==a.gpu and receipt['command'][1:3]==[f'--cpunodebind={a.numa_node}',f'--membind={a.numa_node}']
        assert receipt['command'][3:]==command['command'] and command['environment']==reg['environment']
        assert command['request_sha256']==cpu.sha(a.work/'requests'/(label+'.txt'))
        assert read(folder/(label+'.process.json'))['returncode']==0
        r=inputs[job['snapshot']];gold=read(a.work/'reference'/job['snapshot']/'REFERENCE.json');gold['folder']=a.work/'reference'/job['snapshot']
        actual=check(folder/'outputs'/label,job['method'],requests(r['qids'],job['method'],job['order']),gold)
        assert actual==admitted['rows'][label]
        if job['tool']:
            log=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
    return admitted

def run(a):
    a.work=outside_repo(a.work);inputs=verify_inputs(a.work);stage=a.work/a.stage;stage.mkdir(exist_ok=False);(stage/'outputs').mkdir()
    if a.stage=='primary':admitted=qualification_gate(a)
    build=read(a.build/'BUILD.json');assert all(cpu.sha(a.build/'bin'/n)==h for n,h in build['binaries'].items())
    prepared=read(a.build/'PREPARED.json');assert all(cpu.sha(a.build/'source'/n)==h for n,h in prepared['sources'].items())
    env={k:v for k,v in os.environ.items() if not k.startswith(('BUILD_','TARGET_','PAR_','KNN_','U10_','REGION_'))}
    libs=read(a.build/'BUILD_REGISTERED.json')['library_search_dirs'];env['LD_LIBRARY_PATH']=':'.join(libs+['/usr/local/cuda-13.1/lib64',env.get('LD_LIBRARY_PATH','')])
    env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',REGION_MODE='PAR_STRONG',KNN_MODE='FULL',BUILD_MAPPING='TILED',TARGET_WARMUP='0',U10_OBSERVE='1',U10_TREE_AUDIT='0',TARGET_RESTORE_AUDIT='0')
    reg=dict(jobs=jobs(a.stage),contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),source_sha256=sources(),build_sha256=cpu.sha(a.build/'BUILD.json'),binaries=build['binaries'],inputs_sha256=cpu.sha(a.work/'INPUTS.json'),guard_sha256=cpu.sha(a.guard),gpu=a.gpu,numa_node=a.numa_node,registered_unix=time.time(),environment={k:env[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','REGION_MODE','KNN_MODE','BUILD_MAPPING','TARGET_WARMUP','U10_OBSERVE','U10_TREE_AUDIT','TARGET_RESTORE_AUDIT')})
    if a.stage=='primary':reg['qualification_registration_sha256']=admitted['registration_sha256'];reg['qualification_executed_sha256']=cpu.sha(a.work/'qualification/EXECUTED.py');reg['qualification_checker_sha256']=cpu.sha(a.qualification_source/'static_check.py')
    cpu.save(stage/'REGISTERED.json',reg);shutil.copy2(__file__,stage/'EXECUTED.py');results={};guards={}
    with (a.work/'campaign.lock').open('a+') as lock:
      fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
      for j in reg['jobs']:
        label=j['label'];r=inputs['records'][j['snapshot']];schedule=requests(r['qids'],j['method'],j['order']);prefix=stage/'outputs'/label
        req=a.work/'requests'/(label+'.txt');req.write_text(str(len(schedule))+'\n'+''.join(f"{0 if t=='knn' else 1} {q} 0.705625057220459 8\n" for t,q in schedule))
        if j['method']=='GTSPP_P':
            events=a.work/'requests'/(label+'.events');events.write_text('80\n'+''.join(f"{3 if t=='knn' else 2} {q}\n" for t,q in schedule))
            cmd=[str(a.build/'bin/target'),r['data'],str(events),'2','0.705625057220459',str(prefix),'8']
        elif j['method']=='GPU_RANGE_COMPLETE':cmd=[str(a.build/'bin/range_static'),r['data'],str(req),str(prefix)]
        else:
            py=a.gpu_python if j['method']=='GPU_FLAT_KNN' else a.cpu_python
            cmd=[str(py),str(HERE/'static_native.py'),'--method',j['method'],'--data',r['data'],'--snapshot',r['snapshot'],'--output',str(prefix),'--order',j['order']]
        if j['tool']:cmd=[str(a.sanitizer),'--tool',j['tool'],'--error-exitcode','97',*cmd]
        command=[sys.executable,str(HERE/'static_process.py'),'--record',str(stage/(label+'.process.json')),'--',*cmd];cpu.save(stage/(label+'.command.json'),dict(command=command,request_sha256=cpu.sha(req),environment=reg['environment']))
        folder=stage/'guards'/label
        with (stage/(label+'.outer.log')).open('x') as log:rc=subprocess.run([sys.executable,str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(folder),'--',*command],env=env,stdout=log,stderr=log).returncode
        assert cpu.sha(a.build/'BUILD.json')==reg['build_sha256'] and all(cpu.sha(a.build/'bin'/n)==h for n,h in reg['binaries'].items())
        assert reg['source_sha256']==sources()
        if rc:raise RuntimeError(f'{label} failed; retain all evidence, no replacement')
        guards[label]=guard_check(folder)
        if j['tool']:
            text=(folder/'stdout.log').read_text()+(folder/'stderr.log').read_text();token='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if j['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors';assert token in text
        gold=read(a.work/'reference'/j['snapshot']/'REFERENCE.json');gold['folder']=a.work/'reference'/j['snapshot']
        result=check(prefix,j['method'],schedule,gold)
        if a.stage=='primary' and j['method']=='GTSPP_P':
            prior=admitted['rows']['P_'+j['snapshot']]['canonical_sha256'];assert result['canonical_sha256']==prior
        results[label]=result;cpu.save(stage/'ROWS.json',results)
        print('PASS',label,{k:v for k,v in result['timing'].items() if k.endswith('_pass_ms')},flush=True)
      cpu.save(stage/('ADMISSION.json' if a.stage=='qualification' else 'COMPLETE.json'),dict(passed=True,jobs=reg['jobs'],rows=results,guard_hashes=guards,build_sha256=reg['build_sha256'],source_sha256=reg['source_sha256'],contract_sha256=reg['contract_sha256'],registration_sha256=cpu.sha(stage/'REGISTERED.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--stage',choices=['qualification','primary']);p.add_argument('--numa-node',type=int);p.add_argument('--gpu')
    for k in ('work','snapshots','bounded','library','build','guard','cpu-python','gpu-python','sanitizer','qualification-source'):p.add_argument('--'+k,type=Path,required=k=='work')
    a=p.parse_args();assert __debug__; (prepare if a.action=='prepare' else run)(a)
