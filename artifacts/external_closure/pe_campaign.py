#!/usr/bin/env python3
"""Bounded logical P/E campaign. Stop at the first failure, never auto-replace."""
if not __debug__:raise RuntimeError('Python assertions must remain enabled')
import argparse,json,os,subprocess,sys,time,traceback
from pathlib import Path
import numpy as np
from common import outside_repo
from pe_trace import freeze,warm_events
from pe_check import check
from qualify import cpu
HERE=Path(__file__).resolve().parent
read=lambda p:json.loads(Path(p).read_text())
CONTRACT=read(HERE/'PE_CONTRACT.json')

def source_hashes():
    paths=list(HERE.glob('pe*'))+[HERE/'PE_CONTRACT.json',HERE/'static_guard.py',HERE/'range_service.cu',HERE/'qualify.py',HERE/'common.py',HERE.parent/'rebuild_tree_baselines/cpu.py',HERE.parent/'unified_target_workflow/validate.py']
    return {str(p.relative_to(HERE.parent.parent)):cpu.sha(p) for p in paths if p.is_file()}

def fixtures(a):
    w=a.work/'cases';w.mkdir();x=cpu.validate.verify_target_data(a.data)
    ops=cpu.validate.boundary_operations(4096)
    # Include initial duplicates and both base/buffer deletion; all original finite inputs.
    small=np.array(x[:4096],copy=True);small[1]=small[0]
    cpu.validate.case(small,w/'bounded',ops)
    empty=[(2,0),(3,0)]+[(1,0)]*255+[(2,0),(3,0),(0,0),(2,0),(3,0)]
    cpu.validate.case(np.array(x[:255]),w/'empty',empty)
    (w/'target').mkdir();(w/'target/events.txt').write_bytes(a.events.read_bytes())
    for name in ('bounded','empty','target'):
        d=a.data if name=='target' else w/name/'data.f32bin'
        freeze(d,w/name/'events.txt',w/name/'trace')
        ev=warm_events();(w/name/'warmup.events').write_text(str(len(ev))+'\n'+''.join(f'{f} {i}\n' for f,i in ev))

def jobs(stage):
    if stage=='primary':return [dict(label=f'round_{r}_{m}',method=m,case='target',tool=None,round=r,order=order) for r,order in enumerate(CONTRACT['orders'],1) for m in order]
    out=[dict(label=m+'_bounded',method=m,case='bounded',tool=None) for m in 'PE']
    out += [dict(label=m+'_'+tool,method=m,case='bounded',tool=tool) for m in 'PE' for tool in ('memcheck','racecheck','synccheck')]
    out += [dict(label=m+'_target',method=m,case='target',tool=None) for m in 'PE']
    out += [dict(label='E_empty_tail',method='E',case='empty',tool=None)]
    assert len(out)<=CONTRACT['qualification_budget'];return out

def reference(a):
    expected=next(r for r in read(HERE/'evidence/RTP_RESULTS.json')['rows'] if r['label']=='round_1_P')['output_hashes']
    for n,v in expected.items():assert cpu.sha(a.reference.parent/n)==v,('prior gold binding',n)
    return expected

def register(a):
    a.work=outside_repo(a.work);a.work.mkdir(exist_ok=False,parents=True);fixtures(a)
    reg=dict(contract_sha256=cpu.sha(HERE/'PE_CONTRACT.json'),source_hashes=source_hashes(),p_build_sha256=cpu.sha(a.p_build/'BUILD.json'),e_build_sha256=cpu.sha(a.e_build/'BUILD.json'),
        binaries={'P':cpu.sha(a.p_build/'bin/target'),'E':cpu.sha(a.e_build/'scan')},reference=reference(a),gpu=a.gpu,numa_node=a.numa_node,data_sha256=cpu.sha(a.data),
        cases={str(p.relative_to(a.work/'cases')):cpu.sha(p) for p in (a.work/'cases').rglob('*') if p.is_file()},qualification_jobs=jobs('qualification'),primary_jobs=jobs('primary'),registered_unix=time.time())
    cpu.save(a.work/'REGISTERED.json',reg)

def recover(a):
    a.work=outside_repo(a.work)
    original=read(a.work/'REGISTERED.json');failed=read(a.work/'qualification/RESULTS.json')
    assert not (a.work/'RECOVERY.json').exists() and not (a.work/'recovery').exists()
    assert not failed['complete'] and failed['rows'][0]['label']=='P_bounded' and failed['rows'][0]['status']=='failed'
    assert all(r['status']=='not_executed_after_stop' for r in failed['rows'][1:])
    receipt=read(a.work/'qualification/guards/P_bounded/receipt.json');assert receipt['runtime_valid']
    c=a.work/'cases/bounded';p=a.work/'qualification/outputs/P_bounded'
    recheck={suffix or 'measured':check(c/'data.f32bin',c/events,str(c/'trace')+suffix,str(p)+suffix,'P')
             for suffix,events in (('','events.txt'),('.warmup','warmup.events'))}
    updated={**original,'source_hashes':source_hashes(),'original_registration_sha256':cpu.sha(a.work/'REGISTERED.json'),
        'original_failure_sha256':cpu.sha(a.work/'qualification/RESULTS.json'),'first_sample_offline_recheck':recheck,
        'authorized_scope':'human-approved checker repair; no rerun of P_bounded; remaining10 qualifiers then original12 primaries only if qualified',
        'recovery_jobs':jobs('qualification')[1:],'registered_unix':time.time()}
    cpu.save(a.work/'RECOVERY.json',updated)

