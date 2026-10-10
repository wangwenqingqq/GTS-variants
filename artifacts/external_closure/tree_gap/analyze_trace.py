#!/usr/bin/env python3
"""Verify the first-loss chain using retained read-only traces and full output bytes."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from prepare_trace import sha,outside_repo

def records(path):
    result={}
    for line in path.read_text().splitlines():
        if line.startswith('TRACE '):
            _,stage,*values=line.split();assert stage!='ERROR',line
            result.setdefault(stage,[]).append(values)
    return result

def analyze(prior,run):
    data=prior/'tree_qualify_r3/n4096.f32bin'
    assert sha(data)=='bd391cbf3486b306ac7aa6977903391feaa8708d9725bc792d7124134e4a9acd'
    assert struct.unpack('<iii',data.read_bytes()[:12])==(17,4096,2)
    x=np.fromfile(data,dtype='<f4',offset=12).reshape(4096,17);sq=np.zeros(4096)
    for d in range(17):sq+=(x[:,d].astype('f8')-float(x[0,d]))**2
    order=np.lexsort((np.arange(len(x)),sq));wanted=order[:8].tolist();assert sq[order[8]]>sq[order[7]]
    reg=json.loads((run/'REGISTERED.json').read_text());binding=json.loads((run/'EXECUTION_BINDING.json').read_text())
    assert sha(run/'REGISTERED.json')=='b08de6401ffed010ef5e14080505546b694a846153898468906c70eaaeb3a3e2'
    assert binding['registration_sha256']==sha(run/'REGISTERED.json') and binding['script_sha256']==sha(run/'run.py')
    assert reg['contract_sha256']==sha(run/'CONTRACT.json') and reg['guard_sha256']==sha(run/'run_locked.py')
    assert reg['source_sha256']=={str(p.relative_to(run/'trace_source')):sha(p) for p in (run/'trace_source').rglob('*') if p.is_file()}
    assert sha(run/'trace_source/SOURCE.json')=='927ab4fcac69b7c28bee4874716292dc47a6533d9322717f6be0dd347008bb93'
    assert reg['before_execution'] and reg['max_processes']==8 and [j['label'] for j in reg['jobs']]==['native_trace','reuse_trace']
    results=[]
    for label,old in [('native_trace','tree_qualify_r3/outputs/tree_native_0'),('reuse_trace','tree_diagnose/outputs/tree_adapt_0')]:
        guard=run/'guards'/label;receipt=json.loads((guard/'receipt.json').read_text())
        job=next(j for j in reg['jobs'] if j['label']==label)
        assert json.loads((run/(label+'.attempt.json')).read_text())['registered']==job
        assert sha(run/Path(job['binary']).name)==job['binary_sha256']==receipt['binary_sha256']
        assert job['data_sha256']==sha(data) and job['request_sha256']==sha(prior/'tree_qualify_r3'/Path(job['requests']).name)
        assert receipt['gpu']==reg['gpu'] and receipt['command'][:3]==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}"]
        assert receipt['command'][3:6]==[job['binary'],job['data'],job['requests']]
        assert Path(receipt['command'][6])==Path(job['binary']).parent/'outputs'/label and len(receipt['command'])==7
        assert json.loads((guard/'command.json').read_text())==receipt['command']
        assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
        assert all(not c['foreign'] for c in json.loads((guard/'checks.json').read_text()))
        assert all(json.loads((guard/f).read_text())['apps']=='' for f in ['before.json','after.json'])
        for ext in ('.ids.i32','.dist.f32'):
            assert Path(str(run/'outputs'/label)+ext).read_bytes()==Path(str(prior/old)+ext).read_bytes()
        t=records(guard/'stdout.log');leaves=[r for r in t['MAP'] if int(r[4])==-1]
        assert sorted(int(r[5]) for r in leaves)==list(range(4096)), 'topology must retain all occurrences exactly once'
        got=np.fromfile(str(run/'outputs'/label)+'.ids.i32',dtype='<i4')[:8].tolist();missing=sorted(set(wanted)-set(got))
        assert missing==[374,394] and 0 in got and 1 in got
        before=[int(r[1]) for r in t['ROOT_BEFORE']];after=[int(r[1]) for r in t['ROOT_AFTER']]
        assert before==after and len(before)==11
        bound=float(t['BOUND'][0][1]);assert bound<float(np.sqrt(sq[order[7]]))
        loss=[]
        for occurrence in missing:
            leaf=next(r for r in leaves if int(r[5])==occurrence);root,node=int(leaf[1]),int(leaf[2])
            assert root in after
            pop=next(r for r in t['BOUND_POP'] if int(r[1])==node)
            assert float(pop[2])>float(pop[3]) and int(pop[4])<8
            assert not any(int(r[1])==occurrence for r in t['BOUND_DIST']+t['SEARCH_DIST'])
            assert not any(int(r[2])==occurrence for r in t['HEAP'])
            assert not any(int(r[1])==occurrence for r in t['MERGE_IDS'])
            loss.append(dict(occurrence=occurrence,partition=int(leaf[0]),root=root,node=node,node_lower_bound=float(pop[2]),premature_bound=float(pop[3]),heap_size=int(pop[4]),stage='initial bound traversal before leaf verification'))
        assert all(not set(missing).intersection(np.fromfile(str(run/'outputs'/label)+'.ids.i32',dtype='<i4')[i:i+8]) for i in range(0,8 if label=='native_trace' else 256,8))
        results.append(dict(label=label,full_output_byte_parity=True,reference_top8=wanted,delivered_top8=got,true_eighth_distance=float(np.sqrt(sq[order[7]])),retained_roots=len(after),published_bound=bound,first_losses=loss,trace_sha256=sha(guard/'stdout.log'),receipt_sha256=sha(guard/'receipt.json')))
    return dict(status='MEASURED_FIRST_LOSS_NOT_PERFORMANCE',scope='Frozen N4096/D17 duplicate-occurrence case, PNUM8/K8, native one call and ownership-only32 calls',data_sha256=sha(data),diagnostics=results,registration_sha256=sha(run/'REGISTERED.json'),execution_sha256=sha(run/'EXECUTION_BINDING.json'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('prior',type=Path);p.add_argument('run',type=Path);p.add_argument('output',type=Path);a=p.parse_args();assert __debug__
    a.output=outside_repo(a.output)
    result=analyze(a.prior,a.run);a.output.open('x').write(json.dumps(result,indent=2)+'\n');print('PASS first-loss chain and retained native/reuse full-output parity')
