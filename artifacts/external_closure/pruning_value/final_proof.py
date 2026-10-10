#!/usr/bin/env python3
"""Reconcile retained execution identities and recheck every output without launching CUDA."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import analyze
from build import sha,save,outside_repo
if not __debug__:raise RuntimeError('Python assertions are required')

def read(p):return json.loads(Path(p).read_text())
def files(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def guard(folder,gpu):
    r=read(folder/'receipt.json');assert r['runtime_valid'] and r['exit_code']==0 and r['stop_reason'] is None and r['gpu']==gpu
    assert r['command']==read(folder/'command.json')
    assert r['observer']=='two-sided-starttime-v1' and read(folder/'checks.json')
    assert all(not x['foreign'] and all(o['owned'] for o in x['identities']) for x in read(folder/'checks.json'))
    for f in ('before.json','after.json'):assert not read(folder/f)['apps']
    return r

def sass_functions(path,normalize):
    result={};key=None
    for line in normalize(path.read_text()).splitlines():
        if line.startswith('Function:'):key=line[10:];result[key]=[]
        elif key and line.endswith(';'):result[key].append(line)
    return result

def main(a):
    root=a.work;c=a.campaign;reg=read(c/'REGISTERED.json');executed=root/'executed_code'
    assert all(sha(executed/k)==v for k,v in reg['source_hashes'].items())
    assert reg['contract_sha256']==sha(executed/'CONTRACT.json')==sha(Path(__file__).parent/'CONTRACT.json')
    assert sha(a.inputs)==reg['inputs_sha256'];inputs=read(a.inputs)['records']
    built=read(root/'build/BUILD.json');compiled=read(root/'build/REGISTERED.json')
    assert built==reg['build'] and compiled['probe_sha256']==sha(executed/'probe.cu')==sha(Path(__file__).parent/'probe.cu')
    assert compiled['contract_sha256']==reg['contract_sha256']
    assert files(a.parent/'source')==compiled['parent_sources']==read(a.parent/'PREPARED.json')['sources']
    assert sha(a.parent/'PREPARED.json')=='bcd1ad0b75406f7ee8a690bbc30d6f9543369118a383b82a5b9a751e39e7414f'
    assert all(sha(root/'build'/k)==v for k,v in built.items())
    for name,r in inputs.items():
        assert sha(r['data'])==r['data_sha256'] and sha(a.references/name/'REFERENCE.json')==r['reference_sha256']
        assert list(map(int,(c/(name+'.qids')).read_text().split()))==r['qids']
        if r.get('snapshot_sha256'):assert sha(Path(r['snapshot'])/'SNAPSHOT.json')==r['snapshot_sha256']
    assert sha(a.guard)=='36e9b8f341093613e8671be47f956ea0ae34de66e2f1723326f81b84fd09a4cb','guard differs from the tracked task-owned implementation'
    rejected=a.rejected_campaign
    assert 'RuntimeError: GPU occupied before admission' in a.rejected_log.read_text()
    assert {p.name for p in rejected.iterdir()}=={'REGISTERED.json','initial.qids','first_rebuilt.qids','bounded.qids','bounded_capture_guard'}
    assert not list((rejected/'bounded_capture_guard').iterdir()),'rejected admission must have no child/monitor/command artifacts'
    assert read(rejected/'REGISTERED.json')['build']==built
    rechecked=root/'rechecked_v3';rechecked.mkdir(exist_ok=False);verified=[]
    expected=[('bounded_capture','bounded','capture',None),('bounded_timing','bounded','timing',None)]+[(f'bounded_{t}','bounded','timing',t) for t in ('memcheck','racecheck','synccheck','initcheck')]+[(f'{n}_{s}',n,s,None) for n in ('initial','first_rebuilt') for s in ('capture','timing')]
    assert reg['jobs']==[list(x) for x in expected]
    actual={p.name for p in c.iterdir()}
    wanted={'REGISTERED.json'}|{n+'.qids' for n in inputs}|{n+'_cache' for n in inputs}
    for label,_,_,_ in expected:wanted|={label,label+'_guard',label+'_PASSED.json'}
    wanted|={label+'_checked' for label,_,mode,_ in expected if mode=='timing'}
    assert actual==wanted,('unexpected or missing process artifact',actual^wanted)
    for label,name,mode,tool in expected:
        assert read(c/(label+'_PASSED.json'))['passed'];receipt=guard(c/(label+'_guard'),reg['gpu']);command=receipt['command']
        requested=[str(root/'build'/mode),inputs[name]['data'],str(c/(name+'.qids')),str(c/label),str(c/(name+'_cache'))]
        assert command[-5:]==requested
        assert command[:3]==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}"]
        if tool:
            assert command[3:8]==['/usr/local/bin/compute-sanitizer','--tool',tool,'--error-exitcode','90']
            assert sha('/usr/local/bin/compute-sanitizer')==receipt['binary_sha256']
            text=''.join((c/(label+'_guard')/f).read_text() for f in ('stdout.log','stderr.log'))
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if tool=='racecheck' else 'ERROR SUMMARY: 0 errors') in text
        else:assert receipt['binary_sha256']==built[mode]
        if mode=='timing':
            cache=c/(name+'_cache');hashes=read(cache/'CAPTURE.json')['cache_hashes']
            assert all(sha(cache/k)==v for k,v in hashes.items())
            assert all(sha(rechecked/(name+'_capture')/k)==v for k,v in hashes.items()),'cache must reproduce actual observed candidates, not merely full answers'
            assert all((cache/k).stat().st_mtime_ns<(c/(label+'_guard')/'command.json').stat().st_mtime_ns for k in hashes)
        audit=a.audits/('stress4096_B1/build2' if name=='bounded' else 'million_prefix_B1/build'+('2' if name=='initial' else '3'))
        args=SimpleNamespace(root=c/label,reference=a.references/name,qids=c/(name+'.qids'),audit=audit,output=rechecked/label)
        getattr(analyze,mode)(args)
        proof=read(args.output/('CAPTURE.json' if mode=='capture' else 'TIMING.json'))
        old=c/(name+'_cache' if mode=='capture' else label+'_checked')
        original=read(old/('CAPTURE.json' if mode=='capture' else 'TIMING.json'))
        keys=set(proof)-({'cache_CPU_construct_ms'} if mode=='capture' else set())
        assert {k:proof[k] for k in keys}=={k:original[k] for k in keys}
        for name_csv in (('layers.csv','subtree_sizes.csv','queries.csv') if mode=='capture' else ('passes.csv',)):
            assert sha(args.output/name_csv)==sha(old/name_csv),'published table differs from strict recomputation'
        verified.append(dict(label=label,passed=True,complete_answers=proof['exact_outputs'],guard_sha256=sha(c/(label+'_guard')/'receipt.json'),binary_sha256=built[mode],output_hashes=files(c/label),quality_sha256=sha(args.output/('CAPTURE.json' if mode=='capture' else 'TIMING.json'))))
    # Build-only supplement consumes the final registered process, with no query timing.
    m=root/'maintenance';receipt=guard(m/'build_guard',reg['gpu']);mr=read(m/'BUILD_ONLY_REGISTERED.json')
    assert mr['budget_position']==mr['maximum']==11 and mr['query_count']==0 and mr['binary_sha256']==receipt['binary_sha256']==built['capture']
    assert receipt['command']==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",str(root/'build/capture'),str(m/'second.f32bin'),str(c/'initial.qids'),str(m/'tree'),'BUILD_ONLY']
    assert [p.name for p in m.glob('*guard')]==['build_guard'] and not analyze.table(m/'tree/queries.csv')
    assert mr['gpu']==reg['gpu'] and mr['numa']==reg['numa'] and mr['contract_sha256']==reg['contract_sha256']

    assert sha(m/'second.f32bin')==mr['data_sha256']==read(m/'PREPARED.json')['second_data_sha256']
    analyze.bind_tree(m/'tree',m/'audit/build0')
    assert read(m/'MAINTENANCE_V2.json')['passed'] and read(m/'CONTENT_IDENTITY.json')['content_ids_sha256']==sha(m/'content_ids.npy')
    utility=a.repo/'artifacts/rebuild_tree_baselines/verify_profile.py';spec=importlib.util.spec_from_file_location('normalize',utility);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    original=sass_functions(root/'parent.sass',module.normalize_dump);fresh=sass_functions(root/'timing.sass',module.normalize_dump)
    assert len(original)==113 and len(fresh)==114 and all(original[k]==fresh.get(k) for k in original)
    additions=set(fresh)-set(original);assert len(additions)==1 and 'range_fields' in next(iter(additions))
    selected={k:dict(instructions=len(fresh[k]),normalized_sha256=hashlib.sha256('\n'.join(fresh[k]).encode()).hexdigest()) for k in fresh if any(x in k for x in ('parent_groups','verify_materialized','verify_distancesILi1ELb0ELb1','pack32','collect','range_fields'))}
    save(root/'FINAL_PROOF_V3.json',dict(passed=True,GPU_processes=11,complete_answers=sum(x['complete_answers'] for x in verified),preferred_device_pre_admission_rejection_no_GPU_child=True,executed_source_hashes=reg['source_hashes'],current_CPU_verifier_hashes={p.name:sha(p) for p in Path(__file__).parent.glob('*.py')},binary_sha256=built,parent_prepared_sha256=sha(a.parent/'PREPARED.json'),guard_sha256=sha(a.guard),registered_sha256=sha(c/'REGISTERED.json'),input_manifest_sha256=sha(a.inputs),input_identities={k:{f:v for f,v in r.items() if f.endswith('sha256')} for k,r in inputs.items()},verified=verified,SASS=dict(original_functions=113,unchanged_original_functions=113,added_output_adapter_functions=1,selected=selected),maintenance_sha256=sha(m/'MAINTENANCE_V2.json'),binding_scope='Original launch guard receipts plus post-run byte/hash reconciliation; stricter CPU checker rerun, not GPU rerun. Original runner did not emit per-launch cache hashes; retained files match capture hashes, reconstructed candidates and untouched timestamps. Future runner adds before/after hash receipts. No claim of retroactively collecting those receipts.',guard_source_matches_task_copy=True))
    save(root/'RAW_MANIFEST_V3.json',dict(campaign=files(c),build=files(root/'build'),executed_code=files(executed),maintenance={str(p.relative_to(m)):sha(p) for p in m.rglob('*') if p.is_file() and p.name!='second.f32bin'},final_proof_sha256=sha(root/'FINAL_PROOF_V3.json')))
    print('PASS: 11 processes, all complete answers, exact replay candidates, original tree identity, 113 unchanged GPU functions; no CUDA launched')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','campaign','rejected-campaign','rejected-log','inputs','references','audits','parent','guard','repo'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.work=outside_repo(a.work);main(a)
