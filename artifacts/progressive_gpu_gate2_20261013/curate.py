"""Revalidate private evidence and export only complete scalar/hash records."""
import argparse,csv,math,re
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from campaign import prepared,previous,static_gate,STAGES,table
from prepare import HERE,read,save,sha
from analyze import summarize,classify

KEYS=('gpu__time_duration.avg','dram__bytes.sum','dram__bytes_op_read.sum','dram__bytes_op_write.sum','lts__t_bytes.sum','sm__throughput.avg.pct_of_peak_sustained_elapsed','sm__warps_active.avg.pct_of_peak_sustained_active')
def phase(name,mode,current):
    if mode=='B1':
        if 'squared_l2_b1' in name:return 'scan',0
        if 'flags_kernel' in name:return 'flags',0
        if 'fields_kernel' in name:return 'fields',0
    else:
        match=re.search(r'progressive_stage<\s*(\d+),\s*(\d+)',name)
        if match:return 'scan',(128,256,512,960).index(int(match[2]))+1
        if 'progressive_fields' in name:return 'fields',4
    assert 'cub::' in name or 'CUB_' in name,('unaccounted captured kernel',name)
    return 'compact',current

def traffic(path,mode,qids):
    with path.open() as f:raw=list(csv.reader(f))
    assert len(raw)>2 and 'Kernel Name' in raw[0]
    headers,unitrow=raw[:2];units=dict(zip(headers,unitrow))
    duration_factors={'ns':1.,'nsecond':1.,'us':1e3,'usecond':1e3,'ms':1e6,'msecond':1e6,'s':1e9,'second':1e9}
    assert units[KEYS[0]] in duration_factors
    for k in KEYS[1:5]:assert units[k]=='byte',(k,units[k])
    rows=[];groups=[];current=[];active=0
    for rawrow in raw[2:]:
        assert len(rawrow)==len(headers);r=dict(zip(headers,rawrow));name=r['Kernel Name']
        kind,stage=phase(name,mode,active)
        if kind=='scan' and stage==(0 if mode=='B1' else 1):
            if current:groups.append(current)
            current=[]
        assert current or (kind=='scan' and stage==(0 if mode=='B1' else 1))
        active=stage
        metrics={k:float(r[k].replace(',','')) for k in KEYS}
        metrics[KEYS[0]]*=duration_factors[units[KEYS[0]]]
        assert all(math.isfinite(v) and v>=0 for v in metrics.values())
        assert abs(metrics['dram__bytes.sum']-metrics['dram__bytes_op_read.sum']-metrics['dram__bytes_op_write.sum'])<=max(1,metrics['dram__bytes.sum']*1e-6)
        row=dict(capture_ID=r['ID'],kernel=name,kind=kind,stage=stage,metrics=metrics)
        current.append(row);rows.append(row)
    groups.append(current);assert len(groups)==32
    queryrecords=[];families=defaultdict(list)
    for q,group in zip(qids,groups):
        assert [r['stage'] for r in group if r['kind']=='scan']==([0] if mode=='B1' else [1,2,3,4])
        assert sum(r['kind']=='fields' for r in group)==1
        if mode=='B1':assert sum(r['kind']=='flags' for r in group)==1
        for s in ([0] if mode=='B1' else [1,2,3,4]):assert any(r['kind']=='compact' and r['stage']==s for r in group)
        sums={k:sum(r['metrics'][k] for r in group) for k in KEYS[:5]}
        duration=sums['gpu__time_duration.avg'];assert duration>0
        weights={k:sum(r['metrics'][k]*r['metrics'][KEYS[0]] for r in group)/duration for k in KEYS[5:]}
        queryrecords.append(dict(qid=q,kernels=len(group),kernel_kind_counts=dict(Counter(r['kind'] for r in group)),kernel_ms=duration/1e6,DRAM_bytes=sums[KEYS[1]],DRAM_read_bytes=sums[KEYS[2]],DRAM_write_bytes=sums[KEYS[3]],L2_bytes=sums[KEYS[4]],duration_weighted_percent=weights))
        for r in group:families[(r['kind'],r['stage'])].append(r)
    totals={k:float(np.mean([q[k] for q in queryrecords])) for k in ('DRAM_bytes','DRAM_read_bytes','DRAM_write_bytes','L2_bytes','kernel_ms')}
    familyrecords=[]
    for (kind,stage),group in sorted(families.items()):
        familyrecords.append(dict(kind=kind,stage=stage,launches=len(group),kernel_names=sorted(set(r['kernel'] for r in group)),mean_DRAM_bytes_per_query=sum(r['metrics'][KEYS[1]] for r in group)/32,mean_DRAM_read_bytes_per_query=sum(r['metrics'][KEYS[2]] for r in group)/32,mean_DRAM_write_bytes_per_query=sum(r['metrics'][KEYS[3]] for r in group)/32,mean_L2_bytes_per_query=sum(r['metrics'][KEYS[4]] for r in group)/32,mean_kernel_ms_per_query=sum(r['metrics'][KEYS[0]] for r in group)/32/1e6))
    return dict(mode=mode,diagnostic_only=True,queries=32,all_kernels_included=True,launches=len(rows),raw_CSV_sha256=sha(path),raw_units=units,normalized_metric_units={**{k:units[k] for k in KEYS},KEYS[0]:'ns'},means=totals,DRAM_query_distribution=dict(min=min(q['DRAM_bytes'] for q in queryrecords),p90=float(np.quantile([q['DRAM_bytes'] for q in queryrecords],.9)),max=max(q['DRAM_bytes'] for q in queryrecords)),queries_detail=queryrecords,families=familyrecords,captured_kernels=rows)

