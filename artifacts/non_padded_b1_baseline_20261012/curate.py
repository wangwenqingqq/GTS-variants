"""Reverify raw campaign artifacts; export scalar evidence without deployment paths."""
import argparse,csv,json
from pathlib import Path
from campaign import prepared,previous_stage,STAGES
from prepare import HERE,read,save,sha
from dynamic import hashes
from analyze import metric_record

def curate(work,analysis,out):
    reg=prepared(work)
    for stage in STAGES:previous_stage(work,stage)
    starts=[json.loads(s) for s in (work/'STARTS.jsonl').read_text().splitlines()]
    assert [s['start'] for s in starts]==list(range(1,32))
    assert [s['stage'] for s in starts]==['qualification']*8+['primary']*18+['ncu']*3+['dynamic','dynamic_recovery']
    out.mkdir(exist_ok=False)
    receipts=[];quality=[]
    for stage in STAGES:
        for row in read(work/stage/'RESULTS.json')['rows']:
            q=read(work/stage/(row['label']+'.checked.json'));g=read(work/stage/'guards'/row['label']/'receipt.json')
            assert g['runtime_valid'] and q['passed']
            receipt=dict(stage=stage,label=row['label'],passed=True,guard_sha256=row['guard_sha256'],
                checked_sha256=row['checked_sha256'],command_record_sha256=sha(work/stage/(row['label']+'.command.json')),
                reports=row['report_hashes'],outputs=q.get('output_hashes',{}))
            receipts.append(receipt)
            quality.append(dict(stage=stage,label=row['label'],**{k:q[k] for k in (
                'mode','N','queries','false_negatives','false_positives','max_ordered_FP64_field_error',
                'max_native_scale_error','native_payload_bits_equal','min_ordered_boundary_margin','counts') if k in q}))
    for mode,name in (('N0','NATIVE'),('N1','NON_PADDED'),('R0','READ_ONLY')):
        metrics=metric_record(work/'ncu/reports'/f'{mode}.base.csv')
        assert metrics==read(analysis/(mode+'_METRICS.json'))
        if mode=='R0':
            metrics['work_inflation']=None;metrics['useful_search_proxy_applicable']=False
            metrics['role']='structural checksum streaming reference, not distance or search'
        metrics['raw_CSV_sha256']=sha(work/'ncu/reports'/f'{mode}.base.csv')
        save(out/(name+'_METRICS.json'),metrics)
    timing=read(analysis/'BASELINE_TIMING.json');assert timing['new_GPU_starts']==29
    save(out/'BASELINE_TIMING.json',timing)
    save(out/'QUALITY.json',dict(passed=True,qualification=quality[:8],all_static_processes=quality,
        fixtures=read(work/'qualification/fixtures.checked.json'),
        sanitizers={t:read(work/'qualification'/f'fixtures_{t}.checked.json') for t in ('memcheck','racecheck','synccheck')},
        membership_gate='exact complete IDs/order;0 FN/FP against ordered-FP64, all40 queries/run',
        field_gate='squared-score scale tolerance5e-5; N1 reduction-order bit differences disclosed',
        sanitizer_scope='100-repeat synthetic fixtures in same candidate binary; not full-N1M sanitizer',Graph='not used or qualified'))
    save(out/'QUALITY_RECEIPTS.json',receipts)
    save(out/'INPUT_IDENTITY.json',dict(data_sha256=reg['data_sha256'],original_queries=reg['q32'],reference_hashes=reg['reference_hashes'],
        native_binary_sha256=reg['native_sha256'],readonly_binary_sha256=reg['readonly_sha256'],
        candidate_binary_sha256=read(work/'build/BUILD.json')['binary_sha256'],exact_shared_libraries=reg['libraries'],
        contract_sha256=reg['contract_sha256'],frozen_measurement_sources=reg['source_hashes'],
        analysis_freeze=read(work/'ANALYSIS_FROZEN.json'),analysis_revision2_sha256=sha(HERE/'analyze.py'),
        private_registration_sha256=sha(work/'REGISTERED.json'),private_ready_sha256=sha(work/'READY.json'),
        private_build_sha256=sha(work/'build/BUILD.json'),placement='same privately pinned physical GPU and NUMA, no settings changed'))
    p=work/'dynamic';r=p/'recovery';dr=read(p/'REGISTERED.json');audit=read(r/'AUDIT.json');recovered=read(r/'RESULTS.json')
    assert read(p/'RESULTS.json')['complete'] is False and read(p/'RESULTS.json')['rows'][0]['status']=='failed'
    assert recovered['complete'] and recovered['passed'] and audit['source_hashes']==dr['source_hashes']==hashes()
    assert recovered['registration_sha256']==sha(r/'REGISTERED.json') and recovered['checked_sha256']==sha(r/'strengthened.checked.json')
    assert recovered['old_offline_checked_sha256']==audit['old_offline_checked_sha256']==sha(r/'old.offline_checked.json')
    assert audit['original_results_sha256']==sha(p/'RESULTS.json') and audit['original_register_sha256']==sha(p/'REGISTERED.json')
    for path,h in {**dr['input_hashes'],**dr['generated_sources'],**audit['stopped_old_output_hashes']}.items():assert sha(path)==h
    for v in audit['reference_conversion'].values():
        for path,h in v['hashes'].items():assert sha(path)==h
    dynamic={}
    for mode,prefix,checked,guard in (
        ('old',p/'outputs/old',r/'old.offline_checked.json',p/'guards/old/receipt.json'),
        ('strengthened',r/'outputs/strengthened',r/'strengthened.checked.json',r/'guards/strengthened/receipt.json')):
        q=read(checked);assert q['passed'] and q['measured']['passed'] and q['warmup']['passed'] and read(guard)['runtime_valid']
        for path,h in q['output_hashes'].items():assert sha(path)==h
        assert q['measured']['queries']==256 and q['warmup']['queries']==8
        dynamic[mode]=dict(meta=q['meta'],ops=q['ops'],measured_quality=q['measured'],warmup_quality=q['warmup'],
            checked_sha256=sha(checked),guard_sha256=sha(guard),output_hashes={Path(path).name:h for path,h in q['output_hashes'].items()})
    old,new=(dynamic[k] for k in ('old','strengthened'))
    summary=dict(modes=dynamic,event_counts=dr['event_counts'],capacity=dr['capacity'],max_live=dr['max_live'],
        scope=dr['scope'],unchanged=dr['unchanged'],old_GPU_not_rerun=True,original_failure_preserved=True,
        reference_correction=audit['correction'],reference_ownership_issue=audit['issue'],
        static_device_kernel_unchanged=True,host_ceiling_extended_only=True,
        native_binary_sha256=dr['native_sha256'],candidate_binary_sha256=read(p/'build/BUILD.json')['binary_sha256'],
        libraries=dr['libraries'],frozen_dynamic_sources=dr['source_hashes'],recovery_source_sha256=sha(HERE/'recover.py'),
        registration_sha256=sha(p/'REGISTERED.json'),original_failure_sha256=sha(p/'RESULTS.json'),
        recovery_registration_sha256=sha(r/'REGISTERED.json'),reference_audit_sha256=sha(r/'AUDIT.json'),
        recovery_results_sha256=sha(r/'RESULTS.json'),trace_binding_sha256=sha(dr['trace']+'.binding.json'),
        inherited_trace_speedup=old['meta']['trace_ms']/new['meta']['trace_ms'],
        inherited_trace_reduction=1-new['meta']['trace_ms']/old['meta']['trace_ms'],
        confidence='one forward pair only; no CI, sustained or generalized workflow claim')
    save(out/'DYNAMIC_INTEGRATION.json',summary)
    save(out/'EXECUTION_CLOSURE.json',dict(static_complete=True,dynamic_complete_after_authorized_recovery=True,
        top_level_starts=31,budget_cap=31,stage_counts={s:sum(v['stage']==s for v in starts) for s in ('qualification','primary','ncu','dynamic','dynamic_recovery')},
        GPU_runtime_failures=0,original_postrun_quality_failures=1,old_offline_reference_corrected_pass=True,
        GPU_retries=0,all_two_sided_isolation_valid=True,all_quality_output_hashes_reverified=True,
        raw_STARTS_sha256=sha(work/'STARTS.jsonl'),raw_stage_results_sha256={s:sha(work/s/'RESULTS.json') for s in STAGES}))
    save(out/'RAW_EVIDENCE_IDENTITY.json',dict(privacy='All full vectors, complete payloads, placement, build logs, SASS and vendor reports stay outside Git.',
        work_files={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file() and p.name!='campaign.lock'},
        scope='hash index, not raw content; no assertion that raw vendor binaries may be redistributed'))
    print('VERIFIED:29 static starts + stopped old output + authorized remaining integration process;31/31',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('work','analysis','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();curate(a.work.resolve(),a.analysis.resolve(),a.out.resolve())
