"""CPU-only exact ship-set and scalar recomputation; no CUDA or hidden raw data."""
import csv,hashlib,json,math,statistics,tempfile
from pathlib import Path
from analyze import analyze,classify,load,write

ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    manifest=load(ROOT/'PUBLIC_MANIFEST.json')
    actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='PUBLIC_MANIFEST.json'}
    assert actual==set(manifest['files'])
    for name,h in manifest['files'].items():assert sha(ROOT/name)==h,name
    identity=load(ROOT/'evidence/INPUT_IDENTITY.json');assert sha(ROOT/'CONTRACT.json')==identity['contract_sha256']
    for name,h in identity['frozen_measurement_sources'].items():assert sha(ROOT.parent.parent/name)==h,name
    assert sha(ROOT/'analyze.py')==identity['analysis_revision2_sha256']
    closure=load(ROOT/'evidence/EXECUTION_CLOSURE.json')
    assert closure['static_complete'] and closure['dynamic_complete_after_authorized_recovery'] and closure['top_level_starts']==closure['budget_cap']==31
    assert closure['GPU_runtime_failures']==closure['GPU_retries']==0 and closure['original_postrun_quality_failures']==1
    quality=load(ROOT/'correctness/QUALITY.json');assert quality['passed']
    for q in quality['all_static_processes']:
        if q.get('mode') in ('N0','N1'):
            assert q['false_negatives']==q['false_positives']==0 and q['queries']==40
            assert q['max_ordered_FP64_field_error']<=5e-5
    timing=load(ROOT/'timing/BASELINE_TIMING.json')
    profiles={m:load(ROOT/'profiler'/(n+'_METRICS.json')) for m,n in (('N0','NATIVE'),('N1','NON_PADDED'),('R0','READ_ONLY'))}
    assert profiles['R0']['work_inflation'] is None and not profiles['R0']['useful_search_proxy_applicable']
    # Rebuild the minimal offline analysis input from every published raw ACK/counter.
    with tempfile.TemporaryDirectory() as t:
        work=Path(t)/'work';work.mkdir();out=Path(t)/'computed'
        for s in ('qualification','primary','ncu'):
            (work/s).mkdir();write(work/s/'RESULTS.json',dict(complete=True))
        (work/'ncu/reports').mkdir();(work/'STARTS.jsonl').write_text('{}\n'*29)
        for m,v in timing['modes'].items():
            assert len(v['query_ACK_ms'])==len(v['process_means_ms'])==len(v['process_pass_ms'])==6
            for i,values in enumerate(v['query_ACK_ms']):
                assert len(values)==32 and all(math.isfinite(x) and x>0 for x in values)
                mean=sum(values)/32;assert mean==v['process_means_ms'][i]
                assert v['process_pass_ms'][i]>=sum(values)
                write(work/'primary'/f'r{i+1}_{m}.checked.json',dict(mean_query_ms=mean,query_ack_ms=values,pass_ms=v['process_pass_ms'][i]))
            p=profiles[m];values={'Kernel Name':{'value':p['kernel'],'unit':''},**p['metrics']}
            with (work/'ncu/reports'/f'{m}.base.csv').open('w') as f:
                writer=csv.writer(f);writer.writerow(values);writer.writerow([x['unit'] for x in values.values()]);writer.writerow([x['value'] for x in values.values()])
        analyze(work,out);assert load(out/'BASELINE_TIMING.json')==timing,'public raw ACK/metrics estimator recomputation'
    assert classify(timing['work_inflation'],timing['latency_recovery'],timing['modes']['N1']['median_process_mean_ms'],timing['modes']['R0']['median_process_mean_ms'])==timing['decision']
    dynamic=load(ROOT/'timing/DYNAMIC_INTEGRATION.json');old,new=(dynamic['modes'][k] for k in ('old','strengthened'))
    assert dynamic['inherited_trace_speedup']==old['meta']['trace_ms']/new['meta']['trace_ms']
    assert dynamic['inherited_trace_reduction']==1-new['meta']['trace_ms']/old['meta']['trace_ms']
    assert dynamic['original_failure_preserved'] and dynamic['old_GPU_not_rerun']
    for mode in (old,new):
        assert mode['measured_quality']['passed'] and mode['warmup_quality']['passed']
        assert mode['measured_quality']['queries']==256 and mode['warmup_quality']['queries']==8
        assert len(mode['ops'])==336
        for flag,count in dynamic['event_counts']['measured'].items():assert sum(int(v['flag'])==int(flag) for v in mode['ops'])==count
        assert all(math.isfinite(float(v['ack_ms'])) and float(v['ack_ms'])>=0 for v in mode['ops'])
    for name,h in dynamic['frozen_dynamic_sources'].items():assert sha(ROOT.parent.parent/name)==h,name
    assert dynamic['recovery_source_sha256']==sha(ROOT/'recover.py')
    oldidentity=load(ROOT/'evidence/OLD_OUTPUT_IDENTITY.json');assert oldidentity['passed'] and oldidentity['all_eight_payloads_equal']
    assert all(v['equal'] and v['current_sha256']==v['historical_sha256'] for v in oldidentity['payloads'].values())
    qa=load(ROOT/'evidence/FIGURE_QA.json');assert qa['passed'] and qa['no_Type3_fonts']
    for name,h in qa['figure_PDF_hashes'].items():assert sha(ROOT/'figures'/name)==h
    assert timing['decision'] in (ROOT/'DECISION.md').read_text()
    print('PASS:exact public set/frozen sources,29 static receipts,all576 raw ACKs,bootstrap/NCU metrics,31-start closure and qualified short pair')
if __name__=='__main__':verify()
