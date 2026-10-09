#!/usr/bin/env python3
"""Direct three-mode workflow campaign; unchanged binary and inherited full oracle."""
import argparse,importlib.util,json,math,os,subprocess,sys,time
from pathlib import Path
from types import SimpleNamespace
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'build_distance_tiles'))
import verify as tiles
sha=tiles.sha;save=tiles.campaign.save
def read(p):return tiles.read(Path(p))
CONTRACT=read(HERE/'RTP_CONTRACT.json')

def jobs(stage):
    if stage=='bridge':
        return [dict(label=label,mode='T',case='million_prefix' if label=='T_million_prefix' else 'stress4096',
                     tool=next((t for t in ('memcheck','racecheck','synccheck') if label.endswith('_'+t)),None)) for label in CONTRACT['bridge']]
    return [dict(label=f'round_{r}_{m}',mode=m,case='primary',round=r,order=order,tool=None)
            for r,order in enumerate(CONTRACT['orders'],1) for m in order]

def timing_gate(summary,region,scope,ops,queries):
    assert summary['observe'] is True and summary['results']==sum(int(q['count']) for q in queries)
    for row in ops:
        ack,rebuild=float(row['ack_ms']),float(row['rebuild_ms'])
        assert math.isfinite(ack) and math.isfinite(rebuild) and ack>=rebuild>=0
    for record in (summary,region,scope):
        for key,value in record.items():
            if key.endswith(('_ms','_s')) and isinstance(value,(float,int)):
                assert math.isfinite(value) and value>=0,(key,value)
    for row in summary['stages']:
        assert math.isfinite(row['inclusive_host_ms']) and row['inclusive_host_ms']>=0 and row['calls']>=0
    assert summary['trace_ms']>0
    assert summary['trace_ms']+1e-6>=summary['final_drain_ms']+sum(float(r['ack_ms']) for r in ops)

def check_resume(original,current,work):
    assert {k:v for k,v in original.items() if k not in ('script_sha256','registered_unix')}=={k:v for k,v in current.items() if k not in ('script_sha256','registered_unix')}
    first=current['jobs'][0]['label']
    assert {p.name for p in (work/'guards').iterdir()}=={first}
    receipt=read(work/'guards'/first/'receipt.json');assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
    assert not (work/'BRIDGE.json').exists() and not (work/'RESUME.json').exists()
    assert {p.name for p in work.glob('*.command.json')}=={first+'.command.json'}
    assert all(p.name.startswith(first+'.') for p in (work/'outputs').iterdir())

def check_run(work,job,build,cases,parent,reference,library):
    label=job['label'];guard=work/'guards'/label;receipt=read(guard/'receipt.json')
    assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
    assert read(guard/'before.json')['apps']==read(guard/'after.json')['apps']==''
    checks=read(guard/'checks.json');assert checks and all(not c['foreign'] for c in checks)
    p=work/'outputs'/label;summary=read(str(p)+'.summary.json');region=read(str(p)+'.region.json')
    live=read(str(p)+'.unified.json');numeric=read(str(p)+'.numeric.json');scope=read(str(p)+'.scope.json');mapping=read(str(p)+'.build_tiles.json')
    timing_gate(summary,region,scope,tiles.rows(Path(str(p)+'.ops.csv')),tiles.rows(Path(str(p)+'.queries.csv')))
    expected_mode=int(job['mode']=='P');assert (region['mode'],live['knn_mode'],mapping['mode'])==(expected_mode,'FULL',CONTRACT['modes'][job['mode']][1])
    assert not mapping['audit'] and mapping['new_owned_GPU_bytes']==0
    assert not region['final_owned_bytes'] and not live['final_owned_bytes'] and not numeric['final_bytes']
    events=cases/job['case']/'events.txt';ops=tiles.state_rows(p);rebuilds=sum(int(r['flag'])==0 and int(r['buffer_before'])==9 for r in ops)
    assert len(ops)==int(events.read_text().splitlines()[0]) and live['refreshes']==numeric['refreshes']==numeric['epoch']==rebuilds+1
    assert region['refreshes']==(rebuilds+1 if expected_mode else 0) and mapping['build_calls']==rebuilds+3
    assert scope['warmup'] and [scope[k] for k in ('warmup_events','warmup_queries','warmup_rebuilds')]==[19,8,1]
    assert all(scope[k]==0 for k in ('setup_delay_ms','trace_delay_ms','write_delay_ms'))
    if job['case']=='stress4096':
        tiles.old.verify_cpu_library(library);tiles.validate.scores=tiles.oracle.install(library)
        data=cases/'stress4096/data.f32bin'
        quality=tiles.validate.check(data,events,p,.705625057220459,8,(expected_mode,'FULL'))
        tiles.validate.check(data,cases/'gist4096/events.txt',Path(str(p)+'.warmup'),.705625057220459,8,(expected_mode,'FULL'))
    else:
        quality=tiles.inherited_answer(p,parent,prefix_only=job['case']=='million_prefix')
        if job['case']=='primary':assert rebuilds==2 and len(ops)==336
    if job['tool']:
        text=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
        token='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
        assert token in text
    assert math.isfinite(summary['trace_ms']) and summary['trace_ms']>0
    return dict(**job,trace_ms=summary['trace_ms'],setup_plus_trace_ms=region['setup_plus_trace_ms'],initial_setup_ms=region['setup_ms'],
        warmup_ms=scope['warmup_total_ms'],final_release_ms=summary['final_drain_ms'],results=summary['results'],rebuilds=rebuilds,
        quality=quality,receipt_sha256=sha(guard/'receipt.json'),output_hashes={f.name:sha(f) for f in (work/'outputs').glob(label+'.*')})

