#!/usr/bin/env python3
"""Independently qualify the unchanged, previously sanitizer-checked range-only identity."""
import argparse,csv,json,math,subprocess,sys,time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import qualify
from static_campaign import guard_check
from prepare_trace import sha,outside_repo

def save(path,value):path.write_text(json.dumps(value,indent=2)+'\n')
def prior_structure(reg,rows):
    labels=['tree_adapt_1','tree_adapt_memcheck','tree_adapt_racecheck','tree_adapt_synccheck']
    assert [j['label'] for j in reg['jobs']]==[r['label'] for r in rows]==labels
    assert [j['tool'] for j in reg['jobs']]==[None,'memcheck','racecheck','synccheck']
    assert all(r['guard_exit']==0 and r['quality_passed'] for r in rows)


def validate_payload(prefix,qids,reference_dir,reference_n=1000000):
    with Path(str(prefix)+'.queries.csv').open() as f:queries=list(csv.DictReader(f))
    ids=np.fromfile(str(prefix)+'.ids.i32',dtype='<i4');fields=np.fromfile(str(prefix)+'.dist.f32',dtype='<f4')
    assert len(ids)==len(fields) and len(queries)==len(qids)
    assert np.isfinite(fields).all() and (fields>=0).all(), 'Euclidean fields must be finite and nonnegative'
    assert Path(str(prefix)+'.ids.i32').stat().st_size%4==Path(str(prefix)+'.dist.f32').stat().st_size%4==0
    at=0;quality=[]
    for i,(r,q) in enumerate(zip(queries,qids)):
        z=int(r['count']);assert z>=0 and int(r['offset'])==at and int(r['qid'])==q and int(r['query'])==i and r['task']=='range'
        assert math.isfinite(float(r['ack_ms'])) and float(r['ack_ms'])>=0 and int(r['selected_trees'])>=0
        sq=np.fromfile(reference_dir/(str(q)+'.f64'),dtype='<f8');assert len(sq)==reference_n and np.isfinite(sq).all() and (sq>=0).all()
        quality.append(qualify.cpu.quality(ids[at:at+z],fields[at:at+z],fields[at:at+z].astype('f8')**2,sq,'range',0.705625057220459));at+=z
    assert at==len(ids)
    return dict(quality_passed=all(q['passed'] for q in quality),queries=len(qids),items=at,quality=quality,outputs={p.name:sha(p) for p in prefix.parent.glob(prefix.name+'.*')})

def prior_gate(prior,binary,sanitizer):
    reg=json.loads((prior/'REGISTERED.json').read_text());old=json.loads((prior/'RESULTS.json').read_text())['rows']
    prior_structure(reg,old)
    binding={}
    for job,row in zip(reg['jobs'],old):
        label=job['label'];assert row['label']==label and row['guard_exit']==0 and row['quality_passed']
        assert sha(binary)==job['binary_sha256']=='cb925d0b1cc518ec54065925d50ee57bf413034125a97cff4faa712802a96528'
        assert sha(job['data'])==job['data_sha256'] and sha(job['requests'])==job['request_sha256']
        binding[label]=guard_check(prior/'guards'/label)
        receipt=json.loads((prior/'guards'/label/'receipt.json').read_text())
        command=[job['binary'],job['data'],job['requests'],str(prior/'outputs'/label)]
        if job['tool']:command=[str(sanitizer),'--tool',job['tool'],'--error-exitcode','97',*command]
        assert receipt['command'][0]=='numactl' and receipt['command'][3:]==command
        assert receipt['binary_sha256']==sha(command[0])
        if job['tool']:
            logs=''.join((prior/'guards'/label/f).read_text() for f in ('stdout.log','stderr.log'))
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in logs
        assert qualify.check(job['data'],job['requests'],prior/'outputs'/label)['passed']
        fields=np.fromfile(str(prior/'outputs'/label)+'.dist.f32',dtype='<f4');assert np.isfinite(fields).all() and (fields>=0).all()
    return reg,binding

