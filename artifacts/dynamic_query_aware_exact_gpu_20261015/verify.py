"""Public scalar/identity reconstruction only; never initializes CUDA or private inputs."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path
from common import HERE, REPO, MODES, sha, load, save, expected_jobs, requests, batches
from analyze import run as analyze, check as statistical_check
from traffic import query, maintenance
from audit_stage import output_files, report_files, GUARD_FILES
from summarize import run as summarize


def close(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a: close(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b): close(x, y)
    elif isinstance(a, float): assert math.isfinite(a) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)
    else: assert a == b, (a, b)


def write_csv(path, raw, metrics):
    with path.open('x', newline='') as f:
        writer = csv.writer(f); writer.writerow(['ID', 'Kernel Name', *metrics])
        writer.writerow(['', '', *[raw['normalized_units'][k] for k in metrics]])
        for row in raw['captures']: writer.writerow([row[0], raw['kernel_table'][row[1]], *row[4:]])


def main():
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); assert a.repo.resolve() == REPO and not a.out.exists() and not a.out.resolve().is_relative_to(HERE)
    manifest = load(HERE/'PUBLIC_MANIFEST.json')['files']
    files = {str(p.relative_to(HERE)): p for p in HERE.rglob('*') if p.is_file() and p.name != 'PUBLIC_MANIFEST.json'}
    assert files.keys() == manifest.keys()
    for n, r in manifest.items(): assert not files[n].is_symlink() and files[n].stat().st_size == r['bytes'] and sha(files[n]) == r['sha256']
    for folder, digest in [('pdx_bond_gpu_realizability_gate4_20261015', '0c1a0606502973bbd009a13910250e689b52294a7a4072d9aa46b7c4322e6306'),
                           ('pdx_bond_gpu_realizability_gate4_20261015_recovery_01', '1d4ed50badaaf92c24aa19799f15de396615a8fb6c3c0d1a5068acced25b6892')]:
        old = HERE.parent/folder; assert sha(old/'PUBLIC_MANIFEST.json') == digest
        for n, r in load(old/'PUBLIC_MANIFEST.json')['files'].items(): assert sha(old/n) == r['sha256']
    c = load(HERE/'CONTRACT.json'); identity = load(HERE/'evidence/INPUT_IDENTITY.json')
    assert sha(HERE/'CONTRACT.json') == identity['contract_sha256'] == identity['analysis_freeze']['contract_sha256']
    assert sha(HERE/'analyze.py') == identity['analysis_freeze']['analyzer_sha256']
    for n, h in identity['executed_sources'].items(): assert sha(REPO/n) == h
    for n, h in identity['postprocessing_sources'].items(): assert sha(HERE/n) == h
    spec = importlib.util.spec_from_file_location('immutable_pdx_generator', HERE.parent/'pdx_bond_gpu_realizability_gate4_20261015_recovery_01/gpu_prepare.py')
    generator = importlib.util.module_from_spec(spec); spec.loader.exec_module(generator)
    keeper, pdx, _ = generator.headers(REPO)
    full = generator.replace(keeper, 'for(int stage=0;stage<4;stage++)', 'for(int stage=0;stage<1;stage++)')
    full = generator.replace(full, 'progressive_stage<0,128>', 'progressive_stage<0,960>')
    for mode, text in zip(MODES, (full, keeper, pdx, pdx)):
        assert hashlib.sha256(text.encode()).hexdigest() == identity['generated_sources'][f'build/{mode}/selected.cuh']
    statistical_check(); a.out.mkdir(parents=True); (a.out/'primary').mkdir()
    processes = load(HERE/'evidence/PRIMARY_PROCESSES.json'); assert len(processes) == 72
    jobs = expected_jobs('primary'); by_label = {}
    for process, job in zip(processes, jobs):
        assert all(process['job'][k] == job[k] for k in ('label', 'mode', 'workload', 'round', 'order'))
        meta = process['metadata']; assert meta['N'] == 1000000 and meta['D'] == 960 and meta['B'] == 1 and meta['diagnostic'] == 0
        assert len(process['queries']) == len(process['stages']) == 168
        for q, want in zip(process['queries'], requests(job['workload'], 1000000)):
            assert all(q[k] == v for k, v in want.items()) and q['ack_ms'] > 0 and q['complete']
        assert math.isclose(meta['service_ms'], meta['events_ms']+meta['release_ms'], abs_tol=1e-7)
        assert math.isclose(meta['events_ms'], meta['query_ms']+meta['update_ms_including_statistics']+meta['other_ms'], abs_tol=1e-7)
        fake = dict(metadata=meta, all_target_query_records=process['queries'], query_stage_records=process['stages'])
        save(a.out/'primary'/(job['label']+'.checked.json'), fake); by_label[job['label']] = fake
    close(analyze(a.out), load(HERE/'results/TIMING.json'))
    close(summarize(processes), load(HERE/'results/SUMMARY.json'))
    captures = 0; summary = load(HERE/'results/TRAFFIC.json')['cells']
    for job in expected_jobs('query_ncu'):
        label = job['label']; original = load(HERE/'evidence'/('NCU_'+label+'.json'))
        csv_path = a.out/(label+'.csv'); write_csv(csv_path, original['raw'], c['NCU_metrics'])
        checked = {**by_label[f"W{job['workload']}_r1_{job['mode']}"], 'mode': job['mode'], 'workload': job['workload']}
        rebuilt = query(csv_path, checked, c['NCU_metrics']); rebuilt['raw']['raw_CSV_sha256'] = original['raw']['raw_CSV_sha256']
        close(rebuilt, original)
        close({k: v for k, v in original.items() if k not in ('raw', 'queries')}, summary[label])
        captures += len(original['raw']['captures'])
    original = load(HERE/'evidence/MAINTENANCE_NCU.json'); csv_path = a.out/'maintenance.csv'; write_csv(csv_path, original['raw'], c['NCU_metrics'])
    checked = by_label['W2_r1_S2_INC']; rebuilt = maintenance(csv_path, checked, c['NCU_metrics'], len(batches(2, 1000000)))
    rebuilt['raw']['raw_CSV_sha256'] = original['raw']['raw_CSV_sha256']; close(rebuilt, original)
    captures += len(original['raw']['captures'])
    quality = load(HERE/'evidence/QUALITY.json'); execution = load(HERE/'evidence/EXECUTION.json'); receipts = load(HERE/'evidence/QUALITY_RECEIPTS.json')
    all_jobs = [(s, j) for s in ('qualification', 'primary', 'query_ncu', 'maintenance_ncu') for j in expected_jobs(s)]
    assert quality['passed'] and len(quality['records']) == len(receipts) == len(all_jobs) == 117
    raw = load(HERE/'evidence/RAW_MANIFEST.json')['files']
    custody = load(HERE/'evidence/RAW_CUSTODY.json')
    assert custody['raw_manifest_sha256'] == sha(HERE/'evidence/RAW_MANIFEST.json') and custody['local_copy_payloads_verified']
    selected = {n: r for n, r in raw.items() if not n.startswith(('inputs/', 'cache/'))}
    excluded = {n: r for n, r in raw.items() if n not in selected}
    assert len(selected) == custody['selected_raw_files'] and sum(r['bytes'] for r in selected.values()) == custody['selected_raw_uncompressed_bytes']
    assert len(excluded) == custody['excluded_work_inputs_cache_files'] and sum(r['bytes'] for r in excluded.values()) == custody['excluded_work_inputs_cache_bytes']
    assert hashlib.sha256(json.dumps(excluded, sort_keys=True).encode()).hexdigest() == custody['excluded_work_input_identity_sha256']
    qa = load(HERE/'evidence/FIGURE_QA.json'); assert qa['passed'] and qa['PDF_render_DPI'] == 400
    for n, h in qa['files'].items(): assert sha(HERE/n) == h
    census = load(HERE/'evidence/STAGE_CENSUS.json')
    for stage in ('qualification', 'primary', 'query_ncu', 'maintenance_ncu'):
        jobs = expected_jobs(stage); record = census[stage]
        assert record['passed'] and record['no_extra_entries_or_symlinks'] and record['jobs'] == len(jobs)
        expected = {'REGISTERED.json', 'RESULTS.json'}
        for job in jobs:
            label = job['label']; expected.update(label+s for s in ('.command.json', '.checked.json', '.outer.log'))
            expected.update('guards/'+label+'/'+s for s in GUARD_FILES)
            expected.update('outputs/'+s for s in output_files(job)); expected.update('reports/'+s for s in report_files(job))
            assert raw[stage+'/'+label+'.command.json']['sha256'] == record['source_derived_command_hashes'][label]
        assert {n[len(stage)+1:] for n in raw if n.startswith(stage+'/')} == expected
    for (stage, job), q, r in zip(all_jobs, quality['records'], receipts):
        assert q['stage'] == r['stage'] == stage and q['label'] == r['label'] == job['label'] and q['passed']
        assert set(r['guard_files']) == GUARD_FILES and set(r['reports']) == report_files(job) and set(r['raw_outputs']) == output_files(job)
        assert raw[f"{stage}/{job['label']}.checked.json"]['sha256'] == r['checked_sha256']
        assert r['guard_sha256'] == r['guard_files']['receipt.json']
        for n, h in r['guard_files'].items(): assert raw[f"{stage}/guards/{job['label']}/{n}"]['sha256'] == h
        for n, record in r['reports'].items(): assert raw[f'{stage}/reports/{n}'] == record
        for n, record in r['raw_outputs'].items(): assert raw[f'{stage}/outputs/{n}'] == record
        if job.get('kind') == 'selftest': assert q['iterations'] == 100 and q['stream_slots'] == 2 and q['query_checks'] == 400
        else:
            assert q['false_negatives'] == q['false_positives'] == 0 and q['exact_native_squared_bits']
            assert q['complete_queries_including_warmup'] == 168 and q['formal_queries'] == 160
            assert q['independent_final_maps'] and q['final_device_vector_bytes_compared'] == job['N']*960*4
            if job['diagnostic'] == 2: assert q['internal_FP64_bit_checks'] > 0 and q['internal_FP64_bit_mismatches'] == 0
        if job.get('tool') in ('memcheck', 'racecheck', 'synccheck'): assert q['sanitizer_summary_zero']
    assert execution['complete'] and execution['GPU_starts'] == execution['max_GPU_starts'] == 117 and execution['failed_or_replaced_samples'] == 0
    assert execution['all_two_sided_isolation_valid'] and execution['stage_counts'] == dict(qualification=32, primary=72, query_ncu=12, maintenance_ncu=1)
    assert raw['STARTS.jsonl']['sha256'] == execution['start_ledger_sha256']
    for stage, h in execution['stage_result_hashes'].items(): assert raw[f'{stage}/RESULTS.json']['sha256'] == h
    static = load(HERE/'evidence/STATIC.json'); old = load(HERE.parent/'pdx_bond_gpu_realizability_gate4_20261015_recovery_01/evidence/STATIC.json')
    assert static['passed']
    for mode, record in static['records'].items():
        assert record['binary_sha256'] == identity['binaries'][mode] == raw[f'build/{mode}/service']['sha256']
        if mode != 'S0':
            expected = old['selected_functions']['keeper' if mode == 'S1' else 'candidate']
            for n, f in expected.items(): assert f['normalized_sass_sha256'] == record['functions'][n]['normalized_sass_sha256']
        for resource in record['resources'].values(): assert resource['STACK'] == resource['LOCAL'] == resource['SHARED'] == 0
    refusal = subprocess.run([sys.executable, '-O', str(HERE/'analyze.py')], capture_output=True)
    assert refusal.returncode != 0 and b'Optimized Python disables mandatory checks' in refusal.stderr
    save(a.out/'RECEIPT.json', dict(passed=True, public_files=len(files)+1, primary_processes=72,
        formal_primary_queries=72*160, normalized_NCU_kernels_reconstructed=captures, quality_receipts_bound=117,
        private_membership_scores_SASS_not_reexecuted=True, new_GPU_starts=0, public_manifest_sha256=sha(HERE/'PUBLIC_MANIFEST.json')))
    print('PASS:72process statistics,all NCU captures,117receipt bindings,immutable sources;0 new GPU starts')


if __name__ == '__main__': main()