def run(a):
    a.work=tiles.run.parent.base.outside_repo(a.work);a.work.mkdir(parents=True,exist_ok=a.resume);(a.work/'outputs').mkdir(exist_ok=a.resume)
    executed=a.work/('EXECUTED_RESUME.py' if a.resume else 'EXECUTED.py')
    with executed.open('xb') as f:f.write(Path(__file__).read_bytes())
    binary=a.build/'bin/target';assert sha(binary)==CONTRACT['binary_sha256']
    prepared=read(a.build/'PREPARED.json');assert all(sha(a.build/'source'/k)==v for k,v in prepared['sources'].items())
    admitted=read(HERE.parent/'build_distance_tiles/evidence/QUALIFICATION.json');assert admitted['passed'] and admitted['binary_sha256']==sha(binary)
    assert sha(a.build/'PREPARED.json')==admitted['source']['prepared_sha256']
    assert prepared['sources']==admitted['source']['source_hashes']
    reference=tiles.parent_binding(a.parent)
    assert sha(a.data)==tiles.validate.TARGET_DATA_SHA256
    identities=read(a.cases/'CASES.json');assert all(sha(a.cases/k)==v for k,v in identities.items())
    if a.stage=='primary':
        bridge=read(a.bridge/'BRIDGE.json');assert bridge['passed'] and bridge['contract_sha256']==sha(HERE/'RTP_CONTRACT.json')
        assert bridge['binary_sha256']==sha(binary) and len(bridge['rows'])==5
        assert sha(a.bridge/'REGISTERED.json')==bridge['registered_sha256']
        for job,old in zip(jobs('bridge'),bridge['rows']):assert check_run(a.bridge,job,a.build,a.cases,a.parent,reference,a.library)==old
    record=dict(stage=a.stage,jobs=jobs(a.stage),binary_sha256=sha(binary),build_sha256=sha(a.build/'BUILD.json'),prepared_sha256=sha(a.build/'PREPARED.json'),
        contract_sha256=sha(HERE/'RTP_CONTRACT.json'),script_sha256=sha(__file__),guard_sha256=sha(a.guard),case_hashes=identities,
        data_sha256=sha(a.data),reference=reference,gpu=a.gpu,numa_node=a.numa_node,registered_unix=time.time(),parent_source_sha256=sha(HERE.parent/'build_distance_tiles/verify.py'))
    if a.resume:
        assert a.stage=='bridge'
        original=read(a.work/'REGISTERED.json');assert sha(a.work/'EXECUTED.py')==original['script_sha256']
        check_resume(original,record,a.work)
        assert not (a.work/'RESUME.json').exists()
        save(a.work/'RESUME.json',dict(original_registration_sha256=sha(a.work/'REGISTERED.json'),original_script_sha256=original['script_sha256'],
            corrected_script_sha256=sha(__file__),reason='offline checker passed str to Path reader after first successful GPU execution; reuse that output, no repeat'))
    else:save(a.work/'REGISTERED.json',record)
    rows=[]
    for job in record['jobs']:
        label=job['label'];data=a.data if job['case'] in ('million_prefix','primary') else a.cases/job['case']/'data.f32bin'
        env={k:v for k,v in os.environ.items() if not k.startswith(('BUILD_','TARGET_','PAR_','KNN_','U10_','REGION_'))}
        env.update(REGION_MODE=CONTRACT['modes'][job['mode']][0],BUILD_MAPPING=CONTRACT['modes'][job['mode']][1],KNN_MODE='FULL',
                   TARGET_WARMUP='1',U10_OBSERVE='1',U10_TREE_AUDIT='0',TARGET_RESTORE_AUDIT='0')
        command=[str(binary),str(data),str(a.cases/job['case']/'events.txt'),'2','0.705625057220459',str(a.work/'outputs'/label),'8']
        if job['tool']:command=[str(a.sanitizer),'--tool',job['tool'],'--error-exitcode','97',*command]
        command_path=a.work/(label+'.command.json')
        command_record=dict(command=command,env={k:v for k,v in env.items() if k.startswith(('BUILD_','TARGET_','KNN_','U10_','REGION_'))})
        if command_path.exists():assert a.resume and read(command_path)==command_record
        else:save(command_path,command_record)
        guard=a.work/'guards'/label;start=time.monotonic()
        if a.resume and (guard/'receipt.json').exists():
            rc=read(guard/'receipt.json')['exit_code']
        else:
          with (a.work/(label+'.outer.log')).open('x') as log:
            rc=subprocess.run([sys.executable,str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa_node),'--output',str(guard),'--',*command],env=env,stdout=log,stderr=log).returncode
        assert sha(binary)==record['binary_sha256'] and sha(__file__)==record['script_sha256'] and sha(HERE/'RTP_CONTRACT.json')==record['contract_sha256']
        if rc:raise RuntimeError(f'failed {label}; retained, no automatic replacement')
        row=check_run(a.work,job,a.build,a.cases,a.parent,reference,a.library);rows.append(row);save(a.work/'RAW_ROWS.json',rows)
        print(label,round(row['trace_ms'],3),'ms; full-output PASS',flush=True)
    if a.stage=='bridge':save(a.work/'BRIDGE.json',dict(passed=True,contract_sha256=record['contract_sha256'],binary_sha256=sha(binary),registered_sha256=sha(a.work/'REGISTERED.json'),rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=('bridge','primary'),required=True);p.add_argument('--resume',action='store_true')
    for k in ('work','build','cases','data','parent','library','guard','bridge','sanitizer'):p.add_argument('--'+k,type=Path,required=k not in ('bridge','sanitizer'))
    p.add_argument('--gpu',required=True);p.add_argument('--numa-node',type=int,required=True);a=p.parse_args();assert __debug__;run(a)