def run(a):
    a.work=outside_repo(a.work)
    registration=a.work/('RECOVERY.json' if a.stage in ('recovery','primary') and (a.work/'RECOVERY.json').exists() else 'REGISTERED.json')
    reg=read(registration);assert reg['source_hashes']==source_hashes() and reg['reference']==reference(a)
    assert reg['contract_sha256']==cpu.sha(HERE/'PE_CONTRACT.json') and reg['data_sha256']==cpu.sha(a.data)
    assert reg['gpu']==a.gpu and reg['numa_node']==a.numa_node
    assert all(cpu.sha(a.work/'cases'/p)==v for p,v in reg['cases'].items())
    if a.stage=='primary':
        if registration.name=='RECOVERY.json':
            q=read(a.work/'recovery/RESULTS.json');assert q['complete'] and len(q['rows'])==len(jobs('qualification'))-1
            assert all(r['status']=='passed' for r in q['rows']) and all(v['passed'] for v in reg['first_sample_offline_recheck'].values())
        else:
            q=read(a.work/'qualification/RESULTS.json');assert q['complete'] and len(q['rows'])==len(jobs('qualification')) and all(r['status']=='passed' for r in q['rows'])
    out=a.work/a.stage;out.mkdir(exist_ok=False);(out/'outputs').mkdir();selected=jobs('qualification')[1:] if a.stage=='recovery' else jobs(a.stage);rows=[]
    env={**os.environ,**read(a.e_build/'REGISTERED.json')['environment'], 'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','REGION_MODE':'PAR_STRONG','BUILD_MAPPING':'TILED','KNN_MODE':'FULL','TARGET_WARMUP':'1','U10_OBSERVE':'1','U10_TREE_AUDIT':'0','TARGET_RESTORE_AUDIT':'0'}
    # Freeze all intended jobs and runtime identities before the first new GPU process.
    cpu.save(out/'REGISTERED.json',dict(parent_sha256=cpu.sha(registration),jobs=selected,environment={k:env[k] for k in ('LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','REGION_MODE','BUILD_MAPPING','KNN_MODE','TARGET_WARMUP','U10_OBSERVE','U10_TREE_AUDIT','TARGET_RESTORE_AUDIT')},before_execution=True))
    failed=False
    for j in selected:
        row={**j,'status':'not_executed_after_stop'}
        if failed:rows.append(row);continue
        try:
            case=a.work/'cases'/j['case'];data=a.data if j['case']=='target' else case/'data.f32bin';prefix=out/'outputs'/j['label'];binary=a.p_build/'bin/target' if j['method']=='P' else a.e_build/'scan'
            assert cpu.sha(binary)==reg['binaries'][j['method']]
            cmd=[str(binary),str(data),str(case/'events.txt'),'2',str(CONTRACT['shape']['radius']),str(prefix),'8'] if j['method']=='P' else [str(binary),str(data),str(case/'trace'),str(CONTRACT['shape']['radius']),str(prefix)]
            if j['tool']:cmd=[a.sanitizer,'--tool',j['tool'],'--error-exitcode','97',*cmd]
            e={**env,'PE_TRACE':str(case/'trace')};cpu.save(out/(j['label']+'.command.json'),dict(command=cmd,env={k:e[k] for k in ('LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','REGION_MODE','BUILD_MAPPING','KNN_MODE','TARGET_WARMUP','U10_OBSERVE','PE_TRACE')}))
            result=subprocess.run([sys.executable,str(HERE/'static_guard.py'),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(out/'guards'/j['label']),'--',*cmd],env=e,capture_output=True,text=True)
            (out/(j['label']+'.outer.log')).write_text(result.stdout+result.stderr);row['guard_exit']=result.returncode
            assert result.returncode==0,'runtime/isolation failure'
            guard=read(out/'guards'/j['label']/'receipt.json');assert guard['runtime_valid']
            if j['tool']:
                text=(out/'guards'/j['label']/'stdout.log').read_text()+(out/'guards'/j['label']/'stderr.log').read_text()
                assert 'ERROR SUMMARY: 0 errors' in text or 'RACECHECK SUMMARY: 0 hazards' in text,'missing clean sanitizer summary'
            ref=a.reference if j['case']=='target' else None
            quality=check(data,case/'events.txt',case/'trace',prefix,j['method'],ref)
            warm=check(data,case/'warmup.events',str(case/'trace')+'.warmup',str(prefix)+'.warmup',j['method'],str(ref)+'.warmup' if ref else None)
            cpu.save(str(prefix)+'.quality.json',dict(measured=quality,warmup=warm));row.update(status='passed',quality_sha256=cpu.sha(str(prefix)+'.quality.json'),receipt_sha256=cpu.sha(out/'guards'/j['label']/'receipt.json'))
        except Exception as error:
            row.update(status='failed',error=str(error));(out/(j['label']+'.failure.txt')).write_text(traceback.format_exc());failed=True
        rows.append(row);cpu.save(out/'RESULTS.json',dict(complete=not failed and len(rows)==len(selected),rows=rows));print(row,flush=True)
    cpu.save(out/'RESULTS.json',dict(complete=not failed and len(rows)==len(selected),rows=rows))
    if failed:raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('register','recover','run'));p.add_argument('--stage',choices=('qualification','recovery','primary'),default='qualification')
    for n in ('work','data','events','reference','p-build','e-build'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True);p.add_argument('--sanitizer',default='/usr/local/cuda-13.1/bin/compute-sanitizer')
    a=p.parse_args();assert __debug__;{'register':register,'recover':recover,'run':run}[a.action](a)
