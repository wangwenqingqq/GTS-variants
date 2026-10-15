"""Revalidate the closed GPU campaign and export scalars/hashes, never placement or raw data."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import collections
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
from gpu_prepare import HERE,load,save,sha
from gpu_campaign import legacy,schedule,quality
from analyze import summarize,classify


def curate(w,out):
    reg=load(w/'REGISTERED.json');ready=load(w/'READY.json');c=load(HERE/'GPU_CONTRACT.json')
    repo=Path(reg['repo']);assert ready['passed'] and ready['registration_sha256']==sha(w/'REGISTERED.json')
    assert all(sha(Path(n))==h for n,h in reg['input_sources'].items())
    assert all(sha(Path(n))==h for n,h in reg['generated_sources'].items())
    assert all(sha(repo/n)==h for n,h in c['parents'].items())
    assert all(sha(w/'build'/n)==h for n,h in ready['binaries'].items())
    assert sha(reg['data'])==c['data_sha256']
    assert all(sha(Path(reg['reference'])/n)==h for n,h in reg['reference_hashes'].items())
    assert sha(Path(reg['cpu'])/'raw/global_means.f32')==c['global_means_sha256']
    frozen=load(w.parent/'ANALYSIS_FREEZE.json')
    assert frozen['before_primary_timing'] and frozen['analyzer_sha256']==sha(HERE/'analyze.py')
    assert frozen['contract_sha256']==sha(HERE/'GPU_CONTRACT.json')
    static=load(w/'STATIC.json');assert static['passed'] and static['keeper_device_functions_equal_parent']
    for mode,r in static['records'].items():
        assert r['binary_sha256']==ready['binaries'][mode]
        assert sha(w/'build'/f'{mode}.sass.txt')==r['sass_dump_sha256']
        assert sha(w/'build'/f'{mode}.resources.txt')==r['resource_sha256']
    base=legacy(repo,'campaign');stats_helpers=legacy(repo,'curate')
    receipts=[];checks=[];starts=[]
    for stage in ('qualification','primary','ncu','breakdown'):
        result=load(w/stage/'RESULTS.json');registration=load(w/stage/'REGISTERED.json');jobs=schedule(stage)
        assert result['complete'] and registration['jobs']==jobs and len(result['rows'])==len(jobs)
        assert registration['contract_sha256']==sha(HERE/'GPU_CONTRACT.json')
        if stage=='ncu':assert registration['executor_sha256']==sha(HERE/'gpu_campaign_ncu.py')
        for row,job in zip(result['rows'],jobs):
            assert row['status']=='passed' and all(row[k]==v for k,v in job.items())
            label=job['label'];p=w/stage;g=p/'guards'/label;receipt=load(g/'receipt.json')
            assert sha(g/'receipt.json')==row['guard_sha256']
            assert all(sha(g/n)==h for n,h in row['guard_files'].items())
            assert all(sha(p/'reports'/n)==h for n,h in row['reports'].items())
            assert receipt['runtime_valid'] and receipt['exit_code']==0 and receipt['stop_reason'] is None
            assert receipt['observer']=='two-sided-starttime-v1' and receipt['gpu']==reg['gpu']
            cmd=load(p/(label+'.command.json'))['command']
            assert load(g/'command.json')==receipt['command']==['numactl',f"--cpunodebind={reg['numa']}",f"--membind={reg['numa']}",*cmd]
            assert receipt['binary_sha256']==sha(Path(cmd[0]))
            for n in ('before','after'):assert not load(g/(n+'.json'))['apps']
            for snap in load(g/'checks.json'):assert not snap['foreign']
            original=load(p/(label+'.checked.json'));assert sha(p/(label+'.checked.json'))==row['checked_sha256']
            if job.get('kind')!='fixtures':
                checked=quality(p/'outputs'/label,job,w,reg,base)
                for k,v in checked.items():assert original[k]==v,('quality drift',stage,label,k)
            else:
                assert original['passed'] and original['iterations']==100 and original['stream_slots']==2
                assert all(original['stage_rejects']) and original['subnormal_cases']
            if job.get('tool') in ('memcheck','racecheck','synccheck'):
                logs=(g/'stdout.log').read_text()+(g/'stderr.log').read_text()
                assert 'ERROR SUMMARY: 0 errors' in logs or 'RACECHECK SUMMARY: 0 hazards' in logs
                assert original['sanitizer_summary_zero']
            allowed=('passed','mode','N','queries','measured_queries','all_complete_members','false_negatives','false_positives',
                'max_ordered_FP64_field_error','complete_checkpoint_IDs_checked','internal_ordered_FP64_scores_checked',
                'internal_FP64_bit_mismatches','sanitizer_summary_zero','iterations','stream_slots','empty_answers',
                'exact_boundary_pairs','stage_rejects','subnormal_cases')
            checks.append({'stage':stage,'label':label,**{k:v for k,v in original.items() if k in allowed}})
            receipts.append({'stage':stage,'label':label,'guard_sha256':row['guard_sha256'],'guard_files':row['guard_files'],
                'checked_sha256':row['checked_sha256'],'reports':row['reports'],'outputs':original.get('output_hashes',{})})
            starts.append((stage,label,sha(p/(label+'.command.json'))))
    ledger=[json.loads(s) for s in (w/'STARTS.jsonl').read_text().splitlines()]
    assert len(ledger)==26 and [r['start'] for r in ledger]==list(range(1,27))
    assert [(r['stage'],r['label'],r['command_sha256']) for r in ledger]==starts
    out.mkdir(parents=True,exist_ok=False)
    pairs=[];processes=[]
    for i in range(1,7):
        pair={}
        for mode in ('keeper','candidate'):
            r=load(w/'primary'/f'r{i}_{mode}.checked.json');pair[mode]=r['mean_query_ms']
            processes.append({'round':i,'mode':mode,'order':'forward' if i%2 else 'reverse','mean_query_ms':r['mean_query_ms'],
                'query_ACK_ms':r['query_ack_ms'],'pass_ms':r['pass_ms'],'meta':r['meta']})
        pairs.append(pair)
    timing={'scope':c['measurement']['scope'],'included_ordering_and_parameter_upload':True,**summarize(pairs),'processes':processes}
    save(out/'TIMING.json',timing)
    traffic={mode:stats_helpers.traffic(w/'ncu/reports'/f'{mode}.base.csv','P1',reg['q32']) for mode in ('keeper','candidate')}
    for mode,r in traffic.items():r['mode']=mode;r.pop('raw_units',None)
    dram_ratio=traffic['candidate']['means']['DRAM_bytes']/traffic['keeper']['means']['DRAM_bytes']
    save(out/'DRAM.json',{'scope':c['measurement']['traffic'],'modes':traffic,'DRAM_ratio':dram_ratio,
        'DRAM_reduction':1-dram_ratio,'one_NCU_process_per_mode':True,'profiler_duration_not_primary_latency':True})
    breakdown={mode:stats_helpers.stage_breakdown(w/'breakdown/outputs'/mode) for mode in ('keeper','candidate')}
    with Path(str(w/'breakdown/outputs/candidate')+'.ordering.csv').open() as f:
        import csv
        ordering=list(csv.DictReader(f))
    assert len(ordering)==40 and [int(r['invocation']) for r in ordering]==list(range(40))
    costs={k:float(np.mean([float(r[k]) for r in ordering[8:]])) for k in ('priority_ms','order_submit_ms')}
    save(out/'OP_BREAKDOWN.json',{'scope':'independent event-enabled processes;not primary timings','modes':breakdown,
        'candidate_ordering_CPU_means_ms':costs,'ordering_records':ordering[8:],
        'order_submit_scope':'Host submission of two30-int H2D copies;not isolated device-copy duration',
        'residual_not_automatically_control':True})
    source_bytes=c['CPU_gate']['source_bytes'];s=timing
    final=classify(source_bytes,s['latency_ratio'],dram_ratio,s['wins'],s['paired_95_CI'][1],True)
    save(out/'DECISION.json',{'label':final,'strong_secondary':final=='PRIOR_ART_WINS' and s['latency_ratio']<=.8 and dram_ratio<=.8,
        'latency_ratio':s['latency_ratio'],'DRAM_ratio':dram_ratio,'paired_wins':s['wins'],'paired95CI':s['paired_95_CI'],
        'source_model_bytes':source_bytes,'complete_quality':True,'new_mechanism_or_dynamic_admitted':False})
    save(out/'QUALITY.json',{'passed':True,'records':checks,'complete_membership_fields_verified_all_target_processes':True,
        'internal_FP64_bits_checked_in_full_target_qualification':True,'sanitizer_scope':'synthetic100iterations/two streams and N4096 only;not fullN',
        'Graph':'not used/forbidden','sustained_scope':'six32-query independent passes;not production or dynamic'})
    save(out/'QUALITY_RECEIPTS.json',receipts)
    save(out/'STATIC.json',static)
    save(out/'INPUT_IDENTITY.json',{'data_sha256':c['data_sha256'],'qids':reg['q32'],'reference_hashes':reg['reference_hashes'],
        'global_means_sha256':c['global_means_sha256'],'cpu_contract_sha256':c['cpu_contract_sha256'],
        'cpu_results_sha256':c['cpu_results_sha256'],'binaries':ready['binaries'],'libraries':ready['libraries'],
        'registration_sha256':sha(w/'REGISTERED.json'),'ready_sha256':sha(w/'READY.json'),
        'generated_sources':{Path(n).name:h for n,h in reg['generated_sources'].items()},
        'source_inputs':{str(Path(n).relative_to(repo)):h for n,h in reg['input_sources'].items()},
        'dependency_sources':c['parents'],'controller_sources':{n:sha(HERE/n) for n in ('gpu_prepare.py','gpu_campaign.py','gpu_campaign_ncu.py')},'analyzer_sha256':frozen['analyzer_sha256'],'curator_sha256':sha(Path(__file__)),
        'placement':'one initially idle same-model card,matched NUMA;private placement;no settings changes'})
    save(out/'EXECUTION.json',{'complete':True,'GPU_starts':26,'prior_GPU_starts':0,'max_GPU_starts':26,'failed_or_replaced_GPU_samples':0,
        'stage_counts':dict(collections.Counter(r['stage'] for r in ledger)),'all_two_sided_isolation_valid':True,
        'prior_preparation_failure_retained':True,'CPU_population_reruns':0,'start_ledger_sha256':sha(w/'STARTS.jsonl'),
        'stage_results_sha256':{s:sha(w/s/'RESULTS.json') for s in ('qualification','primary','ncu','breakdown')},
        'NCU_route_preflight_sha256':sha(HERE/'NCU_ROUTE_PREFLIGHT.json'),'dependency_snapshot_and_host_routing_recovery':True,'no_CUDA_algorithm_or_binary_tuning':True})
    raw={str(p.relative_to(w)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in w.rglob('*') if p.is_file() and p.name!='campaign.lock'}
    save(out/'RAW_MANIFEST.json',{'private_only':True,'files':raw,'includes_dataset':False})
    print(json.dumps({'label':final,'strong_secondary':final=='PRIOR_ART_WINS' and s['latency_ratio']<=.8 and dram_ratio<=.8,
        'latency_ratio':s['latency_ratio'],'DRAM_ratio':dram_ratio,'GPU_starts':26}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();curate(a.work.resolve(),a.out.resolve())