def main(a):
    a.output=outside_repo(a.output);assert not a.output.exists();a.output.mkdir()
    reg,binding=prior_gate(a.prior,a.binary,a.sanitizer)
    inputs=json.loads((a.static_work/'INPUTS.json').read_text())['records'];jobs=[]
    for name in ('initial','first_rebuilt'):
        r=inputs[name];assert len(r['qids'])==len(set(r['qids']))==32 and sha(r['data'])==r['data_sha256']
        folder=a.static_work/'reference'/name;ref=json.loads((folder/'REFERENCE.json').read_text());assert sha(folder/'REFERENCE.json')==r['reference_sha256'] and ref['data_sha256']==r['data_sha256']
        assert ref['N']==1000000 and ref['D']==960 and all(sha(folder/(q+'.f64'))==h for q,h in ref['files'].items())
        req=a.output/(name+'.txt');req.write_text('32\n'+''.join(f'1 {q} 0.705625057220459 8\n' for q in r['qids']))
        jobs.append(dict(label=name,data=r['data'],data_sha256=r['data_sha256'],qids=r['qids'],reference_sha256=r['reference_sha256'],request_sha256=sha(req)))
    registration=dict(identity='GPU_TREE_SAFE_ADAPT_RANGE_ONLY',before_execution=True,registered_unix=time.time(),slots=['initial_snapshot','first_rebuilt_snapshot'],max_new_processes=2,knn_repair_not_used=True,prior_registration_sha256=sha(a.prior/'REGISTERED.json'),prior_guards=binding,binary_sha256=sha(a.binary),guard_sha256=sha(a.guard),script_sha256=sha(__file__),checker_sha256=sha(qualify.__file__),quality_sha256=sha(qualify.cpu.__file__),gpu=a.gpu,numa_node=a.numa,jobs=jobs)
    save(a.output/'REGISTERED.json',registration);(a.output/'outputs').mkdir();rows=[]
    for job in jobs:
        name=job['label'];req=a.output/(name+'.txt');prefix=a.output/'outputs'/name
        assert sha(a.binary)==registration['binary_sha256'] and sha(a.guard)==registration['guard_sha256'] and sha(req)==job['request_sha256']
        command=[str(a.binary),job['data'],str(req),str(prefix)]
        save(a.output/(name+'.attempt.json'),dict(command=command,registered_sha256=sha(a.output/'REGISTERED.json'),started_unix=time.time()))
        done=subprocess.run([sys.executable,str(a.guard),'--gpu',a.gpu,'--numa-node',str(a.numa),'--output',str(a.output/'guards'/name),'--',*command],capture_output=True,text=True)
        (a.output/(name+'.outer.log')).write_text(done.stdout+done.stderr)
        row=dict(label=name,guard_exit=done.returncode)
        if not done.returncode:
            row['guards']=guard_check(a.output/'guards'/name)
            receipt=json.loads((a.output/'guards'/name/'receipt.json').read_text())
            assert receipt['command'][3:]==command and receipt['gpu']==a.gpu and receipt['binary_sha256']==registration['binary_sha256']
            assert receipt['command'][:3]==['numactl',f'--cpunodebind={a.numa}',f'--membind={a.numa}']
            row.update(validate_payload(prefix,job['qids'],a.static_work/'reference'/name))
        rows.append(row);save(a.output/'RESULTS.json',rows);print({k:v for k,v in row.items() if k not in ('quality','outputs','guards')},flush=True)
        if done.returncode or not row['quality_passed']:raise SystemExit('STOP range-only qualification; no replacement')
    save(a.output/'COMPLETE.json',dict(passed=True,task='range_only',rows=rows,registration_sha256=sha(a.output/'REGISTERED.json')))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in ('prior','static-work','binary','guard','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--sanitizer',type=Path,required=True);p.add_argument('--gpu',required=True);p.add_argument('--numa',type=int,required=True);a=p.parse_args();assert __debug__;main(a)
