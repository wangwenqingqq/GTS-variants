"""Reconstruct public scalars and evidence bindings;no CUDA or private search data."""
if not __debug__:
    raise SystemExit('Mandatory checks require ordinary Python without optimization.')
import argparse
import collections
import csv
import hashlib
import math
from pathlib import Path
import subprocess
import sys
from common import HERE,REPO,PARENT,load,save,sha,jobs
from primary import analyze_compact,expand
from derive import derive
from timeline import PHASES,check_phases,quantiles
from generate import adapter
from audit_stage import GUARD,output_names,report_names
from analyze import check as statistical_check


def close(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys(),(a.keys()-b.keys(),b.keys()-a.keys())
        for k in a:close(a[k],b[k])
    elif isinstance(a,list):
        assert len(a)==len(b)
        for x,y in zip(a,b):close(x,y)
    elif isinstance(a,float):assert math.isfinite(a) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)
    else:assert a==b,(a,b)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--plot',action='store_true');a=p.parse_args()
    assert not a.out.exists() and not a.out.resolve().is_relative_to(HERE);a.out.mkdir(parents=True)
    manifest=load(HERE/'PUBLIC_MANIFEST.json')['files']
    assert not any(p.is_symlink() for p in HERE.rglob('*'))
    files={str(p.relative_to(HERE)):p for p in HERE.rglob('*') if p.is_file() and p.name!='PUBLIC_MANIFEST.json'}
    assert files.keys()==manifest.keys()
    for n,r in manifest.items():assert files[n].stat().st_size==r['bytes'] and sha(files[n])==r['sha256'],n
    for folder,digest in [('dynamic_update_critical_path_20261015','ed4a8724ce0925ee55e7969ed451ea8899c7fed636d4e7e6b6973c675948a266'),
                          ('dynamic_query_aware_exact_gpu_20261015','e7bc8bd13000998ab5198ac2a0a0e1b51a45072c022c2b16c292543a21f9bd77'),
                          ('pdx_bond_gpu_realizability_gate4_20261015','0c1a0606502973bbd009a13910250e689b52294a7a4072d9aa46b7c4322e6306'),
                          ('pdx_bond_gpu_realizability_gate4_20261015_recovery_01','1d4ed50badaaf92c24aa19799f15de396615a8fb6c3c0d1a5068acced25b6892')]:
        old=HERE.parent/folder;assert sha(old/'PUBLIC_MANIFEST.json')==digest
        for n,r in load(old/'PUBLIC_MANIFEST.json')['files'].items():assert sha(old/n)==r['sha256']
    identity=load(HERE/'evidence/IDENTITY.json');bridge=load(HERE/'evidence/PUBLIC_SOURCE_BRIDGE.json')['files'];assert set(bridge)=={'SCOPE.md'}
    for n,h in identity['executed_sources'].items():
        path=REPO/n
        if path==HERE/'SCOPE.md':assert h==bridge['SCOPE.md']['executed_sha256'] and sha(path)==bridge['SCOPE.md']['published_sha256']
        else:assert sha(path)==h,n
    assert sha(HERE/'CONTRACT.json')==identity['contract_sha256']==identity['analysis_freeze']['contract_sha256']
    assert sha(HERE/'analyze.py')==identity['analysis_freeze']['analyzer_sha256'] and identity['analysis_freeze']['before_primary']
    assert sha(HERE/'PLACEMENT_RECOVERY.json')==identity['placement_amendment_sha256']
    for n,h in identity['postprocessing_sources'].items():assert sha(HERE/n)==h
    post=load(HERE/'evidence/POSTPROCESSING.json');assert post['complete'] and post['new_GPU_starts']==0 and post['prior_scalar_and_Host_time_totals_unchanged']
    for n,h in post['hardened_curation']['files'].items():assert sha(HERE/n)==h
    assert hashlib.sha256(adapter().encode()).hexdigest()==identity['generated']['build/adapter.cuh']
    static=identity['STATIC'];assert static['passed'] and static['search_SASS_identical'] and static['new_update_kernels']==0
    parent=load(PARENT/'evidence/STATIC.json')['records']['S2_STALE']['functions']
    for name,record in static['records'].items():
        assert record['binary_sha256']==identity['binaries'][name]
        assert record['selected_function_hashes']=={k:v['normalized_sass_sha256'] for k,v in parent.items()}
        assert all(v['STACK']==v['LOCAL']==v['SHARED']==0 for v in record['resources'].values())
    primary=load(HERE/'evidence/PRIMARY_SCALARS.json');assert len(primary)==84
    for record,job in zip(primary,jobs('primary')):
        assert record['job']==job;expanded=expand(record)
        if job['kind']=='micro':
            assert len(record['samples'])==job['K']//job['batch']
            assert record['metadata']['N']==1000000 and record['metadata']['K']==8192
    timing=load(HERE/'results/TIMING.json');close(analyze_compact(primary),timing);statistical_check()
    traces=load(HERE/'results/TIMELINES.json');assert set(traces)=={j['label'] for j in jobs('timeline')}
    normalized_ranges=0
    for label,trace in traces.items():
        with (HERE/'timeline'/(label+'.csv')).open() as f:rows=list(csv.DictReader(f))
        rows=[{k:v if k=='operator' else int(v) for k,v in row.items()} for row in rows];assert rows
        assert [r['index'] for r in rows]==list(range(len(rows)));normalized_ranges+=len(rows)
        for r in rows:
            assert sum(r[k] for k in ('sync_API_ns','copy_API_ns','other_API_ns','bookkeeping_Host_ns','other_Host_ns'))==r['scope_ns']
            check_phases(r['operator'],{n:r[n+'_ranges'] for n in PHASES if r[n+'_ranges']})
            if r['operator'] in ('D','I'):
                assert r['sync_API_calls']==1 and r['other_API_calls']==r['launch_API_calls']==r['kernels']==r['other_copy_activity_bytes']==0
                if r['operator']=='I':assert r['copy_API_calls']==1 and r['D2D_activity_bytes']==0
                else:assert r['D2D_activity_bytes']==r['copy_API_calls']*3840 and r['H2D_activity_bytes']==0
        assert {r['operator'] for r in rows}==trace['operators'].keys()
        for kind,record in trace['operators'].items():
            selected=[r for r in rows if r['operator']==kind];assert len(selected)==record['ranges']
            total={k:sum(r[k] for r in selected) for k in selected[0] if k not in ('index','operator','begin_ns')}
            assert total==record['totals'];close(quantiles([r['scope_ns'] for r in selected]),record['scope_ns_quantiles'])
            if kind in ('D','I'):
                names=record['runtime_API_calls'];assert names.get('cudaStreamSynchronize_v3020')==len(selected)
                assert names.get('cudaMemcpyAsync_v3020',0)==total['copy_API_calls']
                assert set(names)<={'cudaMemcpyAsync_v3020','cudaStreamSynchronize_v3020'}
        assert trace['formal_span_ns']==rows[-1]['begin_ns']+rows[-1]['scope_ns'] and not trace['unmatched_formal_device_activities']
        assert not trace['diagnostics']['unreviewed_warning_hashes'] and trace['diagnostics']['warnings']
        metrics=trace['sampled_GPU_metrics'];assert metrics['exact_DRAM_bytes'] is metrics['exact_L2_bytes'] is None
        if trace['job']['kind']!='copy':assert trace['expected_update_binding']['per_ACKs']==sum(r['operator'] in ('D','I') for r in rows)
    service=traces['trace_service'];assert service['operators']['Q']['totals']['kernels']==service['operators']['Q']['totals']['launch_API_calls']==1895
    assert service['operators']['D']['totals']['copy_API_calls']==500000 and service['operators']['I']['totals']['copy_API_calls']==977
    services=load(HERE/'evidence/SERVICE_OPERATORS.json');close(derive(timing,primary,traces,services),load(HERE/'results/DERIVED.json'))
    raw=load(HERE/'evidence/RAW_MANIFEST.json')['files'];qualities=load(HERE/'evidence/QUALITY.json');receipts=load(HERE/'evidence/RECEIPTS.json')
    assert qualities['passed'] and len(qualities['records'])==len(receipts)==124
    alljobs=[(s,j) for s in ('qualification','primary','timeline') for j in jobs(s)]
    for (stage,job),quality,receipt in zip(alljobs,qualities['records'],receipts):
        label=job['label'];assert quality['job']==job and quality['passed'] and receipt['stage']==stage and receipt['label']==label
        assert receipt['checked_sha256']==raw[f'{stage}/{label}.checked.json']['sha256']
        assert set(receipt['guard_files'])==GUARD and set(receipt['reports'])==report_names(job) and set(receipt['raw_outputs'])==output_names(job)
        assert receipt['guard_sha256']==receipt['guard_files']['receipt.json']
        for n,h in receipt['guard_files'].items():assert raw[f'{stage}/guards/{label}/{n}']['sha256']==h
        for n,r in receipt['reports'].items():assert raw[f'{stage}/reports/{n}']==r
        for n,r in receipt['raw_outputs'].items():assert raw[f'{stage}/outputs/{n}']==r
        if job['kind']=='micro':assert quality['complete_queries']==40 and quality['false_negatives']==quality['false_positives']==0 and quality['exact_native_squared_bits'] and quality['independent_full_maps']
        if job['kind']=='service':
            assert quality['complete_queries_including_warmup']==168 and quality['formal_queries']==160
            assert quality['false_negatives']==quality['false_positives']==0 and quality['exact_native_squared_bits'] and quality['independent_final_maps']
            assert quality['actual_mutation_witnesses']==1000000 and quality['final_device_vector_bytes_compared']==3840000000
        if job['kind']=='selftest':assert quality['iterations']==100 and quality['stream_slots']==2 and quality['query_checks']==400
        if job['kind']=='copy':assert quality['all_destination_bytes_compared']==2147483648
        if job.get('tool') in ('memcheck','racecheck','synccheck'):assert quality['sanitizer_summary_zero']
    census=load(HERE/'evidence/STAGE_CENSUS.json')
    for stage in ('qualification','primary','timeline'):
        c=census[stage];assert c['passed'] and c['no_extra_entries_or_symlinks'] and c['jobs']==len(jobs(stage))
        expected={'REGISTERED.json','RESULTS.json'}
        for job in jobs(stage):
            label=job['label'];expected|={label+s for s in ('.command.json','.checked.json','.outer.log')}
            expected|={'guards/'+label+'/'+n for n in GUARD}|{'outputs/'+n for n in output_names(job)}|{'reports/'+n for n in report_names(job)}
            assert raw[f'{stage}/{label}.command.json']['sha256']==c['source_derived_commands'][label]
        assert {n[len(stage)+1:] for n in raw if n.startswith(stage+'/')}==expected
    execution=load(HERE/'evidence/EXECUTION.json');assert execution['complete'] and execution['accepted_fresh_GPU_processes']==124
    assert execution['stage_counts']==dict(qualification=29,primary=84,timeline=11)
    assert execution['R1_preserved_starts']==84 and execution['R2_refused_admission_starts']==1 and execution['refused_attempt_CUDA_targets']==0
    assert execution['total_campaign_starts']==execution['max_campaign_starts']==209 and execution['automatic_retries']==0
    assert execution['start_ledger_sha256']==raw['STARTS.jsonl']['sha256']
    for stage,h in execution['stage_results_sha256'].items():assert raw[f'{stage}/RESULTS.json']['sha256']==h
    custody=load(HERE/'evidence/RAW_CUSTODY.json');assert custody['local_copy_payloads_verified'] and custody['raw_manifest_sha256']==sha(HERE/'evidence/RAW_MANIFEST.json')
    assert custody['raw_work_files_verified']==len(raw) and custody['raw_work_uncompressed_bytes']==sum(r['bytes'] for r in raw.values())
    qa=load(HERE/'evidence/FIGURE_QA.json');assert qa['passed'] and qa['PDF_render_DPI']==400
    for n,h in qa['files'].items():assert sha(HERE/n)==h
    subprocess.run([sys.executable,str(HERE/'test_evidence.py')],check=True)
    if a.plot:
        target=a.out/'figures';subprocess.run([sys.executable,str(HERE/'plot.py'),'--data',str(HERE),'--out',str(target)],check=True)
        for path in (HERE/'figures').glob('*.csv'):assert path.read_bytes()==(target/path.name).read_bytes()
    refused=subprocess.run([sys.executable,'-O',str(HERE/'verify.py')],capture_output=True);assert refused.returncode and b'Mandatory checks' in refused.stderr
    save(a.out/'RECEIPT.json',dict(passed=True,public_files=len(files)+1,primary_processes=84,normalized_trace_ranges=normalized_ranges,
        quality_receipts_bound=124,private_membership_vectors_and_raw_traces_not_reexecuted=True,figure_CSVs_regenerated=a.plot,new_GPU_starts=0,
        public_manifest_sha256=sha(HERE/'PUBLIC_MANIFEST.json')))
    print('PASS:84 process statistics,11 normalized traces,124 receipt bindings,immutable sources and prior artifacts;0 GPU starts')


if __name__=='__main__':main()