def stage_breakdown(prefix):
    stage=table(str(prefix)+'.stages.csv');out=table(str(prefix)+'.output.csv')
    inv=table(str(prefix)+'.invocations.csv');assert len(stage)==160 and len(out)==len(inv)==40
    records=[]
    for i in range(8,40):
        group=stage[i*4:i*4+4];output=out[i];ack=float(inv[i]['ack_ms'])
        assert all(int(r['invocation'])==i for r in group) and int(output['invocation'])==i
        stages=[dict(stage=int(r['stage']),input=int(r['input']),output=int(r['output']),scan_ms=float(r['scan_ms']),compact_ms=float(r['compact_ms']),host_stage_ms=float(r['host_stage_ms'])) for r in group]
        scan=sum(r['scan_ms'] for r in stages);compact=sum(r['compact_ms'] for r in stages)
        assert all(r['scan_ms']>0 and r['compact_ms']>0 and r['host_stage_ms']+1e-5>=r['scan_ms']+r['compact_ms'] for r in stages)
        fields=float(output['fields_ms']);host_output=float(output['host_output_ms'])
        assert host_output+1e-5>=fields
        assert ack+1e-5>=scan+compact+fields
        records.append(dict(query_index=i-8,ack_ms=ack,stages=stages,scan_ms=scan,compact_ms=compact,fields_ms=fields,host_output_ms=host_output,unattributed_host_minus_events_ms=ack-scan-compact-fields))
    means={k:float(np.mean([r[k] for r in records])) for k in ('ack_ms','scan_ms','compact_ms','fields_ms','host_output_ms','unattributed_host_minus_events_ms')}
    return dict(scope='Independent event-enabled diagnostic, not primary ACK; residual is not automatically control cost',queries=records,means=means,isolated_compaction_share=means['compact_ms']/means['ack_ms'])

