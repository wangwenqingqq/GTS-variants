#!/usr/bin/env python3
"""Registered qualification or six fixed paired workflows; reuse the original guard."""
import argparse
import fcntl
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace
import run

HERE=Path(__file__).resolve().parent
sha=run.sha
CONTRACT=json.loads((HERE/'CONTRACT.json').read_text())


def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')


def jobs(stage):
    if stage=='qualification':
        result=[dict(label=case+'_'+mode,case=case,mode=mode,audit=True)
                for case in CONTRACT['qualification']['cases'] for mode in ('B0','B1')]
        result += [dict(label='gist4096_B1_'+tool,case='gist4096',mode='B1',audit=True,tool=tool)
                   for tool in ('memcheck','racecheck','synccheck')]
        result += [dict(label='million_prefix_B1_memcheck',case='million_prefix',mode='B1',audit=False,tool='memcheck')]
        assert len(result)==22;return result
    return [dict(label=f'round_{i}_{mode}',case='primary',mode=mode,audit=False,round=i)
            for i,order in enumerate(CONTRACT['primary']['orders'],1) for mode in (('B0','B1') if order=='B0B1' else ('B1','B0'))]


def register(a):
    a.work.mkdir(parents=True,exist_ok=False);binary=a.build/'bin/target'
    manifest=json.loads((a.build/'BUILD.json').read_text());assert sha(binary)==manifest['binary_sha256']
    run.parent.validate.verify_target_data(a.data)
    if a.stage=='primary':
        import verify
        admission=json.loads(a.admission.read_text())
        assert admission['passed'] and admission['binary_sha256']==sha(binary)
        assert admission['contract_sha256']==sha(HERE/'CONTRACT.json') and admission['data_sha256']==sha(a.data)
        assert admission['source_identity'] and admission['all_layer_identity'] and admission['sanitizers_passed']
        assert admission['source_analysis_sha256']==sha(a.qualification_analysis)
        actual=verify.completed(SimpleNamespace(work=a.admission.parent,build=a.build,cases=a.cases,executed_driver=a.qualification_driver))
        assert actual==admission['evidence_binding'],'qualification raw evidence changed'
    record=dict(stage=a.stage,jobs=jobs(a.stage),binary_sha256=sha(binary),contract_sha256=sha(HERE/'CONTRACT.json'),
        executed_driver_sha256=sha(Path(__file__)),build_sha256=sha(a.build/'BUILD.json'),prepared_sha256=sha(a.build/'PREPARED.json'),
        case_hashes=json.loads((a.cases/'CASES.json').read_text()),data_sha256=sha(a.data),
        guard_sha256=sha(a.guard),gpu=a.gpu,numa_node=a.numa_node,registered_unix=time.time())
    if a.stage=='primary':record['admission_sha256']=sha(a.admission)
    save(a.work/'REGISTERED.json',record)
    groups=range(1,7) if a.stage=='primary' else (None,)
    for group in groups:
        folder=a.work/'guard'/(f'round_{group}' if group else 'campaign')
        cmd=[sys.executable,str(a.guard.resolve()),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(folder),'--',
             sys.executable,str(Path(__file__).resolve()),'execute','--work',str(a.work),'--build',str(a.build),'--cases',str(a.cases),'--data',str(a.data)]
        if group:cmd += ['--round',str(group)]
        with (a.work/f'outer_{group or "campaign"}.log').open('w') as f: result=subprocess.run(cmd,stdout=f,stderr=f)
        assert result.returncode==0, ('failed guarded campaign; retain all attempted rows',group)
        assert json.loads((folder/'receipt.json').read_text())['runtime_valid']


