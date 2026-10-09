#!/usr/bin/env python3
"""Rebind original executions and strengthen all output checks before admission."""
import argparse,csv,hashlib,json,os,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import qualify
from common import outside_repo
cpu=qualify.cpu;sha=cpu.sha;save=cpu.save

def read(p):return json.loads(Path(p).read_text())
def first(prefix):
    with Path(str(prefix)+'.queries.csv').open() as f:r=next(csv.DictReader(f))
    n=int(r['count'])
    return n,Path(str(prefix)+'.ids.i32').read_bytes()[:n*4],Path(str(prefix)+'.dist.f32').read_bytes()[:n*4],r['selected_trees']

def main(a):
    work=outside_repo(a.work);out=work/'FINAL_QUALIFICATION.json';assert not out.exists()
    dev=work/'cpu_dev_r2';registration=read(dev/'REGISTERED.json');selected=read(dev/'SELECTION.json')
    assert sha(dev/'EXECUTED.py')==registration['script_sha256']
    assert sha(dev/'EXECUTED_CPU.py')==registration['executor_sha256']
    assert sha(dev/'SNAPSHOT.json')==registration['snapshot_sha256']
    spec=read(dev/'SNAPSHOT.json');data=cpu.validate.load(a.data);assert sha(a.data)==spec['data_sha256']
    forbidden=set();bindings={}
    for name in ('initial','first_rebuilt'):
        p=a.snapshots/name/'SNAPSHOT.json';s=read(p);source=a.data if name=='initial' else p.parent/'data.f32bin'
        assert sha(source)==s['data_sha256'];x=cpu.validate.load(source)
        forbidden.update(hashlib.sha256(x[q['physical_qid']].tobytes()).hexdigest() for q in s['queries'])
        bindings[name]=dict(manifest_sha256=sha(p),data_sha256=sha(source))
    coordinates=[hashlib.sha256(data[q['physical_qid']].tobytes()).hexdigest() for q in spec['queries']]
    assert coordinates==registration['coordinate_sha256'] and set(coordinates).isdisjoint(forbidden)
    assert sorted(forbidden)==registration['excluded_sha256'] and len(set(coordinates))==32
    assert [(r['method'],r['leaf']) for r in selected['rows']]==[tuple(x) for x in registration['jobs']]
    for r in selected['rows']:
        prefix=dev/f"{r['method']}_{r['leaf']}";meta=read(str(prefix)+'.native.json')
        assert read(str(prefix)+'.receipt.json')['returncode']==0
        assert meta['source_sha256']==registration['executor_sha256'] and meta['snapshot_sha256']==sha(dev/'SNAPSHOT.json')
        assert meta['leaf_size']==r['leaf'] and meta['requested_native_threads']==1
        assert meta['versions']['sklearn']=='1.6.1' and all(p['num_threads']==1 for p in meta['versions']['pools'])
        assert r['cost_ms']==meta['timing']['knn_pass_ms']+meta['timing']['range_pass_ms']
        for name,digest in r['output_sha256'].items():assert sha(dev/name)==digest
    cpu_quality={}
    for method,leaf in selected['selected'].items():
        expected=min((r for r in selected['rows'] if r['method']==method),key=lambda r:(r['cost_ms'],r['leaf']))['leaf'];assert leaf==expected
        prefix=dev/f'{method}_{leaf}'
        cpu.check(SimpleNamespace(data=a.data,snapshot=dev,output=prefix,library=a.library))
        q=read(str(prefix)+'.quality.json');assert q['passed'];cpu_quality[method]=dict(leaf=leaf,proof_sha256=sha(str(prefix)+'.quality.json'),all_64_queries_pass=True)
    os.environ['CLOSURE_CPU_ORACLE']=str(a.library)
    reports={};receipts=[]
    for folder in ('qualify_r2','tree_qualify_r3','tree_diagnose','tree_safe_qualify','range_snapshots'):
        for p in sorted((work/folder/'guards').glob('*/receipt.json')):
            receipts.append(dict(case=folder+'/'+p.parent.name,runtime_valid=read(p)['runtime_valid'],receipt_sha256=sha(p)))
        reg=read(work/folder/'REGISTERED.json')
        for job in reg['jobs']:
            prefix=work/folder/'outputs'/job['label'];guard=work/folder/'guards'/job['label']
            if not (guard/'receipt.json').exists() or not read(guard/'receipt.json')['runtime_valid']:continue
            assert sha(job['data'])==job['data_sha256'] and sha(job['requests'])==job['request_sha256']
            native_required=folder=='range_snapshots' or job.get('exe')=='range_service'
            q=qualify.check(job['data'],job['requests'],prefix,native_squared_required=native_required)
            reports[folder+'/'+job['label']]=q
            if native_required:assert q['passed'],('range admission failure',folder,job['label'])
            if job.get('tool'):
                log=(guard/'stdout.log').read_text()+(guard/'stderr.log').read_text()
                token='RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors'
                assert token in log
    edge=read(work/'CPU_TREE_ALL_LEAVES_EDGES.json');assert edge['passed']
    flat_edge=read(work/'CPU_FLAT_INCLUSIVE_EDGES.json');assert flat_edge['passed'] and flat_edge['inclusive_adapter']
    for name in ('initial','first_rebuilt'):
        folder=work/('cpu_flat_'+name);reg=read(folder/'REGISTERED.json');delivery=read(folder/'DELIVERED.json')
        for filename,digest in delivery['output_sha256'].items():assert sha(folder/filename)==digest
        source=a.data if name=='initial' else a.snapshots/name/'data.f32bin'
        assert reg['data_sha256']==sha(source) and reg['request_sha256']==sha(folder/'queries.txt')
        assert reg['adapter_sha256']==flat_edge['adapter_sha256']
        q=qualify.check(source,folder/'queries.txt',folder/'result',native_squared_required=True);assert q['passed']
        reports['CPU_FLAT_INCLUSIVE_ADAPT/'+name]=q
    assert len(receipts)<=32
    knn=first(work/'tree_qualify_r3/outputs/tree_native_0');rng=first(work/'tree_diagnose/outputs/tree_native_1')
    assert knn==first(work/'tree_diagnose/outputs/tree_adapt_0')
    assert rng==first(work/'tree_diagnose/outputs/tree_adapt_1')==first(work/'tree_safe_qualify/outputs/tree_adapt_1')
    result=dict(status='A_QUALIFICATION_COMPLETE_WITH_GPU_TREE_BLOCKER',CPU_selected=cpu_quality,CPU_rows=selected['rows'],
        development_coordinate_disjointness=dict(passed=True,queries=32,input_snapshots=bindings,registration_sha256=sha(dev/'REGISTERED.json')),
        GPU_processes=len(receipts),primary_processes=0,receipts=receipts,checks=reports,
        tree_first_call_byte_and_selected_tree_identity=True,
        GPU_TREE_admission=False,GPU_TREE_blocker='native kNN 6/8 membership; N<8 unsupported; native tail OOB; safety overlay only bounded range qualified',
        GPU_RANGE_admission=True,CPU_tree_admission=True,CPU_FLAT_INCLUSIVE_ADAPT_admission=True,
        CPU_boundary_proof_sha256=sha(work/'CPU_TREE_ALL_LEAVES_EDGES.json'),CPU_FLAT_native_boundary_passed=read(work/'CPU_FLAT_EDGES.json')['passed'],
        CPU_FLAT_inclusive_proof_sha256=sha(work/'CPU_FLAT_INCLUSIVE_EDGES.json'),checker_sha256=sha(__file__),payload_checker_sha256=sha(Path(qualify.__file__)),
        semantic_scope='External tolerance only, not internal bitwise equality; static qualifiers, no end-to-end performance claim')
    from verify_a import verify
    verify(work,result,work/'CPU_TREE_ALL_LEAVES_EDGES.json',work/'CPU_FLAT_INCLUSIVE_EDGES.json')
    save(out,result)
    print('PASS stage A qualification with explicit GPU_TREE blocker',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','data','snapshots','library'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