def curate(work,out,analysis_freeze):
    assert not out.exists();reg=prepared(work);static_gate(work,reg)
    frozen=read(analysis_freeze)
    for name,h in frozen.items():assert sha(HERE/name)==h,'analysis-source identity drift'
    for stage in STAGES:previous(work,stage)
    starts=[readline for readline in (work/'STARTS.jsonl').read_text().splitlines()]
    import json
    starts=[json.loads(s) for s in starts]
    assert len(starts) in (32,33) and [s['start'] for s in starts]==list(range(1,len(starts)+1))
    recovery=reg['recovery'];prior_starts=recovery['prior_starts'] if recovery else 0
    assert [s['global_start'] for s in starts]==list(range(prior_starts+1,prior_starts+len(starts)+1))
    expected=[(stage,job['label']) for stage in STAGES for job in read(work/stage/'REGISTERED.json')['jobs']]
    assert [(s['stage'],s['label']) for s in starts]==expected
    for s in starts:assert sha(work/s['stage']/(s['label']+'.command.json'))==s['command_sha256']
    out.mkdir();receipts=[];quality=[];public_quality_keys=('mode','N','queries','measured_queries','all_complete_members','false_negatives','false_positives','max_ordered_FP64_field_error','same_campaign_B1_score_error','checkpoint_complete_IDs_checked','sanitizer_summary_zero','iterations','stream_slots','empty_answers','exact_boundary_pairs','stage_rejects','subnormal_cases')
    for stage in STAGES:
        for row in read(work/stage/'RESULTS.json')['rows']:
            checked=read(work/stage/(row['label']+'.checked.json'))
            quality.append(dict(stage=stage,label=row['label'],passed=True,**{k:checked[k] for k in public_quality_keys if k in checked}))
            receipts.append(dict(stage=stage,label=row['label'],guard_sha256=row['guard_sha256'],guard_files=row['guard_hashes'],checked_sha256=row['checked_sha256'],reports=row['report_hashes'],outputs=checked.get('output_hashes',{})))
    save(out/'QUALITY.json',dict(passed=True,records=quality,sanitizer_scope='Synthetic100 iterations/two independent streams and bounded4096 target;no full-N sanitizer claim',Graph='not used',all_membership_and_fields_verified=True))
    save(out/'QUALITY_RECEIPTS.json',receipts)
    processes=[];samples=[]
    for r in range(1,7):
        values={}
        for mode in ('B0','B1','P1'):
            c=read(work/'primary'/f'r{r}_{mode}.checked.json');values[mode]=c['mean_query_ms']
            samples.append(dict(round=r,mode=mode,order='forward' if r%2 else 'reverse',mean_query_ms=c['mean_query_ms'],query_ACK_ms=c['query_ack_ms'],pass_ms=c['pass_ms'],meta=c['meta']))
        processes.append(values)
    timing=dict(scope='Host request ready -> complete Host output ready',**summarize(processes),processes=samples)
    save(out/'PRIMARY_TIMING.json',timing)
    p=work/'qualification/target_P1.checked.json';qual=read(p)
    save(out/'STAGE_COUNTS.json',dict(checkpoints=(128,256,512,960),complete_checkpoint_IDs_checked=True,qids=reg['q32'],warmup8_counts=qual['checkpoint_counts'][:8],measured32_counts=qual['checkpoint_counts'][8:],replay_coordinates=qual['replay_coordinates'][8:],raw_checked_sha256=sha(p)))
    trafficrecords={mode:traffic(work/'ncu/reports'/f'{mode}.base.csv',mode,reg['q32']) for mode in ('B1','P1')}
    dramfraction=trafficrecords['P1']['means']['DRAM_bytes']/trafficrecords['B1']['means']['DRAM_bytes']
    save(out/'DRAM_ACCOUNTING.json',dict(scope='Independent all32-query/all-kernel NCU diagnostics;mean decimal bytes/query',modes=trafficrecords,dram_fraction=dramfraction,dram_reduction=1-dramfraction,latency_reduction=1-timing['latency_ratio'],conversion_ratio=(1-timing['latency_ratio'])/(1-dramfraction)))
    breakdown=stage_breakdown(work/'breakdown/outputs/P1_events');save(out/'STAGE_BREAKDOWN.json',breakdown)
    # Event-measured selection is a directly isolated component. An unexplained
    # host-minus-events residual is retained but never relabeled as control.
    control=breakdown['isolated_compaction_share']
    label=classify(trafficrecords['P1']['means']['DRAM_bytes'],timing['latency_ratio'],timing['paired_95_CI'][1],control,True)
    save(out/'DECISION.json',dict(label=label,strong_GO=label=='GO_PROGRESSIVE_GPU' and trafficrecords['P1']['means']['DRAM_bytes']<=1.3e9 and timing['latency_ratio']<=.65,quality=True,DRAM_mean_bytes=trafficrecords['P1']['means']['DRAM_bytes'],latency_ratio=timing['latency_ratio'],paired_CI_upper=timing['paired_95_CI'][1],isolated_control_share=control,control_denominator='Event-enabled diagnostic complete ACK;only measured CUB selection admitted here',persistent_motivation_only=control>=.25,no_production_or_dynamic_admission=True))
    save(out/'STATIC.json',read(work/'build/STATIC.json'))
    repair=read(work/'HOST_ONLY_REPAIR_PROOF.json') if recovery else dict(repair_not_applicable=True,reason='Clean fresh campaign without prior failure')
    if recovery:assert repair['passed'] and repair['no_GPU_starts'] and repair['all_5_candidate_functions_normalized_sass_equal'] and repair['CUDA_headers_equal'] and repair['keeper_selected_sass_equal']
    save(out/'HOST_ONLY_REPAIR_PROOF.json',repair)
    resources={}
    text=(work/'build/candidate.resources.txt').read_text()
    for match in re.finditer(r' Function (\S+):\n\s*([^\n]+)',text):
        if 'progressive_stage' in match[1] or 'progressive_fields' in match[1]:
            resources[match[1]]={k:int(v) for k,v in re.findall(r'(REG|STACK|SHARED|LOCAL):(\d+)',match[2])}
    assert len(resources)==5
    save(out/'CUSTOM_KERNEL_RESOURCES.json',dict(no_runtime_performance_claim=True,functions=resources,raw_resources_sha256=sha(work/'build/candidate.resources.txt')))
    nsys_jobs=read(work/'nsys/REGISTERED.json')['jobs']
    if not nsys_jobs:assert timing['latency_ratio']<=.80 and timing['paired_95_CI'][1]<.90
    save(out/'NSYS_SCOPE.json',dict(performed=bool(nsys_jobs),conditional_skip=not bool(nsys_jobs),skip_rule='No trace required when primary ratio<=.80 and paired CIupper<.90',raw_result_sha256=sha(work/'nsys/RESULTS.json')))
    save(out/'INPUT_IDENTITY.json',dict(data_sha256=reg['data_sha256'],reference_hashes=reg['reference_hashes'],query_ids=reg['q32'],keeper_sha256=reg['keeper_sha256'],readonly_sha256=reg['readonly_sha256'],candidate_binaries=read(work/'READY.json')['binaries'],libraries=reg['libraries'],measurement_sources=reg['source_hashes'],contract_sha256=reg['contract_sha256'],registration_sha256=sha(work/'REGISTERED.json'),ready_sha256=sha(work/'READY.json'),dependency_preflight_sha256=sha(work/'DEPENDENCY_PREFLIGHT.json'),analysis_freeze_sha256=sha(analysis_freeze),analysis_sources=frozen,curator_sha256=sha(HERE/'curate.py'),placement='Privately pinned single initially empty card and matching NUMA;no setting changes'))
    raw={str(p.relative_to(work)):dict(sha256=sha(p),bytes=p.stat().st_size) for p in work.rglob('*') if p.is_file() and p.name!='campaign.lock'}
    save(out/'RAW_IDENTITY.json',dict(scope='Private raw payloads/reports/source/build/log archive;hash identities only',files=raw))
    save(out/'EXECUTION_CLOSURE.json',dict(complete=True,new_starts=len(starts),prior_failed_guard_starts=prior_starts,prior_CUDA_starts=0,total_starts=len(starts)+prior_starts,budget_cap=recovery['max_total_starts'] if recovery else 33,stage_counts=dict(Counter(s['stage'] for s in starts)),prior_failure_sha256=recovery['prior_failure_sha256'] if recovery else None,prior_start_ledger_sha256=recovery['prior_ledger_sha256'] if recovery else None,new_start_ledger_sha256=sha(work/'STARTS.jsonl'),stage_results_sha256={s:sha(work/s/'RESULTS.json') for s in STAGES},approved_recovery=bool(recovery),no_passed_sample_repeated=True,all_two_sided_isolation_valid=True,no_thresholds_or_queries_relaxed=True))
    print('CURATED',label,'DRAM',trafficrecords['P1']['means']['DRAM_bytes'],'latency ratio',timing['latency_ratio'],'starts',len(starts)+prior_starts,flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--analysis-freeze',type=Path,required=True);a=p.parse_args();curate(a.work.resolve(),a.out.resolve(),a.analysis_freeze.resolve())
