#!/usr/bin/env python3
"""Bounded standalone construction replays under preserved GPU ownership locks."""
import argparse,fcntl,hashlib,json,os,subprocess,sys
from pathlib import Path
import numpy as np
NODE=np.dtype([('pid','<i4'),('min_dis','<f4'),('size','<i4'),('lid','<i4'),('is_leaf','<i4')])
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for x in iter(lambda:f.read(8<<20),b''):h.update(x)
    return h.hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def unpack(snapshot,out):
    if out.exists():
        info=json.loads(out.with_suffix('.json').read_text())
        assert out.stat().st_size==1000000*960*4 and sha(out)==info['sha256']
        assert info['bit_exact_inverse_pack'] and sha(snapshot/'packed.f32')==info['source_sha256'];return
    src=np.memmap(snapshot/'packed.f32',dtype='<u4',mode='r',shape=(31250,960,32))
    dst=np.memmap(out,dtype='<u4',mode='w+',shape=(1000000,960))
    for first in range(0,31250,512):
        last=min(first+512,31250);dst[first*32:last*32]=src[first:last].transpose(0,2,1).reshape(-1,960)
        assert np.array_equal(dst[first*32:last*32].reshape(-1,32,960).transpose(0,2,1),src[first:last])
    dst.flush();del dst
    dump(out.with_suffix('.json'),{'bytes':out.stat().st_size,'sha256':sha(out),'source_sha256':sha(snapshot/'packed.f32'),'bit_exact_inverse_pack':True})
def native_gate(snap,out):
    eq={f:sha(snap/f)==sha(out/f) for f in ('order.i32','nodes.bin','empty.i32')}
    assert all(eq.values()),('STOP_NATIVE_REPLAY',eq)
    dump(out/'NATIVE_GATE.json',{'passed':True,'byte_identical':eq,'semantic_implication':['order','leaf memberships','selected pivots','canonical topology']})
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);p.add_argument('helpers',type=Path);p.add_argument('phase',choices=['native','C1','C2','C3']);a=p.parse_args()
    root=a.root.resolve();contract=json.loads((root/'CONTRACT.json').read_text());audit=json.loads((root/'SOURCE_AUDIT.json').read_text())
    assert sha(a.prior/'FINAL_CLOSURE.json')==contract['prior_final_closure_sha256']
    assert sha(a.prior/'summary_v2/RESULT.json')==contract['prior_result_sha256']
    old_manifest=json.loads((a.prior/'summary_v2/SNAPSHOT_MANIFEST.json').read_text())
    # Rehash every captured snapshot payload once before first replay.
    if a.phase=='native':
        assert not (root/'REGISTERED_native.json').exists(),'never silently repeat GPU processes'
        assert sha(a.prior/'summary_v2/SNAPSHOT_MANIFEST.json')==contract['prior_snapshot_manifest_sha256']
        for entry in old_manifest:
            target=a.prior/'snapshots'/entry['file']
            assert target.stat().st_size==entry['bytes'] and sha(target)==entry['sha256']
        dump(root/'PRIOR_REVERIFIED.json',{'passed':True,'files':len(old_manifest),'bytes':sum(e['bytes'] for e in old_manifest),'manifest_sha256':sha(a.prior/'summary_v2/SNAPSHOT_MANIFEST.json')})
    else:
        for r in (1,2):
            for name in ('PRE','C0'):assert json.loads((root/f'runs/R{r}_{name}/NATIVE_GATE.json').read_text())['passed']
        if a.phase in ('C2','C3'):
            gate=json.loads((root/f'ADMIT_{a.phase}.json').read_text());assert gate['admitted'] and gate['contract_sha256']==sha(root/'CONTRACT.json')
    for rel,h in audit['replay_files'].items():assert sha(root/'source'/rel)==h
    live=subprocess.check_output(['nvidia-smi','-i','1','--query-gpu=uuid,name,driver_version,power.limit,clocks.current.sm,clocks.current.memory','--format=csv,noheader'],text=True).strip()
    assert hashlib.sha256(live.split(',')[0].strip().encode()).hexdigest()==contract['hardware']['gpu_uuid_sha256']
    (root/'inputs').mkdir(exist_ok=True);(root/'runs').mkdir(exist_ok=True)
    tasks=[(r,name,0 if name in ('PRE','C0') else int(name[1:])) for r in (1,2) for name in (('PRE','C0') if a.phase=='native' else (a.phase,))]
    registration=root/f'REGISTERED_{a.phase}.json';assert not registration.exists(),'no silent rerun'
    record={'phase':a.phase,'order':[f'R{r}_{name}' for r,name,dose in tasks],'budget':len(tasks),'contract_sha256':sha(root/'CONTRACT.json'),'binary_sha256':sha(root/'replay'),'source_audit_sha256':sha(root/'SOURCE_AUDIT.json'),'hardware_private':live}
    dump(registration,record)
    for r,name,dose in tasks:
        snap=a.prior/f'snapshots/{"PRE" if name=="PRE" else "POST"}_R{r}';pre=a.prior/f'snapshots/PRE_R{r}'
        aos=root/f'inputs/{snap.name}.f32';unpack(snap,aos)
        out=root/f'runs/R{r}_{name}';out.mkdir();(out/'audit').mkdir()
        env={**os.environ,'BUILD_MAPPING':'TILED','BUILD_AUDIT_DIR':str(out/'audit'),'U10_TREE_AUDIT':'0','U10_OBSERVE':'0','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'}
        locks=[]
        try:
            for path in contract['locks']:
                f=open(path,'a+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);locks.append(f)
            env['GTS_CAMPAIGN_LOCK_FDS']=','.join(str(f.fileno()) for f in locks)
            cmd=[sys.executable,str(a.helpers/'locked.py'),'--gpu','1','--numa-node','0','--output',str(out/'runtime'),'--',str(root/'replay'),str(aos),str(pre),str(snap),str(dose),str(out)]
            dump(out/'PROCESS.json',{'command_private':cmd,'dose':dose,'snapshot':snap.name,'aos_sha256':sha(aos),'binary_sha256':record['binary_sha256']})
            subprocess.run(cmd,env=env,pass_fds=tuple(f.fileno() for f in locks),check=True)
        finally:
            for f in locks:f.close()
        if not dose:native_gate(snap,out)
        print(f'COMPLETED R{r}_{name}',flush=True)
    dump(root/f'PHASE_{a.phase}.json',{'passed':True,'registered_sha256':sha(registration),'completed':record['order']})
if __name__=='__main__':main()
