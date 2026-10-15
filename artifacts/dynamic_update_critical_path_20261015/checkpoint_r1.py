"""Audit the stopped R1 without running CUDA or converting it into native evidence."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import collections
import json
from pathlib import Path
from common import HERE, PARENT, load, save, sha, jobs, module
from campaign import command

exact_directory=module('parent_checkpoint_directory_check',PARENT/'audit_stage.py').exact_directory


def output_names(job):
    if job['kind']=='selftest':return set()
    suffixes={'copy.csv','meta.json'} if job['kind']=='copy' else {
        'queries.csv','ops.csv','ids.i32','dist.f32','squared.f64','authority.f64',
        'physical.i32','reverse.i32','mutations.i32','final.json','stages.csv','output.csv','meta.json'}
    if job['kind']=='micro':suffixes.add('ordering.csv')
    if job['kind']=='service' and job['mode']=='S2_STALE':suffixes|={'means.f32','ordering.csv'}
    return {job['label']+'.'+s for s in suffixes}


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=a.root.resolve();w=root/'work_r1';reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');out=a.out.resolve()
    assert not out.exists() and sha(w/'REGISTERED.json')==ready['registration_sha256'] and ready['passed']
    frozen=root/'code/artifacts/dynamic_update_critical_path_20261015';assert sha(frozen/'CONTRACT.json')==reg['contract_sha256']
    for name in ('CONTRACT.json','common.py','campaign.py'):assert sha(HERE/name)==sha(frozen/name)
    for name,h in reg['sources'].items():assert sha(root/'code'/name)==h
    for name,h in reg['generated'].items():assert sha(w/name)==h
    for variant,h in ready['binaries'].items():assert sha(w/'build'/variant/'service')==h
    assert not (w/'timeline').exists() and load(root/'SOURCE_AUDIT_STOP_R1.json')['no_foreign_signals']
    cleanup=load(root/'ORPHAN_MONITOR_STOP_R1.json');assert cleanup['no_GPU_process_or_setting_changed'] and cleanup['signal']=='SIGTERM'
    failed_archive=load(root/'ARCHIVE_FAILURE_R1.json');assert not failed_archive['passed'] and failed_archive['exit_code']==1 and failed_archive['GPU_starts']==0
    starts=[json.loads(line) for line in (w/'STARTS.jsonl').read_text().splitlines()];assert len(starts)==84
    expected_ledger=[];records=[];quality=[]
    for stage in ('qualification','primary'):
        result=load(w/stage/'RESULTS.json');expected=jobs(stage);rows=result['rows'];assert len(rows)==len(expected)
        registered=load(w/stage/'REGISTERED.json');assert registered['jobs']==expected and registered['executor_sha256']==sha(frozen/'campaign.py')
        assert result['complete']==(stage=='qualification')
        started=[r for r in rows if r['status']!='not_executed'];passed=[r for r in rows if r['status']=='passed']
        files={'REGISTERED.json','RESULTS.json'}|{r['label']+s for r in started for s in ('.command.json','.outer.log')}|{r['label']+'.checked.json' for r in passed}
        exact_directory(w/stage,files,('guards','outputs','reports'))
        exact_directory(w/stage/'guards',(),[r['label'] for r in started]);exact_directory(w/stage/'reports',())
        exact_directory(w/stage/'outputs',set().union(*(output_names(r) for r in started)))
        for job,row in zip(expected,rows):
            label=job['label'];assert all(row[k]==v for k,v in job.items());status=row['status']
            record=dict(stage=stage,job=job,status=status,native_Host_attribution_admissible=False)
            if status!='not_executed':
                path=w/stage/(label+'.command.json');cmd=command(job,w,reg,w/stage/'outputs'/label)
                assert load(path)==dict(command=cmd);expected_ledger.append((stage,label,sha(path)))
                record['command_sha256']=sha(path)
            if status=='passed':
                g=w/stage/'guards'/label;r=load(g/'receipt.json')
                assert r['runtime_valid'] and r['exit_code']==0 and r['stop_reason'] is None and r['observer']=='two-sided-starttime-v1'
                assert r['command']==load(g/'command.json')==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
                assert not load(g/'before.json')['apps'] and not load(g/'after.json')['apps'] and all(not x['foreign'] for x in load(g/'checks.json'))
                assert sha(g/'receipt.json')==row['guard_sha256'] and sha(w/stage/(label+'.checked.json'))==row['checked_sha256']
                assert set(row['guard_files'])=={p.name for p in g.iterdir() if p.is_file()}
                exact_directory(g,{'command.json','before.json','after.json','checks.json','receipt.json','stdout.log','stderr.log','gpu.csv'})
                for name,h in row['guard_files'].items():assert sha(g/name)==h
                original=load(w/stage/(label+'.checked.json'))
                assert set(original.get('raw_outputs',{}))==output_names(job)
                for name,identity in original.get('raw_outputs',{}).items():
                    path=w/stage/'outputs'/name;assert sha(path)==identity['sha256'] and path.stat().st_size==identity['bytes']
                record.update(checked_sha256=row['checked_sha256'],guard_sha256=row['guard_sha256'],guard_files=row['guard_files'],raw_outputs=original.get('raw_outputs',{}))
                if job['kind']=='selftest':
                    assert original['passed'] and original['query_checks']==400
                    if job.get('tool'):assert original['sanitizer_summary_zero']
                    quality.append(dict(stage=stage,label=label,selftest=True,original_passed=True))
                else:
                    hardened=root/'OFFLINE_HARDENED_R1'/(label+'.checked.json');current=load(hardened)
                    assert current['passed'] and current['raw_outputs']==original['raw_outputs']
                    record['hardened_checked_sha256']=sha(hardened)
                    if job['kind']=='micro':
                        quality.append(dict(stage=stage,label=label,complete_queries=current['complete_queries'],
                            false_negatives=current['false_negatives'],false_positives=current['false_positives'],
                            exact_native_squared_bits=current['exact_native_squared_bits'],max_native_scaled_error=current['max_native_scaled_error'],
                            independent_full_maps=current['independent_full_maps'],final_device_vector_bytes_compared=current['final_device_vector_bytes_compared']))
                    else:quality.append(dict(stage=stage,label=label,kind=job['kind'],hardened_output_passed=True))
            elif status=='failed':
                assert label=='r4_service_S1' and row['error'].splitlines()[-1]=='KeyboardInterrupt'
                assert not (w/stage/'guards'/label/'receipt.json').exists()
                exact_directory(w/stage/'guards'/label,{'command.json','before.json','stdout.log','stderr.log','gpu.csv'})
                record.update(reason='Controller interrupted after source-audit stop;guard completion proof absent.',measurement_accepted=False,
                    output_only_recheck_passed=load(root/'OFFLINE_HARDENED_R1/INTERRUPTED_OUTPUT_ONLY.json')['passed_output_only'])
            else:assert status=='not_executed'
            records.append(record)
    assert [(r['stage'],r['label'],r['command_sha256']) for r in starts]==expected_ledger and [r['start'] for r in starts]==list(range(1,85))
    assert collections.Counter(r['status'] for r in records)==dict(passed=83,failed=1,not_executed=29)
    recheck=load(root/'OFFLINE_HARDENED_R1/RESULTS.json');assert recheck['complete'] and len(recheck['rows'])==75 and recheck['GPU_starts']==0
    out.mkdir();save(out/'EXECUTION_R1.json',dict(complete=False,state='STOPPED_SOURCE_AUDIT',GPU_starts=84,
        original_max_GPU_starts=124,qualification_passed=29,primary_passed=54,interrupted=1,primary_not_executed=29,timeline_not_executed=11,
        native_Host_attribution_admissible=False,reason='R1 annotation scope destroys validation set before copy submission instead of after stream synchronization.',
        no_foreign_signals=True,automatic_retries=0,exact_partial_stage_census=True,start_ledger_sha256=sha(w/'STARTS.jsonl'),
        interrupted_telemetry_child_cleanup='Only the verified task-owned read-only monitor was terminated;its incomplete sample remains excluded.',records=records))
    save(out/'QUALITY_R1.json',dict(output_recheck_passed=True,nonselftest_rows_rechecked=75,selftests=8,
        interrupted_output_only_not_measurement=True,checker_sha256=sha(root/'offline_fix_code/artifacts/dynamic_update_critical_path_20261015/quality.py'),
        does_not_repair_R1_timing_provenance=True,records=quality))
    save(out/'IDENTITY_R1.json',dict(parent_commit=load(frozen/'CONTRACT.json')['parent_commit'],contract_sha256=reg['contract_sha256'],
        executed_sources=reg['sources'],generated=reg['generated'],binaries=ready['binaries'],libraries=ready['libraries'],
        original_registration_sha256=sha(w/'REGISTERED.json'),ready_sha256=sha(w/'READY.json'),selected_query_SASS=load(w/'STATIC.json'),
        hardened_recheck_sha256=sha(root/'OFFLINE_HARDENED_R1/RESULTS.json'),placement='Initially idle same-model GPU;private physical placement.'))
    raw={str(path.relative_to(w)):dict(bytes=path.stat().st_size,sha256=sha(path)) for path in sorted(w.rglob('*')) if path.is_file() and path.name!='campaign.lock'}
    archive=root/'RAW_MEASUREMENTS_R1_STABLE.tar.gz';assert archive.is_file()
    save(out/'RAW_MANIFEST_R1.json',dict(scope='Raw stopped-run files retained externally;hashes only,no raw database or private environment contents.',files=raw,
        stable_archive=dict(bytes=archive.stat().st_size,sha256=sha(archive),contains='Original code,all work outputs,guards,stop/preflight/run logs and cleanup record;not external parent data or reference caches.'),
        first_archive_rejected=dict(bytes=failed_archive['bytes'],sha256=failed_archive['sha256'],exit_code=1,reason='Incomplete-sample telemetry still appended during tar;first archive retained,not accepted.'),
        interrupted_telemetry='Read-only collector outlived interrupted controller;verified ownership by uid,starttime,exact command and open log descriptor before terminating only that monitor. Failed log includes post-stop samples and is excluded from all attribution.',
        cleanup_receipt_sha256=sha(root/'ORPHAN_MONITOR_STOP_R1.json'),original_stop_receipt_sha256=sha(root/'SOURCE_AUDIT_STOP_R1.json')))
    print('CHECKPOINT_VERIFIED:84 starts,83 passed,1 interrupted,40 unexecuted;75 hardened offline checks;NO native attribution claim;0 new GPU starts')


if __name__=='__main__':main()
