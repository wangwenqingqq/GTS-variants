"""Revalidate raw identities and publish scalar evidence, never private placement."""
import argparse,csv,json,re,shutil
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from campaign import prepared,previous,stats,jobs
from trace import HERE,read,save,sha
def csvrows(p):
    with Path(p).open() as f:return list(csv.DictReader(f))
def curate(w,out,freeze):
    assert not out.exists();assert read(freeze)=={'curate.py':sha(HERE/'curate.py')};reg=prepared(w);ready=read(w/'READY.json');previous(w,'qualification',reg);previous(w,'A',reg)
    a=stats(w,'A');assert a==read(w/'A/STATS.json')
    stages=['qualification','A'];b=None
    if a['decision']=='GO_DYNAMIC_PROGRESSIVE':
        previous(w,'B',reg);b=stats(w,'B');assert b==read(w/'B/STATS.json');stages.append('B')
        if b['decision']=='PASS_UPDATE_HEAVY':previous(w,'B_probes',reg);stages.append('B_probes')
    else:assert not (w/'B').exists() and not (w/'B_probes').exists(),'no B admission after gray/non-GO'
    starts=[json.loads(s) for s in (w/'STARTS.jsonl').read_text().splitlines()];prior=reg.get('recovery',{}).get('prior_starts',0)
    assert [s['start'] for s in starts]==list(range(1,len(starts)+1)) and [s['global_start'] for s in starts]==list(range(prior+1,prior+len(starts)+1))
    assert [(s['stage'],s['label']) for s in starts]==[(stage,job['label']) for stage in stages for job in jobs(stage)]
    for s in starts:assert s['command_sha256']==sha(w/s['stage']/(s['label']+'.command.json'))
    out.mkdir();(out/'evidence').mkdir();(out/'inputs').mkdir();(out/'timing').mkdir();(out/'updates').mkdir();(out/'memory').mkdir();(out/'operations').mkdir();(out/'correctness').mkdir()
    processes=[];receipts=[];memory=[];operation_rows=[]
    for stage in stages:
        for row in read(w/stage/'RESULTS.json')['rows']:
            label=row['label'];c=read(w/stage/(label+'.checked.json'));assert c['passed']
            processes.append(dict(stage=stage,label=label,**c));receipts.append(dict(stage=stage,label=label,checked_sha256=row['checked_sha256'],guards=row['guard_hashes'],outputs=c['output_hashes']))
            g=w/stage/'guards'/label;telemetry=csvrows_no_header(g/'gpu.csv');sampled=max((float(r[1]) for r in telemetry),default=None)
            for name in ('before','after'):
                snapshot=read(g/(name+'.json'));assert not snapshot['apps']
            if stage in ('A','B'):
                p=out/'operations/raw'/stage;p.mkdir(parents=True,exist_ok=True)
                for suffix in ('.ops.csv','.ownership.csv','.queries.csv'):shutil.copyfile(w/stage/'outputs'/(label+suffix),p/(label+suffix))
                meta=c['measured']['meta'];memory.append(dict(stage=stage,label=label,meta=meta,sampled_device_peak_MiB=sampled,sampling_ms=200,sampled_not_exact_peak=True))
                operation_rows.append(dict(stage=stage,label=label,**c['measured']['op_totals_ms'],trace_ms=meta['trace_ms'],events_ms=meta['events_ms'],release_ms=meta['release_ms'],unattributed_event_bookkeeping_ms=meta['events_ms']-sum(c['measured']['op_totals_ms'].values())))
    save(out/'evidence/QUALITY_PROCESSES.json',processes);save(out/'evidence/QUALITY_RECEIPTS.json',receipts)
    save(out/'timing/TRACE_A.json',a);save(out/'timing/TRACE_B.json',b or dict(status='NOT_EXECUTED',reason='A_UNCLASSIFIED_or_non_GO',measurement=None,pairs=0,conditional_rule='only after A GO'))
    save(out/'operations/OP_BREAKDOWN.json',dict(processes=operation_rows,A_metrics=a['metrics'],B_metrics=b['metrics'] if b else None,primary_aggregate='actual process total before statistics,not sum of component medians'))
    keys={'QUERY_QUALITY.json':('false_negatives','false_positives'),'OWNERSHIP_QUALITY.json':('ownership_errors',),'FINAL_STATE.json':('final_state_errors',)}
    for name,fields in keys.items():
        records=[]
        for p in processes:
            for part in ('measured','warmup'):
                c=p[part];records.append(dict(stage=p['stage'],label=p['label'],part=part,queries=c['queries'],updates=c['updates'],**{k:c[k] for k in fields},final_vector_bytes=c['final_proof']['all_vector_bytes_bitwise_compared']))
        save(out/'correctness'/name,dict(passed=True,scope=f'all{len(starts)} successful processes,formal and warmup;fixture-only sanitizers',records=records,update_method='actual local transition witnesses+full independent map induction;not direct full actual-map export after every mutation',final_method='actual full forward/reverse maps+direct byte comparison of every final GPU vector'))
    probes=read(w/'qualification/D1_A_dry.checked.json')['probes'];assert probes['passed']
    by=defaultdict(list)
    for r in probes['rows']:by[r['step']].append(r)
    base={r['qid']:r for r in by[-1]};snapshots=[]
    for step,rows in by.items():
        assert len(rows)==32 and {r['qid'] for r in rows}==set(base)
        snapshots.append(dict(step=step,queries=32,live=rows[0]['live'],mean_percent=np.mean([r['percent'] for r in rows],axis=0).tolist(),max_abs_percentage_point_change_vs_initial=np.max([np.abs(np.array(r['percent'])-base[r['qid']]['percent']) for r in rows],axis=0).tolist()))
    save(out/'updates/STAGE_ROBUSTNESS.json',dict(A=dict(passed=True,rows=probes['rows'],snapshots=snapshots,query_pool_size=32,diagnostic_only=True,scope='exact initial/20I20D/40I40D/final;descriptive stability,no invented threshold'),B=dict(status='NOT_EXECUTED',reason='A not GO') if b is None else dict(status='see B_probes receipts'),no_dynamic_DRAM_profile=True))
    save(out/'updates/UPDATE_ROBUSTNESS.json',dict(A={k:a['metrics'][k] for k in ('insert_ms','delete_ms')},B=b,update_paths_unchanged=True,no_rebuilds=True,unlimited_updates_or_capacity_growth='NOT_TESTED'))
    persistent=[];temporary=[]
    for m in memory:
        meta=m['meta'];persistent.append(dict(stage=m['stage'],label=m['label'],capacity=meta['capacity'],GPU_vector_bytes=meta['vector_storage_bytes'],GPU_native_norm_bytes=meta['norm_storage_bytes'],CPU_forward_map_capacity_bytes=meta['forward_map_capacity_bytes'],CPU_reverse_map_capacity_bytes=meta['reverse_map_capacity_bytes'],CPU_retained_input_vector_bytes=meta['vector_storage_bytes']))
        temporary.append(dict(stage=m['stage'],label=m['label'],GPU_owned_query_bytes=meta['query_owned_bytes'],GPU_progressive_state_bytes=meta['progressive_state_bytes'],GPU_CUB_reserved_bytes=meta['cub_scratch_bytes'],device_used_built_bytes=meta['device_used_built_bytes'],device_used_after_events_bytes=meta['device_used_after_events_bytes'],device_used_after_service_release_bytes=meta['device_used_final_bytes'],sampled_device_peak_MiB=m['sampled_device_peak_MiB']))
    for r in range(1,7):
        aa=[p for p in persistent if p['stage']=='A' and p['label'].startswith(f'r{r}_')];assert len(aa)==2 and {k:v for k,v in aa[0].items() if k!='label'}=={k:v for k,v in aa[1].items() if k!='label'}
    save(out/'memory/PERSISTENT_MEMORY.json',dict(records=persistent,D0_D1_identical=True,D1_extra_ND_representation=False,map_space='Host CPU',host_input_retention='both systems inherit one preloaded CPU vector array;excluded final validation briefly makes another CPU replay copy',capacity_growth='not tested'))
    save(out/'memory/TEMP_MEMORY.json',dict(records=temporary,state_not_index=True,reusable_workspace_reserved_before_service_ready=True,device_used_scope='CUDA mem-info;includes context/library reservations,not just index storage',peak='200ms sampled device-wide high-water mark,not exact ownership/peak proof',retained_client_and_audit_container_teardown='not timed',CPU_RSS_peak='not measured'))
    for p in (w/'inputs').glob('*'):
        if p.suffix in ('.logical','.json'):shutil.copyfile(p,out/'inputs'/p.name)
    shutil.copyfile(w/'pool32.txt',out/'inputs/pool32.txt')
    static=read(w/'build/STATIC.json');save(out/'evidence/STATIC.json',static)
    resources={}
    for mode in ('D0','D1'):
        res={};text=(w/'build'/(mode+'.resources.txt')).read_text()
        for match in re.finditer(r' Function (\S+):\n\s*([^\n]+)',text):
            selected=('squared_l2_b1',) if mode=='D0' else ('progressive_stage','progressive_fields')
            if any(k in match[1] for k in selected):res[match[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',match[2])}
        assert len(res)==(1 if mode=='D0' else 5);resources[mode]=res
    save(out/'evidence/KERNEL_RESOURCES.json',dict(scope='static only;not runtime duration',modes=resources))
    recovery=reg.get('recovery',{})
    save(out/'evidence/INPUT_IDENTITY.json',dict(base_commit=reg['base_commit'],contract_sha256=reg['contract_sha256'],data_sha256=reg['data_sha256'],radius=reg['radius'],binaries=ready['binaries'],libraries=ready['libraries'],static_libraries={Path(p).name:h for p,h in reg['static_libraries'].items()},measurement_sources=reg['sources'],compiled_sources=recovery.get('compile_sources',reg['sources']),input_hashes=ready['inputs'],stage_prefix_references={Path(p).name:h for p,h in reg['stage_reference_hashes'].items()},registration_sha256=sha(w/'REGISTERED.json'),ready_sha256=sha(w/'READY.json'),analysis_freeze_sha256=sha(freeze),curator_sha256=sha(HERE/'curate.py')))
    receipt=dict(recovery_used=bool(recovery),prior_failed_guard_starts=prior,no_passed_sample_repeated=True,quality_timing_and_input_contract_unchanged=True)
    if recovery:receipt.update(human_approved=True,scope='small fixture empty probe-pool argument only',prior_CUDA_initializations=0,**{k:recovery[k] for k in ('prior_failure_sha256','prior_ledger_sha256','prior_registration_sha256','changed_non_GPU_sources','unchanged_binaries')})
    save(out/'evidence/RECOVERY.json',receipt)
    save(out/'evidence/EXECUTION_CLOSURE.json',dict(complete_at_declared_stop=True,A_decision=a['decision'],successful_processes=len(starts),prior_failed_guard_starts=prior,total_top_level_starts=len(starts)+prior,budget_cap=recovery.get('max_total_starts',29),stage_counts=dict(Counter(s['stage'] for s in starts)),unexecuted_conditional_jobs=jobs('B')+jobs('B_probes') if b is None else [],all_isolation_receipts_valid=True,no_query_or_threshold_adjustment=True,full_dynamic_admission=bool(a['decision']=='GO_DYNAMIC_PROGRESSIVE' and b and b['decision']=='PASS_UPDATE_HEAVY'),thesis_admission=False,new_start_ledger_sha256=sha(w/'STARTS.jsonl'),stage_result_sha256={s:sha(w/s/'RESULTS.json') for s in stages}))
    raw={str(p.relative_to(w)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in w.rglob('*') if p.is_file() and p.name!='campaign.lock'}
    save(out/'evidence/RAW_IDENTITY.json',dict(scope='full private data/cache/build/output/log identities;scalar curation only',files=raw))
    print('CURATED',a['decision'],'starts',len(starts)+prior,'B',bool(b),flush=True)
def csvrows_no_header(p):
    with Path(p).open() as f:return list(csv.reader(f))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--analysis-freeze',type=Path,required=True);a=p.parse_args();curate(a.work.resolve(),a.out.resolve(),a.analysis_freeze.resolve())
