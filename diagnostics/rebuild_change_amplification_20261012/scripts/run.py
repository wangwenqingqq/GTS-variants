#!/usr/bin/env python3
"""One locked diagnostic replay of a pinned keeper-derived Host observer."""
import argparse,csv,fcntl,hashlib,importlib.util,json,os,subprocess,sys
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def rows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);p.add_argument('data',type=Path);p.add_argument('native_reference',type=Path);a=p.parse_args()
    root=a.root;prior=a.prior;contract=json.loads((root/'CONTRACT.json').read_text());audit=json.loads((root/'SOURCE_AUDIT.json').read_text())
    assert not (root/'REGISTERED.json').exists(),'never silently rerun'
    case=prior/'cases/target';events=case/'events.txt';trace=case/'trace'
    assert sha(prior/'P2/bench')==contract['keeper_binary_sha256']
    assert sha(a.data)==contract['data_sha256'] and sha(events)==contract['events_sha256']
    for name,h in audit['keeper_files'].items():assert sha(prior/'P2/source'/name)==h
    for e in ('BUILD_AUDIT_DIR','REGION_COUNTERS','TARGET_SCOPE_DIAGNOSTIC'):assert not os.environ.get(e),e
    live=subprocess.check_output(['nvidia-smi','-i','1','--query-gpu=uuid,name,driver_version,power.limit,clocks.current.sm,clocks.current.memory','--format=csv,noheader'],text=True).strip()
    assert hashlib.sha256(live.split(',')[0].strip().encode()).hexdigest()==contract['hardware']['gpu_uuid_sha256']
    env={**os.environ,'REGION_MODE':'PAR_STRONG','BUILD_MAPPING':'TILED','KNN_MODE':'FULL','TARGET_WARMUP':'1',
         'U10_OBSERVE':'1','U10_TREE_AUDIT':'0','TARGET_RESTORE_AUDIT':'0','PE_TRACE':str(trace),
         'RCA_DIR':str(root/'snapshots'),'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
    (root/'snapshots').mkdir();(root/'outputs').mkdir();output=root/'outputs/observer'
    binary=root/'observer'
    record={'contract_sha256':sha(root/'CONTRACT.json'),'binary_sha256':sha(binary),'build_log_sha256':sha(root/'build.log'),
            'source_audit_sha256':sha(root/'SOURCE_AUDIT.json'),'source':{str(f.relative_to(root/'observer_source')):sha(f) for f in sorted((root/'observer_source').rglob('*')) if f.is_file()},
            'case':{str(f.relative_to(case)):sha(f) for f in sorted(case.rglob('*')) if f.is_file()},'live_hardware':live,
            'order':['observer_exact_target'],'budget':1}
    (root/'REGISTERED.json').write_text(json.dumps(record,indent=2)+'\n')
    locks=[]
    try:
        for name in contract['locks']:
            f=open(name,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
        env['GTS_CAMPAIGN_LOCK_FDS']=','.join(str(f.fileno()) for f in locks)
        cmd=[sys.executable,str(prior/'deps/locked.py'),'--gpu','1','--numa-node','0','--output',str(root/'runtime'),'--',
             str(binary),str(a.data),str(events),'2',str(contract['shape']['radius']),str(output),'8']
        subprocess.run(cmd,env=env,pass_fds=tuple(f.fileno() for f in locks),check=True)
    finally:
        for f in locks:f.close()
    quality={'passed':False,'payload_hashes':{},'ordered_payloads_identical':True}
    frozen=prior/'primary/outputs/r1_P2'
    for suffix in ('.ids.i32','.dist.f32','.final.i32','.warmup.ids.i32','.warmup.dist.f32','.warmup.final.i32'):
        assert sha(str(output)+suffix)==sha(str(frozen)+suffix),(suffix,'frozen full bytes differ')
        quality['payload_hashes'][suffix]=sha(str(output)+suffix)
    obsrows=rows(str(output)+'.ops.csv');oldrows=rows(str(frozen)+'.ops.csv');assert len(obsrows)==len(oldrows)==336
    for x,y in zip(obsrows,oldrows):
        assert {k:v for k,v in x.items() if k not in ('ack_ms','rebuild_ms')}=={k:v for k,v in y.items() if k not in ('ack_ms','rebuild_ms')}
        assert (float(x['rebuild_ms'])>0)==(float(y['rebuild_ms'])>0)
    assert rows(str(output)+'.queries.csv')==rows(str(frozen)+'.queries.csv')
    triggers=[int(r['step']) for r in obsrows if float(r['rebuild_ms'])>0];assert len(triggers)==2
    quality['rebuild_trigger_steps_zero_based']=triggers
    assert sorted(p.name for p in (root/'snapshots').iterdir())==['POST_R1','POST_R2','PRE_R1','PRE_R2']
    for r,step in enumerate(triggers,1):
        before=json.loads((root/f'snapshots/PRE_R{r}/meta.json').read_text());after=json.loads((root/f'snapshots/POST_R{r}/meta.json').read_text())
        assert before['step']==after['step']==step and before['buffer']==10 and after['buffer']==0
        assert before['n']==after['n']==1000000 and after['nn']==after['valid_nodes']==111111
        assert before['epoch']+1==after['epoch'] and before['live']==after['live']
        assert sha(root/f'snapshots/PRE_R{r}/live.i32')==sha(root/f'snapshots/POST_R{r}/live.i32')
        assert after['build_created_children']+1==after['valid_nodes']
    # No rebuild happens between POST_R1 and PRE_R2: published base representation must be exact.
    stable=['base.i32','nodes.bin','empty.i32','order.i32','lo.f64','hi.f64','packed.f32']+['plan_'+f+'.i32' for f in ('regions','leaf_slot','slot_pid','leaves','owners','parents','skeleton','level_offsets','skeleton_offsets')]
    assert all(sha(root/'snapshots/POST_R1'/f)==sha(root/'snapshots/PRE_R2'/f) for f in stable)
    sys.path.insert(0,str(prior/'checker/artifacts/external_closure'))
    spec=importlib.util.spec_from_file_location('frozen_check',prior/'checker/artifacts/external_closure/pe_check.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    checked=mod.check(a.data,events,trace,output,'P',a.native_reference)
    quality.update(passed=True,full_quality=checked,stable_between_rebuilds=True)
    (root/'QUALITY.json').write_text(json.dumps(quality,indent=2)+'\n');print(json.dumps({'quality_passed':True,'trigger_steps':triggers}),flush=True)
    subprocess.run([sys.executable,str(root/'scripts/analyze.py'),str(root/'snapshots'),str(root/'summary')],check=True)
    bound={'passed':True,'registered_sha256':sha(root/'REGISTERED.json'),'quality_sha256':sha(root/'QUALITY.json'),
           'runtime_sha256':sha(root/'runtime/receipt.json'),'result_sha256':sha(root/'summary/RESULT.json'),
           'snapshot_manifest_sha256':sha(root/'summary/SNAPSHOT_MANIFEST.json'),'contract_sha256':sha(root/'CONTRACT.json')}
    (root/'CLOSURE.json').write_text(json.dumps(bound,indent=2)+'\n');print(json.dumps(bound),flush=True)
if __name__=='__main__':main()
