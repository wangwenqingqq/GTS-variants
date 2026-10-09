#!/usr/bin/env python3
"""Execute fixed fresh processes under an own-campaign lock and unchanged GPU guard."""
import argparse
import csv
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import numpy as np
if not __debug__:raise RuntimeError('Python assertions are required')
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import validate
import qualify
import oracle
MODES={'A':('NATIVE','FULL'),'B':('PAR_STRONG','FULL'),'C':('PAR_STRONG','BOUND')}
ORDERS=['ABC','CBA','BCA','ACB','CAB','BAC']
RADIUS=0.705625057220459


def recipe():
    spec=importlib.util.spec_from_file_location('gts_phase_b_recipe',HERE/'run.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()


def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def job_list(stage):
    if stage=='qualification':
        return ([dict(label=f'scope_{m}',mode=m,restore=True,audit=True) for m in 'ABC']
          +[dict(label='scope_C_cold',mode='C',warm=False,audit=True)]
          +[dict(label='scope_C_'+name,mode='C',delay=name,audit=True) for name in ('setup','trace','write')]
          +[dict(label='scope_C_'+tool,mode='C',tool=tool) for tool in ('memcheck','racecheck','synccheck')]
          +[dict(label='million_C_memcheck',mode='C',tool='memcheck',million=True,restore=True)])
    if stage=='observer':
        return [dict(label=f'observer_{i}_{mode}',mode='C',observe=mode=='ON',million=True,short=True,round=i)
                for i,order in enumerate((('OFF','ON'),('ON','OFF'),('OFF','ON')),1) for mode in order]
    if stage=='primary':
        return [dict(label=f'round_{i}_{mode}',mode=mode,million=True,short=True,round=i,order=order)
                for i,order in enumerate(ORDERS,1) for mode in order]
    raise ValueError(stage)


def register(a):
    a.work.mkdir(parents=True,exist_ok=False)
    binary=a.build/'bin/target';manifest=json.loads((a.build/'BUILD.json').read_text())
    assert sha(binary)==manifest['binary_sha256']
    validate.verify_target_data(a.data)
    if a.stage=='primary':
        for name in ('QUALIFICATION.json','OBSERVER.json'):
            gate=json.loads((a.admission/name).read_text());assert gate['passed'] and gate['evidence_binding']
            assert gate['binary_sha256']==sha(binary) and gate['contract_sha256']==sha(HERE/'CONTRACT.json')
            assert gate['data_sha256']==sha(a.data) and gate['short_events_sha256']==sha(a.cases/'short1m/events.txt')
    jobs=job_list(a.stage)
    record=dict(stage=a.stage,jobs=jobs,binary_sha256=sha(binary),data_sha256=sha(a.data),
        campaign_source_sha256=sha(Path(__file__)),
        case_hashes=json.loads((a.cases/'CASES.json').read_text()),contract_sha256=sha(HERE/'CONTRACT.json'),
        gpu=a.gpu,guard_sha256=sha(a.guard),build_sha256=sha(a.build/'BUILD.json'),
        prepared_sha256=sha(a.build/'PREPARED.json'),registered_unix=time.time(),
        guard_grouping='six sequential three-process rounds' if a.stage=='primary' else 'one guarded diagnostic campaign')
    save(a.work/'REGISTERED.json',record)
    groups=range(1,7) if a.stage=='primary' else (None,)
    for group in groups:
        guarded=a.work/'guard'/(f'round_{group}' if group else 'campaign')
        cmd=[sys.executable,str(a.guard.resolve()),'--gpu',a.gpu,'--numa-node',str(a.numa_node),
             '--output',str(guarded),'--',sys.executable,str(Path(__file__).resolve()),'execute',
             '--work',str(a.work.resolve()),'--build',str(a.build.resolve()),'--cases',str(a.cases.resolve()),
             '--data',str(a.data.resolve()),'--gpu',a.gpu]
        if group:cmd+=['--round',str(group)]
        p=subprocess.run(cmd,text=True,capture_output=True)
        (a.work/f'outer_{group or "campaign"}.log').write_text(p.stdout+p.stderr)
        assert p.returncode==0,p.stdout+p.stderr
        guard=json.loads((guarded/'receipt.json').read_text())
        assert guard['runtime_valid']
        assert not any(x['foreign'] for x in json.loads((guarded/'checks.json').read_text()))
    print('PASS guarded',a.stage,flush=True)


def execute(a):
    registered=json.loads((a.work/'REGISTERED.json').read_text());binary=(a.build/'bin/target').resolve()
    assert sha(binary)==registered['binary_sha256']
    assert sha(Path(__file__))==registered['campaign_source_sha256']
    start=time.monotonic();rows=json.loads((a.work/'RAW_ROWS.json').read_text()) if (a.work/'RAW_ROWS.json').exists() else []
    selected=[j for j in registered['jobs'] if a.round is None or j['round']==a.round]
    if a.round:assert len(rows)==(a.round-1)*3 and len(selected)==3
    else:assert not rows
    for job in selected:
        label=job['label'];run=a.work/'runs'/label;run.mkdir(parents=True,exist_ok=False)
        (a.work/'outputs').mkdir(exist_ok=True);prefix=a.work/'outputs'/label
        if job.get('million'):
            data=a.data;events=a.cases/('short1m' if job.get('short') else 'warmup')/'events.txt'
        else:data=a.cases/'scope4096/data.f32bin';events=a.cases/'scope4096/events.txt'
        relative=str(events.relative_to(a.cases));assert sha(events)==registered['case_hashes'][relative]
        if not job.get('million'):assert sha(data)==registered['case_hashes'][str(data.relative_to(a.cases))]
        # The outer existing guard owns both shared GPU locks and watches all descendants.
        before=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip()
        assert not before,'device occupied between fresh processes'
        range_mode,knn=MODES[job['mode']]
        env={**os.environ,'REGION_MODE':range_mode,'KNN_MODE':knn,
             'TARGET_WARMUP':'1' if job.get('warm',True) else '0',
             'U10_OBSERVE':'1' if job.get('observe',True) else '0',
             'U10_TREE_AUDIT':'1' if job.get('audit',False) else '0',
             'TARGET_RESTORE_AUDIT':'1' if job.get('restore',False) else '0'}
        for name in ('TARGET_STALE','PAR_STALE','KNN_STALE','TARGET_SCOPE_DIAGNOSTIC',
                     'TARGET_SETUP_DELAY_MS','TARGET_TRACE_DELAY_MS','TARGET_WRITE_DELAY_MS'):env.pop(name,None)
        if job.get('delay'):
            env['TARGET_SCOPE_DIAGNOSTIC']='1';env['TARGET_'+job['delay'].upper()+'_DELAY_MS']='200'
        cmd=[str(binary),str(data),str(events),'2',str(RADIUS),str(prefix),'8']
        if job.get('tool'):
            tool=shutil.which('compute-sanitizer');assert tool,'installed compute-sanitizer required'
            cmd=[str(Path(tool).resolve()),'--tool',job['tool'],'--error-exitcode','86',*cmd]
        save(run/'command.json',dict(command=cmd,env={k:env[k] for k in env if k.startswith(('TARGET_','U10_','KNN_','REGION_'))}))
        beginning=time.monotonic()
        with (run/'stdout.log').open('w') as out,(run/'stderr.log').open('w') as err:
            p=subprocess.run(cmd,env=env,stdout=out,stderr=err)
        after=subprocess.check_output(['nvidia-smi','-i',a.gpu,'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True).strip()
        receipt=dict(label=label,exit_code=p.returncode,binary_sha256=sha(binary),
                     offset_start_s=beginning-start,wall_s=time.monotonic()-beginning,empty_before=not before,empty_after=not after)
        save(run/'receipt.json',receipt);assert p.returncode==0 and not after,(label,p.returncode)
        summary=json.loads(Path(str(prefix)+'.summary.json').read_text());scope=json.loads(Path(str(prefix)+'.scope.json').read_text())
        region=json.loads(Path(str(prefix)+'.region.json').read_text());live=json.loads(Path(str(prefix)+'.unified.json').read_text())
        assert (region['mode'],live['knn_mode'])==(int(range_mode=='PAR_STRONG'),knn)
        assert scope['warmup']==job.get('warm',True) and summary['observe']==job.get('observe',True)
        assert summary['trace_ms']>0 and math.isfinite(summary['trace_ms'])
        rows.append({**job,**receipt,'trace_ms':summary['trace_ms'],'setup_plus_trace_ms':region['setup_plus_trace_ms'],
                     'warmup_ms':scope['warmup_total_ms'],'results':summary['results']})
        save(a.work/'RAW_ROWS.json',rows)
        print(label,'trace_ms',summary['trace_ms'],flush=True)



def verify_completed(a):
    """Bind offline analysis to complete, valid original execution evidence."""
    registered=json.loads((a.work/'REGISTERED.json').read_text());rows=json.loads((a.work/'RAW_ROWS.json').read_text())
    driver=a.executed_driver if a.executed_driver else Path(__file__)
    assert sha(driver)==registered['campaign_source_sha256'],'executed driver identity required'
    assert sha(HERE/'CONTRACT.json')==registered['contract_sha256']
    assert registered['jobs']==job_list(registered['stage']) and len(rows)==len(registered['jobs'])
    groups=[a.work/'guard'/f'round_{i}' for i in range(1,7)] if registered.get('guard_grouping')=='six sequential three-process rounds' else [a.work/'guard']
    if len(groups)==1 and not (groups[0]/'receipt.json').exists():groups=[groups[0]/'campaign']
    guards={}
    for folder in groups:
        receipt=json.loads((folder/'receipt.json').read_text());checks=json.loads((folder/'checks.json').read_text())
        assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
        assert checks and not any(check['foreign'] for check in checks)
        assert not json.loads((folder/'before.json').read_text())['apps'] and not json.loads((folder/'after.json').read_text())['apps']
        for name in ('receipt.json','checks.json','before.json','after.json'):
            guards[str((folder/name).relative_to(a.work))]=sha(folder/name)
    outputs={}
    for job,row in zip(registered['jobs'],rows):
        assert all(row[k]==v for k,v in job.items())
        run=a.work/'runs'/job['label'];receipt=json.loads((run/'receipt.json').read_text())
        assert all(row[k]==v for k,v in receipt.items()) and receipt['exit_code']==0 and receipt['empty_before'] and receipt['empty_after']
        assert receipt['binary_sha256']==registered['binary_sha256']
        prefix=a.work/'outputs'/job['label'];summary=json.loads(Path(str(prefix)+'.summary.json').read_text())
        region=json.loads(Path(str(prefix)+'.region.json').read_text());scope=json.loads(Path(str(prefix)+'.scope.json').read_text())
        assert row['trace_ms']==summary['trace_ms'] and row['results']==summary['results']
        assert row['setup_plus_trace_ms']==region['setup_plus_trace_ms'] and row['warmup_ms']==scope['warmup_total_ms']
        assert math.isfinite(row['trace_ms']) and row['trace_ms']>0
        if job.get('tool'):
            combined=(run/'stdout.log').read_text()+(run/'stderr.log').read_text()
            expected='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
            assert expected in combined
        for path in sorted((a.work/'outputs').glob(job['label']+'.*')):
            outputs[str(path.relative_to(a.work))]=sha(path)
    return dict(registered_sha256=sha(a.work/'REGISTERED.json'),raw_rows_sha256=sha(a.work/'RAW_ROWS.json'),
                executed_driver_sha256=sha(driver),guard_hashes=guards,output_hashes=outputs)


def verify_cpu_library(path):
    metadata=json.loads((path.parent/'CPU_BUILD.json').read_text())
    CPU_FLAGS=recipe().CPU_FLAGS
    assert metadata['library_sha256']==sha(path) and metadata['source_sha256']==sha(HERE/'cpu_oracle.cpp')
    assert metadata['flags']==CPU_FLAGS and metadata['threads']==8
    conformance=path.parent.parent/'CPU_ORACLE.json'
    assert metadata['oracle_conformance_sha256']==sha(conformance)
    proof=json.loads(conformance.read_text())
    assert not proof['cuda_used'] and proof['extreme_nextafter_subnormal_D128_D960']
    assert len(proof['rows'])==9 and all(r['bitwise_ordered_numpy_match'] for r in proof['rows'])
    return dict(build_sha256=sha(path.parent/'CPU_BUILD.json'),conformance_sha256=sha(conformance),library_sha256=sha(path))


def check_outputs(a):
    binding=verify_completed(a);cpu_binding=verify_cpu_library(a.library)
    registered=json.loads((a.work/'REGISTERED.json').read_text());rows=json.loads((a.work/'RAW_ROWS.json').read_text())
    assert len(rows)==len(registered['jobs'])
    validate.scores=oracle.install(a.library)
    checked=[];seen={};observed_groups={}
    for job in registered['jobs']:
        label=job['label'];prefix=a.work/'outputs'/label
        data=a.data if job.get('million') else a.cases/'scope4096/data.f32bin'
        events=a.cases/('short1m' if job.get('short') else 'warmup')/'events.txt' if job.get('million') else a.cases/'scope4096/events.txt'
        answer=tuple(sha(Path(str(prefix)+suffix)) for suffix in ('.ids.i32','.dist.f32','.queries.csv'))
        key=(str(data),str(events))
        observed=job.get('observe',True)
        if observed:observed_groups.setdefault(key,[]).append(label)
        expected_refreshes=3 if job.get('short') else 2
        live=json.loads(Path(str(prefix)+'.unified.json').read_text());numeric=json.loads(Path(str(prefix)+'.numeric.json').read_text())
        region=json.loads(Path(str(prefix)+'.region.json').read_text())
        assert live['refreshes']==numeric['refreshes']==numeric['epoch']==expected_refreshes
        assert not live['final_owned_bytes'] and not region['final_owned_bytes'] and not numeric['final_bytes']
        assert region['refreshes']==(expected_refreshes if job['mode']!='A' else 0)
        assert (region['mode'],live['knn_mode'])==(int(job['mode']!='A'),MODES[job['mode']][1])
        if observed and key not in seen:
            quality=validate.check(data,events,prefix,RADIUS,8,(int(job['mode']!='A'),MODES[job['mode']][1]));seen[key]=(label,answer)
        else:
            # OFF may precede its ON partner. Validate it after the observed oracle exists.
            quality=dict(full_output_identity_pending=True) if key not in seen else dict(full_output_identity=answer==seen[key][1],oracle_binding=seen[key][0])
            if key in seen:assert answer==seen[key][1],label
        if job.get('warm',True):
            warm=Path(str(prefix)+'.warmup')
            validate.check(data,a.cases/'warmup/events.txt',warm,RADIUS,8,(int(job['mode']!='A'),MODES[job['mode']][1]))
        scope=json.loads(Path(str(prefix)+'.scope.json').read_text())
        if job.get('restore'):assert scope['restored_device_bytes_checked']==validate.load(data).nbytes
        if job.get('audit'):
            text=(a.work/'runs'/label/'stdout.log').read_text().split('TARGET_PHASE measured\n',1)[1]
            filtered=a.work/'runs'/label/'measured_tree.log';filtered.write_text(text)
            quality['coverage']=validate.coverage(data,events,filtered)
        checked.append(dict(label=label,answer_hashes=answer,quality=quality))
    for job,row in zip(registered['jobs'],checked):
        data=a.data if job.get('million') else a.cases/'scope4096/data.f32bin'
        events=a.cases/('short1m' if job.get('short') else 'warmup')/'events.txt' if job.get('million') else a.cases/'scope4096/events.txt'
        assert tuple(row['answer_hashes'])==seen[(str(data),str(events))][1],row['label']
        if row['quality'].pop('full_output_identity_pending',False):
            row['quality'].update(full_output_identity=True,oracle_binding=seen[(str(data),str(events))][0])
        if job.get('observe',True):
            with Path(str(a.work/'outputs'/job['label'])+'.ops.csv').open() as f:
                states=list(csv.DictReader(f));assert len(states)==(336 if job.get('short') else 19)
                assert all(math.isfinite(float(r[k])) and float(r[k])>=0 for r in states for k in ('ack_ms','rebuild_ms'))
    for labels in observed_groups.values():qualify.equal_outputs(a,labels)
    save(a.work/'QUALITY.json',dict(passed=True,rows=checked,oracle_library_sha256=sha(a.library),ordered_full_outputs=True,evidence_binding=binding,CPU_binding=cpu_binding,analysis_source_sha256=sha(Path(__file__))))
    print('PASS complete CPU oracle and identical answer bindings',registered['stage'],flush=True)


def bootstrap(values,seed=202610090242):
    x=np.log(values);rng=np.random.default_rng(seed);draw=x[rng.integers(0,len(x),size=(20000,len(x)))].mean(axis=1)
    return dict(ratio=float(np.exp(x.mean())),CI95=list(map(float,np.exp(np.quantile(draw,[.025,.975])))))


def summarize(a):
    quality=json.loads((a.work/'QUALITY.json').read_text());assert quality['passed']
    integrity=verify_completed(a);assert quality['evidence_binding']==integrity
    record=json.loads((a.work/'REGISTERED.json').read_text());rows=json.loads((a.work/'RAW_ROWS.json').read_text());by={r['label']:r for r in rows}
    binding=dict(binary_sha256=record['binary_sha256'],contract_sha256=record['contract_sha256'],data_sha256=record['data_sha256'],
                 short_events_sha256=record['case_hashes']['short1m/events.txt'],registered_sha256=sha(a.work/'REGISTERED.json'),evidence_binding=integrity,quality_sha256=sha(a.work/'QUALITY.json'),analysis_source_sha256=sha(Path(__file__)))
    if record['stage']=='qualification':
        base=by['scope_C'];trace=by['scope_C_trace'];setup=by['scope_C_setup'];write=by['scope_C_write']
        assert trace['trace_ms']-base['trace_ms']>=180
        assert setup['setup_plus_trace_ms']-base['setup_plus_trace_ms']>=180
        assert abs(setup['trace_ms']-base['trace_ms'])<100 and abs(write['trace_ms']-base['trace_ms'])<100
        assert write['wall_s']-base['wall_s']>=.18
        save(a.work/'QUALIFICATION.json',dict(**binding,passed=True,scope_injection_ms=200,rows=rows,
            warmup_clone_restore=True,bounded_access_sync_sanitizers='0 errors',target_clone_rebuild_access_memcheck='0 errors',
            full_leak_diagnostic='UNRESOLVED_CONTEXT_SYMBOLS_NOT_CLEAN',production_promotion=False))
    elif record['stage']=='observer':
        ratios=[by[f'observer_{i}_ON']['trace_ms']/by[f'observer_{i}_OFF']['trace_ms'] for i in range(1,4)]
        result=bootstrap(ratios);passed=result['CI95'][1]<=1.05 and max(ratios)<=1.05
        save(a.work/'OBSERVER.json',dict(**binding,passed=passed,ON_over_OFF=ratios,paired=result,rows=rows,
            scope='same fixed N1M/D960 336-event trace; complete answers identical; no production promotion'))
        assert passed,'observer overhead gate failed; retain result and stop primary admission'
    else:
        comparisons={}
        for left,right in (('A','B'),('B','C'),('A','C')):
            values=[by[f'round_{i}_{left}']['trace_ms']/by[f'round_{i}_{right}']['trace_ms'] for i in range(1,7)]
            result=bootstrap(values);strata={}
            for before in (True,False):
                v=[values[i] for i,order in enumerate(ORDERS) if (order.index(left)<order.index(right))==before]
                assert len(v)==3;strata['baseline_before' if before else 'baseline_after']=float(np.exp(np.log(v).mean()))
            reversal=(strata['baseline_before']-1)*(strata['baseline_after']-1)<0
            decision='inconclusive' if result['CI95'][0]<=1<=result['CI95'][1] or reversal else ('narrow_short_win' if result['ratio']>1 else 'narrow_short_regression')
            comparisons[left+'/'+right]=dict(raw_ratios=values,paired=result,order_strata=strata,order_reversal=reversal,
                candidate_wins=sum(v>1 for v in values),decision=decision)
        variants={m:dict(values_ms=[by[f'round_{i}_{m}']['trace_ms'] for i in range(1,7)],
                        p10_median_p90_ms=list(map(float,np.quantile([by[f'round_{i}_{m}']['trace_ms'] for i in range(1,7)],[.1,.5,.9])))) for m in 'ABC'}
        save(a.work/'SHORT_RESULTS.json',dict(**binding,status='MEASURED_FIXED_SHORT_SCOPE',comparisons=comparisons,variants=variants,rows=rows,
            default_promoted=False,long_started=False,external_dynamic_comparison=False))
    print('PASS summary',record['stage'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('run','execute','check','summarize'))
    p.add_argument('--stage',choices=('qualification','observer','primary'));p.add_argument('--work',type=Path,required=True)
    p.add_argument('--build',type=Path);p.add_argument('--cases',type=Path);p.add_argument('--data',type=Path)
    p.add_argument('--gpu');p.add_argument('--numa-node',type=int,default=2);p.add_argument('--guard',type=Path)
    p.add_argument('--library',type=Path);p.add_argument('--admission',type=Path);p.add_argument('--round',type=int,choices=range(1,7));p.add_argument('--executed-driver',type=Path)
    a=p.parse_args()
    a.work=recipe().base.outside_repo(a.work)
    if a.action=='run':
        with Path(f'/tmp/gts_target_workflow_campaign_{a.gpu}.lock').open('a+') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);register(a)
    elif a.action=='execute':execute(a)
    elif a.action=='check':check_outputs(a)
    else:summarize(a)