def execute(a):
    record=json.loads((a.work/'REGISTERED.json').read_text());binary=a.build/'bin/target'
    assert sha(binary)==record['binary_sha256'] and sha(Path(__file__))==record['executed_driver_sha256']
    assert sha(HERE/'CONTRACT.json')==record['contract_sha256']
    rows=json.loads((a.work/'RAW_ROWS.json').read_text()) if (a.work/'RAW_ROWS.json').exists() else []
    selected=[j for j in record['jobs'] if a.round is None or j.get('round')==a.round]
    assert len(rows)==((a.round-1)*2 if a.round else 0)
    with Path('/tmp/gts_build_tiles_campaign.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for job in selected:
            label=job['label'];folder=a.work/'runs'/label;folder.mkdir(parents=True,exist_ok=False)
            (a.work/'outputs').mkdir(exist_ok=True);output=a.work/'outputs'/label
            data=a.data if job['case'] in ('primary','million_prefix') else a.cases/job['case']/'data.f32bin'
            events=a.cases/job['case']/'events.txt'
            assert sha(events)==record['case_hashes'][str(events.relative_to(a.cases))]
            if data!=a.data:assert sha(data)==record['case_hashes'][str(data.relative_to(a.cases))]
            env={k:v for k,v in os.environ.items() if not k.startswith(('BUILD_','TARGET_','PAR_','KNN_','U10_','REGION_'))}
            env.update(REGION_MODE='PAR_STRONG',KNN_MODE='FULL',BUILD_MAPPING=CONTRACT['modes'][job['mode']],
                TARGET_WARMUP='1',U10_OBSERVE='1',U10_TREE_AUDIT='0',TARGET_RESTORE_AUDIT='0')
            if job['audit']:
                audit=a.work/'audit'/label;audit.mkdir(parents=True,exist_ok=False);env['BUILD_AUDIT_DIR']=str(audit)
            before=subprocess.check_output(['nvidia-smi','-i',record['gpu'],'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
            assert not before.strip(),'GPU occupied between own fresh processes'
            command=[str(binary),str(data),str(events),'2',str(CONTRACT['scope']['radius']),str(output),'8']
            if job.get('tool'):
                tool=shutil.which('compute-sanitizer');assert tool
                command=[str(Path(tool).resolve()),'--tool',job['tool'],'--error-exitcode','86',*command]
            save(folder/'command.json',dict(command=command,env={k:v for k,v in env.items() if k.startswith(('BUILD_','TARGET_','KNN_','U10_','REGION_'))}))
            start=time.monotonic()
            with (folder/'stdout.log').open('w') as out,(folder/'stderr.log').open('w') as err:
                result=subprocess.run(command,env=env,stdout=out,stderr=err)
            after=subprocess.check_output(['nvidia-smi','-i',record['gpu'],'--query-compute-apps=pid,process_name,used_memory','--format=csv,noheader'],text=True)
            receipt=dict(exit_code=result.returncode,wall_s=time.monotonic()-start,binary_sha256=sha(binary),empty_before=True,empty_after=not after.strip())
            save(folder/'receipt.json',receipt)
            if result.returncode or after.strip():
                save(folder/'FAILED.json',dict(job=job,receipt=receipt));raise RuntimeError('retain failed attempt; do not replace automatically')
            summary=json.loads(Path(str(output)+'.summary.json').read_text());scope=json.loads(Path(str(output)+'.scope.json').read_text())
            region=json.loads(Path(str(output)+'.region.json').read_text());mapping=json.loads(Path(str(output)+'.build_tiles.json').read_text())
            assert mapping['mode']==CONTRACT['modes'][job['mode']] and mapping['audit']==job['audit']
            assert math.isfinite(summary['trace_ms']) and summary['trace_ms']>0 and scope['warmup']
            rows.append({**job,**receipt, 'trace_ms':summary['trace_ms'],'setup_plus_trace_ms':region['setup_plus_trace_ms'],
                         'initial_setup_ms':region['setup_ms'],'warmup_ms':scope['warmup_total_ms'],'results':summary['results']})
            save(a.work/'RAW_ROWS.json',rows);print(label,summary['trace_ms'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('run','execute'))
    for name in ('work','build','cases','data','guard','admission','qualification-driver','qualification-analysis'):p.add_argument('--'+name,type=Path)
    p.add_argument('--gpu');p.add_argument('--numa-node',type=int);p.add_argument('--stage',choices=('qualification','primary'));p.add_argument('--round',type=int)
    a=p.parse_args();assert __debug__;a.work=run.parent.base.outside_repo(a.work)
    (register if a.action=='run' else execute)(a)
