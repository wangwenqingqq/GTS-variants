#!/usr/bin/env python3
"""Offline binding for the retained tree diagnostics; never launches a GPU process."""
import argparse,json
from pathlib import Path
import numpy as np
from analyze_trace import analyze
from prepare_trace import sha,outside_repo
from prepare_repair import repair_text
from range_targets import prior_gate,prior_structure,validate_payload,qualify,guard_check

def read(p):return json.loads(Path(p).read_text())
def diagnostic_structure(guards,attempts):
    expected={'native_trace','reuse_trace','bounded_regression','memcheck'}
    assert guards==attempts==expected

def target_structure(rows,guards,attempts,complete):
    expected=['initial','first_rebuilt'];labels=[r['label'] for r in rows]
    assert labels==expected[:len(rows)] and len(rows)<=2
    assert attempts==set(expected[:len(attempts)]) and len(attempts)<=2 and guards==attempts
    assert len(rows)<=len(attempts)<=min(2,len(rows)+1)
    failed=[i for i,r in enumerate(rows) if r['guard_exit'] or not r.get('quality_passed',False)]
    assert not failed or failed==[len(rows)-1] and len(attempts)==len(rows)
    if complete:assert labels==expected and attempts==set(expected) and not failed

def verify(prior,run,static_work,sanitizer):
    diagnostic_structure({p.name for p in (run/'guards').iterdir() if p.is_dir()},
                         {p.name[:-len('.attempt.json')] for p in run.glob('*.attempt.json')})
    trace=analyze(prior,run);reg=read(run/'REPAIR_REGISTERED.json');results=read(run/'REPAIR_RESULTS.json')
    assert reg['conditional_jobs']==['bounded_regression','memcheck','racecheck','synccheck'] and reg['new_budget']==8
    assert [r['label'] for r in results]==['bounded_regression','memcheck']
    assert sha(run/'qualify_repair_v2.py')==reg['script_sha256']
    assert reg['check_sha256']==sha(qualify.__file__) and reg['cpu_quality_sha256']==sha(qualify.cpu.__file__)
    binary=run/'tree_kbound_v2';assert sha(binary)==reg['binary_sha256']
    assert reg['source_sha256']=={str(p.relative_to(run/'repair_source_v2')):sha(p) for p in (run/'repair_source_v2').rglob('*') if p.is_file()}
    parent=prior/'tree_source_safe';assert sha(parent/'SOURCE.json')=='2ae6127690744f640ae7149d95c281321ce2a6f9a4d325147b8279baecef9c6d'
    assert read(parent/'SOURCE.json')['output_headers']=={p.name:sha(p) for p in (parent/'include').glob('*.cuh')}
    assert read(parent/'SOURCE.json')['adapter_sha256']==sha(parent/'tree_service.cu')
    for p in (parent/'include').glob('*.cuh'):
        actual=run/'repair_source_v2/include'/p.name
        if p.name=='search.cuh':assert actual.read_bytes()==repair_text(p.read_bytes().decode('utf-8',errors='surrogateescape')).encode('utf-8',errors='surrogateescape')
        else:assert actual.read_bytes()==p.read_bytes()
    assert (run/'repair_source_v2/tree_service.cu').read_bytes()==(parent/'tree_service.cu').read_bytes()
    req=run/'bounded.txt';data=prior/'tree_qualify_r3/n4096.f32bin';assert sha(req)==reg['requests_sha256'] and sha(data)==reg['data_sha256']
    proof=[]
    for row in results:
        label=row['label'];g=run/'guards'/label;receipt=read(g/'receipt.json');attempt=read(run/(label+'.attempt.json'))
        assert attempt['registration_sha256']==sha(run/'REPAIR_REGISTERED.json')
        assert receipt['command'][3:]==attempt['command'] and receipt['command']==read(g/'command.json')
        command=attempt['command'];assert [Path(v).resolve() for v in command[-4:]]==[p.resolve() for p in (binary,data,req,run/'outputs'/label)]
        trace_reg=read(run/'REGISTERED.json');assert receipt['gpu']==trace_reg['gpu'] and receipt['command'][:3]==['numactl',f"--cpunodebind={trace_reg['numa']}",f"--membind={trace_reg['numa']}"]
        assert receipt['binary_sha256']==sha(binary if label=='bounded_regression' else sanitizer)
        if label=='bounded_regression':
            guards=guard_check(g);prefix=run/'outputs'/label;quality=qualify.check(data,req,prefix);assert quality['passed'] and len(quality['per_query'])==80
            ids=np.fromfile(str(prefix)+'.ids.i32',dtype='<i4');fields=np.fromfile(str(prefix)+'.dist.f32',dtype='<f4');assert np.isfinite(fields).all() and (fields>=0).all()
            assert all((np.diff(fields[i:i+8])>=0).all() for i in range(0,48*8,8))
            assert ids[:8].tolist()==trace['diagnostics'][0]['reference_top8']
            proof.append(dict(label=label,passed=True,queries=80,knn_queries=48,range_queries=32,items=len(ids),first_knn_ids=ids[:8].tolist(),output_hashes=quality['output_sha256'],guards=guards))
        else:
            assert command[:5]==[str(sanitizer),'--tool','memcheck','--error-exitcode','97']
            assert receipt['exit_code']==97 and not receipt['runtime_valid'] and receipt['stop_reason'] is None
            log=(g/'stdout.log').read_text();assert 'Invalid __global__ write of size 4 bytes' in log and 'initPQ(int, HeapStruct *, int)' in log and 'out of bounds' in log
            proof.append(dict(label=label,passed=False,exit_code=97,first_error='Invalid global write, initPQ, priority_queue.cuh:49; one-based capacity500 with500-element array',receipt_sha256=sha(g/'receipt.json'),stdout_sha256=sha(g/'stdout.log')))
    target=run/'range_targets';tr=read(target/'REGISTERED.json')
    oldreg=read(prior/'tree_safe_qualify/REGISTERED.json')
    _,prior_binding=prior_gate(prior/'tree_safe_qualify',Path(oldreg['jobs'][0]['binary']),sanitizer)
    assert prior_binding==tr['prior_guards'] and tr['prior_registration_sha256']==sha(prior/'tree_safe_qualify/REGISTERED.json')
    assert tr['binary_sha256']=='cb925d0b1cc518ec54065925d50ee57bf413034125a97cff4faa712802a96528'
    assert tr['script_sha256']==sha(run/'range_targets.py') and [j['label'] for j in tr['jobs']]==['initial','first_rebuilt']
    target_rows=read(target/'RESULTS.json');complete=(target/'COMPLETE.json').exists()
    attempts={p.name[:-len('.attempt.json')] for p in target.glob('*.attempt.json')}
    guards={p.name for p in (target/'guards').iterdir() if p.is_dir()}
    target_structure(target_rows,guards,attempts,complete)
    targets=[]
    for row in target_rows:
        label=row['label'];job=next(j for j in tr['jobs'] if j['label']==label);g=target/'guards'/label;receipt=read(g/'receipt.json');attempt=read(target/(label+'.attempt.json'))
        assert attempt['registered_sha256']==sha(target/'REGISTERED.json') and receipt['command'][3:]==attempt['command']
        assert attempt['command']==[oldreg['jobs'][0]['binary'],job['data'],str(target/(label+'.txt')),str(target/'outputs'/label)]
        assert sha(attempt['command'][0])==tr['binary_sha256']==receipt['binary_sha256']
        assert receipt['gpu']==tr['gpu'] and receipt['command'][:3]==['numactl',f"--cpunodebind={tr['numa_node']}",f"--membind={tr['numa_node']}"]
        inputs=read(static_work/'INPUTS.json')['records'][label];assert job['qids']==inputs['qids'] and len(job['qids'])==32 and job['data_sha256']==inputs['data_sha256']==sha(job['data'])
        assert sha(target/(label+'.txt'))==job['request_sha256']
        ref=static_work/'reference'/label;reference=read(ref/'REFERENCE.json');assert sha(ref/'REFERENCE.json')==job['reference_sha256']
        assert reference['N']==1000000 and reference['D']==960 and reference['data_sha256']==job['data_sha256'] and all(sha(ref/(q+'.f64'))==h for q,h in reference['files'].items())
        clean=dict(label=label,guard_exit=row['guard_exit'],receipt_sha256=sha(g/'receipt.json'))
        if row['guard_exit']==0:
            guards=guard_check(g);payload=validate_payload(target/'outputs'/label,job['qids'],ref)
            assert payload['quality_passed']==row['quality_passed'];clean.update(payload,guards=guards)
        else:assert not receipt['runtime_valid']
        targets.append(clean)
    complete=(target/'COMPLETE.json').exists()
    if complete:
        comp=read(target/'COMPLETE.json');assert comp['passed'] and comp['registration_sha256']==sha(target/'REGISTERED.json') and comp['rows']==read(target/'RESULTS.json') and len(targets)==2 and all(t['quality_passed'] for t in targets)
    return dict(status='CORRECTNESS_CHECKPOINT_NOT_TIMING',trace=trace,repair=proof,repair_registration_sha256=sha(run/'REPAIR_REGISTERED.json'),repair_binary_sha256=reg['binary_sha256'],range_targets=targets,range_complete=complete,new_GPU_processes=4+len(attempts),pending_targets=sorted(attempts-{r['label'] for r in targets}),budget=8,skipped_repair_slots=['racecheck','synccheck'],blocked_knn='K-bound repair passes bounded outputs but fails memcheck; no replacement or performance admission',limits=['Range and kNN identities remain distinct','No new end-to-end timing','No universal leak-clean or novelty claim','Formal Host-input timing and any supplemental matrix require separate registration'])
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('prior','run','static-work','sanitizer','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;a.output=outside_repo(a.output);result=verify(a.prior,a.run,a.static_work,a.sanitizer)
    result['verification_source_sha256']={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')}
    a.output.open('x').write(json.dumps(result,indent=2)+'\n');print('PASS retained tree evidence and independent range gate',result['range_complete'])
