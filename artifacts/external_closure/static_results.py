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

def verify_stage(work,stage,build,guard,qualification_source):
    folder=work/stage;reg=read(folder/'REGISTERED.json');proof=read(folder/('ADMISSION.json' if stage=='qualification' else 'COMPLETE.json'))
    assert proof['passed'] and reg['jobs']==proof['jobs']==campaign.jobs(stage)
    assert proof['registration_sha256']==cpu.sha(folder/'REGISTERED.json')
    current=campaign.sources()
    if stage=='qualification':
        for name in ('static_campaign.py','static_check.py'):current[name]=cpu.sha(qualification_source/name)
    assert current['static_campaign.py']==cpu.sha(folder/'EXECUTED.py')
    assert reg['source_sha256']==proof['source_sha256']==current
    assert reg['contract_sha256']==proof['contract_sha256']==cpu.sha(HERE/'STATIC_CONTRACT.json')
    assert reg['inputs_sha256']==cpu.sha(work/'INPUTS.json') and reg['guard_sha256']==cpu.sha(guard)
    assert reg['build_sha256']==proof['build_sha256']==cpu.sha(build/'BUILD.json')
    assert reg['source_sha256']['static_campaign.py']==cpu.sha(folder/'EXECUTED.py')
    assert set(proof['rows'])==set(proof['guard_hashes'])=={j['label'] for j in reg['jobs']}
    assert campaign.guard_labels(folder/'guards')==set(proof['rows'])
    inputs=read(work/'INPUTS.json')['records'];records=[]
    for job in reg['jobs']:
        label=job['label'];r=inputs[job['snapshot']];prefix=folder/'outputs'/label
        assert campaign.guard_check(folder/'guards'/label)==proof['guard_hashes'][label]
        receipt=read(folder/'guards'/label/'receipt.json');cmd=read(folder/(label+'.command.json'))
        assert receipt['gpu']==reg['gpu'] and receipt['command'][1:3]==[f"--cpunodebind={reg['numa_node']}",f"--membind={reg['numa_node']}"]
        assert receipt['command'][3:]==cmd['command'] and cmd['environment']==reg['environment']
        assert cmd['request_sha256']==cpu.sha(work/'requests'/(label+'.txt'))
        process=read(folder/(label+'.process.json'));assert process['returncode']==0 and all(math.isfinite(process[k]) and process[k]>=0 for k in ('wall_s','cpu_user_s','cpu_system_s','max_rss_bytes'))
        gold=read(work/'reference'/job['snapshot']/'REFERENCE.json');gold['folder']=work/'reference'/job['snapshot']
        actual=check(prefix,job['method'],requests(r['qids'],job['method'],job['order']),gold);assert actual==proof['rows'][label]
        if job['tool']:
            log=(folder/'guards'/label/'stdout.log').read_text()+(folder/'guards'/label/'stderr.log').read_text()
            assert ('RACECHECK SUMMARY: 0 hazards displayed (0 errors, 0 warnings)' if job['tool']=='racecheck' else 'ERROR SUMMARY: 0 errors') in log
        meta=actual['timing'];keep=('preparation_ms','build_ms','warmup_ms','release_ms','range_pass_ms','knn_pass_ms','representation_bytes','index_bytes','memory_before','memory_built','memory_final','device_memory','device_used_before','device_used_built','device_used_final','workspace_bytes','context_ms','host_query_upload_bytes','extra_nonindexed_query_bytes')
        clean={k:meta[k] for k in keep if k in meta};clean.update(process=process,per_query_ms=actual['per_query_ms'])
        if job['method']=='GTSPP_P':
            s=read(str(prefix)+'.summary.json');clean.update(sampled_device_peak_bytes=s['sampled_device_peak_bytes'],host_output_capacity_bytes=s['host_output_capacity_bytes'])
        records.append(dict(**job,**clean,queries=actual['queries'],items=actual['items'],canonical_sha256=actual['canonical_sha256'],output_hashes=actual['output_hashes'],receipt_sha256=cpu.sha(folder/'guards'/label/'receipt.json'),quality_passed=True))
    return records,dict(registration_sha256=cpu.sha(folder/'REGISTERED.json'),proof_sha256=cpu.sha(folder/('ADMISSION.json' if stage=='qualification' else 'COMPLETE.json')),guard_hashes=proof['guard_hashes'])

def main(a):
    assert not a.output.exists();inputs=campaign.verify_inputs(a.work)
    built=read(a.build/'BUILD.json');assert all(cpu.sha(a.build/'bin'/name)==sha for name,sha in built['binaries'].items())
    qualifier,qbinding=verify_stage(a.work,'qualification',a.build,a.guard,a.qualification_source);rows,pbinding=verify_stage(a.work,'primary',a.build,a.guard,a.qualification_source)
    assert len(qualifier)==6 and len(rows)==72
    qr=read(a.work/'qualification/REGISTERED.json');pr=read(a.work/'primary/REGISTERED.json')
    for k in qr.keys()-{'jobs','registered_unix','source_sha256'}:assert qr[k]==pr[k],k
    assert pr['qualification_registration_sha256']==cpu.sha(a.work/'qualification/REGISTERED.json') and pr['qualification_executed_sha256']==qr['source_sha256']['static_campaign.py'] and pr['qualification_checker_sha256']==qr['source_sha256']['static_check.py']
    assert {k:v for k,v in qr['source_sha256'].items() if k not in ('static_campaign.py','static_check.py')}=={k:v for k,v in pr['source_sha256'].items() if k not in ('static_campaign.py','static_check.py')}
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
    result=dict(status='MEASURED_COMPLETE_EXTERNAL_STATIC',contract_sha256=cpu.sha(HERE/'STATIC_CONTRACT.json'),source_base=campaign.CONTRACT['source'],shape=campaign.CONTRACT['shape'],rows=rows,comparisons=comparisons,qualification_rows=qualifier,bindings={'qualification':qbinding,'primary':pbinding},binary_sha256=built['binaries'],inputs_sha256=cpu.sha(a.work/'INPUTS.json'),checker_sha256=cpu.sha(__file__),source_sha256=campaign.sources(),blocked=campaign.CONTRACT['blocked'],external_primary_processes=72,total_primary_processes_including_RTP=90,cumulative_GPU_qualifier_attempts=32,retained_pre_CUDA_failure=1,limits=campaign.CONTRACT['limits'])
    cpu.save(a.output,result);print('PASS all72 bound full-output rows and frozen paired statistics',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('work','build','guard','output','qualification-source'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();assert __debug__;main(a)
