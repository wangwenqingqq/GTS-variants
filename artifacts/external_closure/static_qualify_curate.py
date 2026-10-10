#!/usr/bin/env python3
"""Publish only bound qualification evidence, never qualification speed claims."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
import static_campaign as campaign
from static_check import read
cpu=campaign.cpu
HERE=Path(__file__).resolve().parent

def curate(root):
    proof=read(root/'campaign_r2/qualification/ADMISSION.json')
    recheck=read(root/'QUALIFICATION_RECHECK_R3.json')
    assert recheck['passed'] and recheck['GPU_reruns']==0
    assert recheck['admission_sha256']==cpu.sha(root/'campaign_r2/qualification/ADMISSION.json')
    assert recheck['new_source_sha256']=={n:cpu.sha(root/'repo_r3/artifacts/external_closure'/n) for n in recheck['new_source_sha256']}
    assert recheck['new_source_sha256']['static_check.py']==cpu.sha(HERE/'static_check.py')
    assert recheck['old_source_sha256']==proof['source_sha256']
    assert recheck['registration_sha256']==proof['registration_sha256']==cpu.sha(root/'campaign_r2/qualification/REGISTERED.json')
    assert proof['contract_sha256']==cpu.sha(HERE/'STATIC_CONTRACT.json')
    expected={j['label'] for j in campaign.jobs('qualification')}
    assert proof['passed'] and set(recheck['rows'])==set(proof['rows'])==set(proof['guard_hashes'])==expected
    assert campaign.guard_labels(root/'campaign_r2/qualification/guards')==expected
    rows=[]
    for job in campaign.jobs('qualification'):
        name=job['label'];row=proof['rows'][name];guard=root/'campaign_r2/qualification/guards'/name
        assert row['passed'] and all(q['passed'] for q in row['per_query'])
        assert campaign.guard_check(guard)==proof['guard_hashes'][name]
        for name,h in row['output_hashes'].items():assert cpu.sha(root/'campaign_r2/qualification/outputs'/name)==h
        rows.append(dict(**job,**{k:row[k] for k in ('passed','queries','items','canonical_sha256','output_hashes')}))
    failed=root/'campaign/qualification';failed_guards=failed/'guards'
    assert campaign.guard_labels(failed_guards)=={'P_bounded_memcheck'}
    assert not (failed_guards/'P_bounded_memcheck/receipt.json').exists()
    assert not list((failed/'outputs').iterdir())
    assert '/usr/bin/time' in (failed_guards/'P_bounded_memcheck/stderr.log').read_text()
    spec=importlib.util.spec_from_file_location('static_normalize',HERE.parent/'rebuild_tree_baselines/verify_profile.py')
    normal=importlib.util.module_from_spec(spec);spec.loader.exec_module(normal)
    sass={}
    for name,pair,count in [('P',('parent.sass','static.sass'),113),('range',('range_parent.sass','range_static.sass'),5)]:
        a,b=[normal.normalize_dump((root/p).read_text()) for p in pair]
        assert a==b and sum(line.startswith('Function:') for line in a.splitlines())==count
        sass[name]=dict(functions=count,instructions=sum(line.endswith(';') for line in a.splitlines()),normalized_sha256=hashlib.sha256(a.encode()).hexdigest(),raw_sha256={p:cpu.sha(root/p) for p in pair})
    inputs=read(root/'campaign_r2/INPUTS.json');refs={}
    for name,r in inputs['records'].items():
        path=root/'campaign/reference'/name/'REFERENCE.json';ref=read(path)
        assert cpu.sha(path)==r['reference_sha256'] and ref['data_sha256']==r['data_sha256']
        refs[name]=dict(N=ref['N'],D=ref['D'],queries=len(r['qids']),data_sha256=r['data_sha256'],reference_sha256=r['reference_sha256'])
    return dict(status='QUALIFIED_HOST_READY_ADAPTERS_NOT_EXTERNAL_SPEEDUP',shape=campaign.CONTRACT['shape'],snapshots=refs,
        rows=rows,sass_identity=sass,binaries=read(root/'build/BUILD.json')['binaries'],
        build_sha256=cpu.sha(root/'build/BUILD.json'),build_registration_sha256=cpu.sha(root/'build/BUILD_REGISTERED.json'),
        prepared_sha256=cpu.sha(root/'build/PREPARED.json'),prepared_contract_sha256=read(root/'build/PREPARED.json')['contract_sha256'],
        runtime_contract_sha256=proof['contract_sha256'],executed_source_sha256=proof['source_sha256'],
        strengthened_checker_source_sha256=recheck['new_source_sha256'],guard_hashes=proof['guard_hashes'],
        qualification_proof_sha256=recheck['admission_sha256'],recheck_sha256=cpu.sha(root/'QUALIFICATION_RECHECK_R3.json'),
        failed_attempt_file_hashes={str(p.relative_to(failed)):cpu.sha(p) for p in failed.rglob('*') if p.is_file()},
        resource_wrapper_failure=1,successful_new_GPU_qualifiers=6,cumulative_GPU_qualifier_attempts=32,
        planned_external_primaries=72,planned_total_primaries_including_RTP=90,primary_ceiling=102,
        hardware=dict(GPU='RTX PRO 6000 Blackwell Server Edition',SM=120,CUDA='13.1.115',driver='590.48.01',CPU='shared host, one native thread, fixed NUMA placement'),
        blocked=campaign.CONTRACT['blocked'],limits=campaign.CONTRACT['limits'],curator_sha256=cpu.sha(__file__))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--raw',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    assert not a.output.exists();a.output.write_text(json.dumps(curate(a.raw),indent=2)+'\n')
