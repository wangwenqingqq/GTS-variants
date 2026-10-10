#!/usr/bin/env python3
"""Rebind a COMPLETE static matrix before publishing any paired comparison."""
import argparse,json,math,re
from pathlib import Path
import numpy as np
from qualify import cpu
import static_campaign as campaign
from static_check import check,read,requests
from rtp_results import paired
HERE=Path(__file__).resolve().parent

def verify_stage(work,stage,build,guard,qualification_source,original_source,retained_prefix=None):
    folder=work/stage;reg=read(folder/'REGISTERED.json')
    expected=campaign.jobs('primary')[:4] if stage=='primary' else campaign.jobs(stage)
    source_root=qualification_source if stage=='qualification' else original_source if stage=='primary' else HERE
    names=set(campaign.SOURCES)-({'STATIC_RECOVERY.json','static_preflight.py'} if stage!='recovery' else set())
    current={n:cpu.sha(source_root/n) for n in names}
    assert current['static_campaign.py']==cpu.sha(folder/'EXECUTED.py') and reg['source_sha256']==current
    assert reg['contract_sha256']==cpu.sha(HERE/'STATIC_CONTRACT.json')
    assert reg['inputs_sha256']==cpu.sha(work/'INPUTS.json') and reg['guard_sha256']==cpu.sha(guard)
    assert reg['build_sha256']==cpu.sha(build/'BUILD.json') and reg['jobs']==campaign.jobs(stage)
    if stage=='primary':
        assert retained_prefix is not None and not (folder/'COMPLETE.json').exists()
        rows=read(folder/'ROWS.json');guards=retained_prefix['guard_hashes'];proof_path=folder/'ROWS.json'
        assert retained_prefix['registration_sha256']==cpu.sha(folder/'REGISTERED.json')
        assert campaign.guard_labels(folder/'guards')=={j['label'] for j in campaign.jobs('primary')[:5]}
    else:
        proof_path=folder/('ADMISSION.json' if stage=='qualification' else 'COMPLETE.json');proof=read(proof_path)
        assert proof['passed'] and proof['jobs']==expected
        assert proof['registration_sha256']==cpu.sha(folder/'REGISTERED.json')
        for key in ('source_sha256','contract_sha256','build_sha256'):assert proof[key]==reg[key]
        rows=proof['rows'];guards=proof['guard_hashes']
        assert campaign.guard_labels(folder/'guards')==set(rows)
    assert set(rows)==set(guards)=={j['label'] for j in expected}
    inputs=read(work/'INPUTS.json')['records'];records=[]
    for job in expected:
        label=job['label'];r=inputs[job['snapshot']];prefix=folder/'outputs'/label
        assert campaign.guard_check(folder/'guards'/label)==guards[label]
        receipt=read(folder/'guards'/label/'receipt.json');cmd=read(folder/(label+'.command.json'))
        assert receipt['gpu']==reg['gpu'] and receipt['command'][1:3]==[f"--cpunodebind={reg['numa_node']}",f"--membind={reg['numa_node']}"]
        assert receipt['command'][3:]==cmd['command'] and cmd['environment']==reg['environment']
        assert cmd['request_sha256']==cpu.sha((folder/'requests' if stage=='recovery' else work/'requests')/(label+'.txt'))
        process=read(folder/(label+'.process.json'));assert process['returncode']==0 and all(math.isfinite(process[k]) and process[k]>=0 for k in ('wall_s','cpu_user_s','cpu_system_s','max_rss_bytes'))
        gold=read(work/'reference'/job['snapshot']/'REFERENCE.json');gold['folder']=work/'reference'/job['snapshot']
        actual=check(prefix,job['method'],requests(r['qids'],job['method'],job['order']),gold);assert actual==rows[label]
        if job['tool']:
            log=(folder/'guards'/label/'stdout.log').read_text()+(folder/'guards'/label/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
        meta=actual['timing'];keep=('preparation_ms','build_ms','warmup_ms','release_ms','range_pass_ms','knn_pass_ms','representation_bytes','index_bytes','memory_before','memory_built','memory_final','device_memory','device_used_before','device_used_built','device_used_final','workspace_bytes','context_ms','host_query_upload_bytes','extra_nonindexed_query_bytes')
        clean={k:meta[k] for k in keep if k in meta};clean.update(process=process,per_query_ms=actual['per_query_ms'])
        if job['method']=='GTSPP_P':
            s=read(str(prefix)+'.summary.json');clean.update(sampled_device_peak_bytes=s['sampled_device_peak_bytes'],host_output_capacity_bytes=s['host_output_capacity_bytes'])
        records.append(dict(**job,**clean,queries=actual['queries'],items=actual['items'],canonical_sha256=actual['canonical_sha256'],output_hashes=actual['output_hashes'],receipt_sha256=cpu.sha(folder/'guards'/label/'receipt.json'),quality_passed=True))
    return records,dict(registration_sha256=cpu.sha(folder/'REGISTERED.json'),proof_sha256=cpu.sha(proof_path),guard_hashes=guards,scope='retained incomplete prefix' if stage=='primary' else 'complete stage')

def main(a):
    assert not a.output.exists();inputs=campaign.verify_inputs(a.work)
    built=read(a.build/'BUILD.json');assert all(cpu.sha(a.build/'bin'/name)==sha for name,sha in built['binaries'].items())
    original=read(a.work/'primary/REGISTERED.json');a.gpu=original['gpu'];a.numa_node=original['numa_node']
    retained=campaign.stopped_prefix(a)
    qualifier,qbinding=verify_stage(a.work,'qualification',a.build,a.guard,a.qualification_source,a.original_source)
    prefix,pbinding=verify_stage(a.work,'primary',a.build,a.guard,a.qualification_source,a.original_source,retained)
    fresh,rbinding=verify_stage(a.work,'recovery',a.build,a.guard,a.qualification_source,a.original_source)
    rows=prefix+fresh
    assert len(qualifier)==6 and len(prefix)==4 and len(fresh)==68 and len(rows)==72
    assert [r['label'] for r in rows]==[j['label'] for j in campaign.jobs('primary')]
    qr=read(a.work/'qualification/REGISTERED.json');pr=read(a.work/'primary/REGISTERED.json');rr=read(a.work/'recovery/REGISTERED.json')
    assert rr['preserved_prefix']==retained
    assert rr['preflight_sha256']==cpu.sha(a.work/'recovery/DEPENDENCIES_PREFLIGHT.json')
    assert rr['recovery_contract_sha256']==cpu.sha(HERE/'STATIC_RECOVERY.json')
    for k in qr.keys()-{'jobs','registered_unix','source_sha256'}:assert qr[k]==pr[k]==rr[k],k
    for reg in (pr,rr):
        assert reg['qualification_registration_sha256']==cpu.sha(a.work/'qualification/REGISTERED.json') and reg['qualification_executed_sha256']==qr['source_sha256']['static_campaign.py'] and reg['qualification_checker_sha256']==qr['source_sha256']['static_check.py']
    for key in set(qr['source_sha256'])-{'static_campaign.py','static_check.py','static_native.py'}:
        assert qr['source_sha256'][key]==pr['source_sha256'][key]==rr['source_sha256'][key]
    for r in rows:
        if r['method']=='GTSPP_P':assert r['canonical_sha256']==next(q['canonical_sha256'] for q in qualifier if q['label']=='P_'+r['snapshot'])
    comparisons={}
    for snapshot in campaign.CONTRACT['snapshots']:
        comparisons[snapshot]={}
        for scope in ('knn_pass_ms','range_pass_ms','both_task_lifecycle_ms'):
            group={}
            methods=[m for m in campaign.CONTRACT['orders'][0] if m!='GPU_TREE_ADAPT' and m!='GTSPP_P' and (scope=='knn_pass_ms' and m!='GPU_RANGE_COMPLETE' or scope=='range_pass_ms' and m!='GPU_FLAT_KNN' or scope=='both_task_lifecycle_ms' and m.startswith('CPU'))]
            def time(row):return row[scope] if scope!='both_task_lifecycle_ms' else sum(row[k] for k in ('preparation_ms','build_ms','knn_pass_ms','range_pass_ms','release_ms'))
            for m in methods:
                left=[time(next(r for r in rows if r['snapshot']==snapshot and r['round']==i and r['method']==m)) for i in range(1,7)]
                right=[time(next(r for r in rows if r['snapshot']==snapshot and r['round']==i and r['method']=='GTSPP_P')) for i in range(1,7)]
                group[m+'/GTSPP_P']=paired(left,right,campaign.CONTRACT['orders'],m,'GTSPP_P')
            comparisons[snapshot][scope]=group
    result=dict(status='MEASURED_COMPLETE_EXTERNAL_STATIC',contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),source_base=campaign.CONTRACT['source'],shape=campaign.CONTRACT['shape'],rows=rows,comparisons=comparisons,qualification_rows=qualifier,bindings={'qualification':qbinding,'primary_prefix':pbinding,'recovery':rbinding},binary_sha256=built['binaries'],inputs_sha256=cpu.sha(a.work/'INPUTS.json'),checker_sha256=cpu.sha(__file__),source_sha256=campaign.sources(),blocked=campaign.CONTRACT['blocked'],external_primary_processes=72,external_primary_attempts=73,total_primary_processes_including_RTP=91,retained_pre_build_CPU_failure=1,cumulative_GPU_qualifier_attempts=32,retained_pre_CUDA_failure=1,limits=campaign.CONTRACT['limits'])
    cpu.save(a.output,result);print('PASS all72 bound full-output rows and frozen paired statistics',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','build','guard','output','qualification-source','original-source'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
