#!/usr/bin/env python3
"""Independently close inputs, actual pivot interventions, and raw replay payloads."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from analyze import NODE,sha,dump,correspondence

def check_input(snapshot,aos):
    src=np.memmap(snapshot/'packed.f32',dtype='<u4',mode='r',shape=(31250,960,32));dst=np.memmap(aos,dtype='<u4',mode='r',shape=(1000000,960))
    for first in range(0,31250,512):
        last=min(first+512,31250)
        assert np.array_equal(dst[first*32:last*32].reshape(-1,32,960).transpose(0,2,1),src[first:last])
    info=json.loads(aos.with_suffix('.json').read_text());assert info['sha256']==sha(aos) and info['source_sha256']==sha(snapshot/'packed.f32')
    return {'passed':True,'bit_exact_inverse_pack':True,'aos_sha256':info['sha256'],'packed_sha256':info['source_sha256'],'bytes':aos.stat().st_size}
def decisions(pre,current,run):
    oldbase=np.fromfile(pre/'base.i32',dtype='<i4');base=np.fromfile(current/'base.i32',dtype='<i4');oldorder=np.fromfile(pre/'order.i32',dtype='<i4');oldnodes=np.fromfile(pre/'nodes.bin',dtype=NODE)
    common,oldrows,newrows=np.intersect1d(oldbase,base,return_indices=True)
    maxoid=int(max(oldbase.max(),base.max()))+1;inverse=np.full(maxoid,-1,dtype=np.int32);inverse[base]=np.arange(len(base))
    with (run/'DECISIONS.csv').open() as f:rows=list(csv.DictReader(f))
    dose=json.loads((run/'REPLAY.json').read_text())['dose'];admitted=fallback=requested=0
    for level in range(5):
        audit=run/'audit/build0';order=np.fromfile(audit/f'level{level}.input.order',dtype='<i4');nodes=np.fromfile(audit/f'level{level}.input.nodes',dtype=NODE);pids=np.fromfile(audit/f'level{level}.distance.pids',dtype='<i4')
        slots=10**level;first=(slots-1)//9;match={};counts=None
        if level<dose:
            if level==0:match={0:0}
            else:
                ol=np.full(maxoid,-1,dtype=np.int32);nl=ol.copy()
                for j in range(slots):
                    v=oldnodes[first+j];ol[oldbase[oldorder[v['lid']:v['lid']+v['size']]]]=j
                    v=nodes[first+j];nl[base[order[v['lid']:v['lid']+v['size']]]]=j
                assert (ol[common]>=0).all() and (nl[common]>=0).all()
                match,counts=correspondence(ol[common],nl[common],slots)
        levelrows=[r for r in rows if int(r['level'])==level];assert len(levelrows)==slots
        for slot,r in enumerate(levelrows):
            nid=first+slot;v=nodes[nid];local=order[v['lid']:v['lid']+v['size']];native=int(base[order[(2*int(v['lid'])+int(v['size'])-1)//2]])
            expected={'level':level,'storage_node':nid,'pre_storage_node':-1,'requested':int(level<dose),'admitted':0,'reason':'native' if level>=dose else 'no_correspondence','pre_pivot_oid':-1,'native_pivot_oid':native,'chosen_pivot_oid':native,'intersection':0,'current_size':int(v['size']),'pre_size':0}
            if level<dose:
                requested+=1
                if slot in match:
                    oldnid=first+match[slot];old=oldnodes[oldnid];oldpivot=int(oldbase[oldnodes[oldnid*10+1]['pid']]);physical=int(inverse[oldpivot])
                    expected.update(pre_storage_node=oldnid,pre_pivot_oid=oldpivot,pre_size=int(old['size']),intersection=len(common) if level==0 else int(counts[slot,match[slot]]))
                    if physical>=0 and np.any(local==physical):expected.update(admitted=1,reason='admitted',chosen_pivot_oid=oldpivot);admitted+=1
                    else:expected['reason']='pivot_absent';fallback+=1
                else:fallback+=1
            actual={k:r[k] if k=='reason' else int(r[k]) for k in expected}
            assert actual==expected,(run.name,level,slot,actual,expected)
            assert int(base[pids[nid]])==expected['chosen_pivot_oid']
    assert len(rows)==11111
    return {'passed':True,'decision_rows':len(rows),'dose':dose,'requested':requested,'admitted':admitted,'fallback':fallback,'native_middle_and_actual_device_pid_checked':True,'correspondence_independently_recomputed':True}
def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('prior',type=Path);p.add_argument('summary',type=Path);a=p.parse_args();c=json.loads((a.root/'CONTRACT.json').read_text())
    assert sha(a.prior/'FINAL_CLOSURE.json')==c['prior_final_closure_sha256']
    assert sha(a.prior/'summary_v2/RESULT.json')==c['prior_result_sha256']
    assert sha(a.prior/'summary_v2/SNAPSHOT_MANIFEST.json')==c['prior_snapshot_manifest_sha256']
    prior_manifest=json.loads((a.prior/'summary_v2/SNAPSHOT_MANIFEST.json').read_text())
    for entry in prior_manifest:
        f=a.prior/'snapshots'/entry['file'];assert f.stat().st_size==entry['bytes'] and sha(f)==entry['sha256']
    inputs={};runs={};files={};phases=set();phase_bindings={}

    for r in (1,2):
        for side in ('PRE','POST'):
            label=f'{side}_R{r}';inputs[label]=check_input(a.prior/'snapshots'/label,a.root/f'inputs/{label}.f32')
        for mode in ('PRE','C0','C1','C2','C3'):
            run=a.root/f'runs/R{r}_{mode}'
            if not (run/'REPLAY.json').exists():continue
            side='PRE' if mode=='PRE' else 'POST';label=f'{side}_R{r}'
            process=json.loads((run/'PROCESS.json').read_text());assert process['aos_sha256']==inputs[label]['aos_sha256']
            expected_dose=0 if mode in ('PRE','C0') else int(mode[1:])
            assert process['dose']==json.loads((run/'REPLAY.json').read_text())['dose']==expected_dose
            runtime=json.loads((run/'runtime/receipt.json').read_text());assert runtime['runtime_valid'] and runtime['exit_code']==0 and runtime['stop_reason'] is None
            assert process['binary_sha256']==runtime['binary_sha256']==sha(a.root/'replay')
            if mode in ('PRE','C0'):
                assert json.loads((run/'NATIVE_GATE.json').read_text())['passed']
                for name in ('order.i32','nodes.bin','empty.i32'):assert sha(run/name)==sha(a.prior/'snapshots'/label/name)
            phases.add('native' if mode in ('PRE','C0') else mode)

            assert json.loads((run/'VALIDITY.json').read_text())['passed']
            runs[run.name]=decisions(a.prior/f'snapshots/PRE_R{r}',a.prior/'snapshots'/label,run)
            for f in sorted(run.rglob('*')):
                if f.is_file():files[str(f.relative_to(a.root))]={'bytes':f.stat().st_size,'sha256':sha(f)}
    registered_run_set=set()
    for phase in sorted(phases):
        path=a.root/f'REGISTERED_{phase}.json';reg=json.loads(path.read_text());done=json.loads((a.root/f'PHASE_{phase}.json').read_text())
        assert reg['binary_sha256']==sha(a.root/'replay') and reg['contract_sha256']==sha(a.root/'CONTRACT.json')
        assert reg['source_audit_sha256']==sha(a.root/'SOURCE_AUDIT.json')
        assert done['passed'] and done['registered_sha256']==sha(path) and done['completed']==reg['order'] and reg['budget']==len(reg['order'])
        registered_run_set.update(reg['order'])
        phase_bindings[phase]={'registered_sha256':sha(path),'phase_receipt_sha256':sha(a.root/f'PHASE_{phase}.json'),'budget':reg['budget']}
        if phase in ('C2','C3'):
            admitpath=a.root/f'ADMIT_{phase}.json';admit=json.loads(admitpath.read_text());evidence=a.root/f'summary_{"C1" if phase=="C2" else "C2"}/RESULT.json'
            assert admit['admitted'] and admit['contract_sha256']==sha(a.root/'CONTRACT.json') and admit['evidence_sha256']==sha(evidence)
            phase_bindings[phase]['admit_sha256']=sha(admitpath)
            if phase=='C3':assert admit['C2_closure_sha256']==sha(a.root/'CLOSURE_C2_v1.json')
    assert registered_run_set==set(runs)
    audit=json.loads((a.root/'SOURCE_AUDIT.json').read_text())
    for rel,h in audit['replay_files'].items():assert sha(a.root/'source'/rel)==h
    closure={'passed':True,'contract_sha256':sha(a.root/'CONTRACT.json'),'source_audit_sha256':sha(a.root/'SOURCE_AUDIT.json'),'binary_sha256':sha(a.root/'replay'),'build_log_sha256':sha(a.root/'build.log'),'inputs':inputs,'runs':runs,'actual_gpu_construction_processes':len(runs),'failed_prebinary_launches':1,'prior_closure_sha256':sha(a.prior/'FINAL_CLOSURE.json'),'result_sha256':sha(a.summary/'RESULT.json'),'prior_snapshot_files_rehashed':len(prior_manifest),'phase_bindings':phase_bindings,'raw_files':len(files),'raw_bytes':sum(x['bytes'] for x in files.values()),'validation_scope':'full inverse-pack bytes and independently reconstructed actual pivot decisions; structural gates only; no performance or production admission'}
    dump(a.root/'RAW_MANIFEST.json',files);closure['raw_manifest_sha256']=sha(a.root/'RAW_MANIFEST.json');dump(a.root/'CLOSURE.json',closure);print(json.dumps({k:v for k,v in closure.items() if k not in ('inputs','runs')}),flush=True)
if __name__=='__main__':main()
