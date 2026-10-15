"""Reconstruct the public GPU decision without CUDA, private data, or new samples."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from analyze import check, classify, summarize
from gpu_prepare import HERE, PRIOR, headers, load, save, sha
from gpu_campaign import schedule


def close(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a: close(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b): close(x, y)
    elif isinstance(a, float):
        assert math.isfinite(a) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)
    else:
        assert a == b, (a, b)


def traffic(r, qids, metrics):
    assert r['queries'] == 32 and r['launches'] == len(r['captured_kernels']) == 416
    assert r['all_kernels_included'] and r['diagnostic_only']
    keys = dict(DRAM_bytes=metrics[1], DRAM_read_bytes=metrics[2],
                DRAM_write_bytes=metrics[3], L2_bytes=metrics[4], kernel_ms=metrics[0])
    groups = collections.defaultdict(list)
    for i, q in enumerate(r['queries_detail']):
        rows = r['captured_kernels'][i*13:(i+1)*13]
        assert q['qid'] == qids[i] and q['kernels'] == 13
        assert [x['stage'] for x in rows if x['kind'] == 'scan'] == [1, 2, 3, 4]
        assert collections.Counter(x['kind'] for x in rows) == {'scan': 4, 'compact': 8, 'fields': 1}
        for x in rows:
            assert set(x['metrics']) == set(metrics)
            assert all(math.isfinite(v) and v >= 0 for v in x['metrics'].values())
            m = x['metrics']; close(m[metrics[1]], m[metrics[2]] + m[metrics[3]])
            groups[x['kind'], x['stage']].append(x)
        for k, raw in keys.items():
            close(sum(x['metrics'][raw] for x in rows)/(1e6 if k == 'kernel_ms' else 1), q[k])
        for raw in metrics[5:]:
            close(sum(x['metrics'][raw]*x['metrics'][metrics[0]] for x in rows)/sum(x['metrics'][metrics[0]] for x in rows), q['duration_weighted_percent'][raw])
    for k in keys: close(float(np.mean([q[k] for q in r['queries_detail']])), r['means'][k])
    assert len(groups) == len(r['families']) == 9
    for f in r['families']:
        rows = groups[f['kind'], f['stage']]
        assert len(rows) == f['launches']
        assert sorted(set(x['kernel'] for x in rows)) == f['kernel_names']
        for k, raw in keys.items():
            close(sum(x['metrics'][raw] for x in rows)/32/(1e6 if k == 'kernel_ms' else 1), f['mean_'+k+'_per_query'])
    vals = [q['DRAM_bytes'] for q in r['queries_detail']]
    close(r['DRAM_query_distribution'], dict(min=min(vals), p90=float(np.quantile(vals, .9)), max=max(vals)))


def main():
    p = argparse.ArgumentParser(); p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); a = p.parse_args()
    repo = a.repo.resolve()
    assert repo/'artifacts'/HERE.name == HERE
    assert not a.out.exists(), 'Fresh output directory required'
    assert not a.out.resolve().is_relative_to(HERE), 'Keep verification outputs outside the public bundle'
    manifest = load(HERE/'PUBLIC_MANIFEST.json')['files']
    files = {str(p.relative_to(HERE)): p for p in HERE.rglob('*') if p.is_file() and p.name != 'PUBLIC_MANIFEST.json'}
    assert files.keys() == manifest.keys()
    for n, r in manifest.items():
        assert not files[n].is_symlink() and files[n].stat().st_size == r['bytes'] and sha(files[n]) == r['sha256']
    old = load(PRIOR/'PUBLIC_MANIFEST.json')['files']
    assert sha(PRIOR/'PUBLIC_MANIFEST.json') == '0c1a0606502973bbd009a13910250e689b52294a7a4072d9aa46b7c4322e6306'
    assert len(old)+1 == 47
    for n, r in old.items(): assert sha(PRIOR/n) == r['sha256'] and (PRIOR/n).stat().st_size == r['bytes']
    c = load(HERE/'GPU_CONTRACT.json'); identity = load(HERE/'evidence/INPUT_IDENTITY.json')
    assert c['decision_priority_approved'] and c['max_GPU_starts'] == 26
    assert identity['data_sha256'] == c['data_sha256'] and identity['qids'] == c['qids']
    assert identity['dependency_sources'] == c['parents']
    for n, h in c['parents'].items(): assert sha(repo/n) == h
    for n, h in identity['source_inputs'].items(): assert sha(repo/n) == h
    for n, h in identity['controller_sources'].items(): assert sha(HERE/n) == h
    assert sha(HERE/'analyze.py') == identity['analyzer_sha256']
    assert sha(HERE/'curate.py') == identity['curator_sha256']
    route = load(HERE/'NCU_ROUTE_PREFLIGHT.json')
    assert route['before_NCU_starts'] and route['failed_NCU_or_replaced_samples'] == 0
    assert sha(HERE/'gpu_campaign_ncu.py') == route['controller_sha256']
    assert sha(HERE/'gpu_campaign.py') == route['prior_controller_sha256']
    generated = headers(repo)
    for n, text in zip(('keeper.cuh', 'candidate.cuh', 'bond_fixtures.hpp'), generated):
        assert hashlib.sha256(text.encode()).hexdigest() == identity['generated_sources'][n]
    check()
    timing = load(HERE/'evidence/TIMING.json'); pairs = []
    expected = [(r, m) for r in range(1, 7) for m in ('keeper', 'candidate')]
    assert [(x['round'], x['mode']) for x in timing['processes']] == expected
    for r in range(1, 7):
        pair = {}
        for x in timing['processes'][(r-1)*2:r*2]:
            assert len(x['query_ACK_ms']) == 32 and min(x['query_ACK_ms']) > 0
            close(float(np.mean(x['query_ACK_ms'])), x['mean_query_ms'])
            assert x['meta']['N'] == 1000000 and x['meta']['D'] == 960 and x['meta']['B'] == 1
            assert not x['meta']['diagnostic'] and x['meta']['diagnostic_mode'] == 0
            assert x['order'] == ('forward' if r % 2 else 'reverse')
            pair[x['mode']] = x['mean_query_ms']
        pairs.append(pair)
    stats = summarize(pairs)
    close(stats, {k: timing[k] for k in stats})
    dram = load(HERE/'evidence/DRAM.json')
    for mode in ('keeper', 'candidate'): traffic(dram['modes'][mode], c['qids'], c['NCU_metrics'])
    ratio = dram['modes']['candidate']['means']['DRAM_bytes']/dram['modes']['keeper']['means']['DRAM_bytes']
    close(ratio, dram['DRAM_ratio']); close(1-ratio, dram['DRAM_reduction'])
    quality = load(HERE/'evidence/QUALITY.json'); receipts = load(HERE/'evidence/QUALITY_RECEIPTS.json')
    raw = load(HERE/'evidence/RAW_MANIFEST.json')['files']
    jobs = [(s, j) for s in ('qualification', 'primary', 'ncu', 'breakdown') for j in schedule(s)]
    assert len(jobs) == len(quality['records']) == len(receipts) == 26 and quality['passed']
    for (stage, job), q, r in zip(jobs, quality['records'], receipts):
        label = job['label']; assert q['stage'] == r['stage'] == stage and q['label'] == r['label'] == label and q['passed']
        assert r['guard_sha256'] == r['guard_files']['receipt.json']
        bindings = {f'{stage}/guards/{label}/{n}': h for n, h in r['guard_files'].items()}
        bindings.update({f'{stage}/reports/{n}': h for n, h in r['reports'].items()})
        bindings.update({f'{stage}/outputs/{n}': h for n, h in r['outputs'].items()})
        bindings[f'{stage}/{label}.checked.json'] = r['checked_sha256']
        for n, h in bindings.items(): assert raw[n]['sha256'] == h
        if 'N' in q:
            assert q['queries'] == 40 and q['measured_queries'] == 32 and q['all_complete_members']
            assert q['false_negatives'] == q['false_positives'] == 0
            assert q['max_ordered_FP64_field_error'] <= 5e-5
        if job.get('tool') in ('memcheck', 'racecheck', 'synccheck'): assert q['sanitizer_summary_zero']
        if label in ('target_keeper', 'target_candidate'):
            assert q['complete_checkpoint_IDs_checked'] and q['internal_ordered_FP64_scores_checked'] == 7711
            assert q['internal_FP64_bit_mismatches'] == 0
    execution = load(HERE/'evidence/EXECUTION.json')
    assert execution['stage_counts'] == dict(qualification=10, primary=12, ncu=2, breakdown=2)
    assert execution['complete'] and execution['all_two_sided_isolation_valid']
    assert execution['GPU_starts'] == execution['max_GPU_starts'] == 26
    assert execution['failed_or_replaced_GPU_samples'] == execution['CPU_population_reruns'] == execution['prior_GPU_starts'] == 0
    assert raw['STARTS.jsonl']['sha256'] == execution['start_ledger_sha256']
    assert sha(HERE/'NCU_ROUTE_PREFLIGHT.json') == execution['NCU_route_preflight_sha256']
    for stage, h in execution['stage_results_sha256'].items(): assert raw[f'{stage}/RESULTS.json']['sha256'] == h
    static = load(HERE/'evidence/STATIC.json')
    assert static['passed'] and static['keeper_device_functions_equal_parent']
    for mode in ('keeper', 'candidate'):
        assert static['records'][mode]['binary_sha256'] == identity['binaries'][mode] == raw[f'build/{mode}']['sha256']
        assert len(static['selected_functions'][mode]) == len(static['records'][mode]['resources']) == 5
        for res in static['records'][mode]['resources'].values():
            assert res['STACK'] == res['SHARED'] == res['LOCAL'] == 0
        for f in static['selected_functions'][mode].values():
            assert not any('MMA' in op for op in f['opcode_counts'])
    breakdown = load(HERE/'evidence/OP_BREAKDOWN.json')
    for mode in ('keeper', 'candidate'):
        b = breakdown['modes'][mode]; assert len(b['queries']) == 32
        for k, v in b['means'].items(): close(float(np.mean([q[k] for q in b['queries']])), v)
        if mode == 'candidate':
            for i, q in enumerate(b['queries']):
                want = load(PRIOR/'source/STAGE_SURVIVORS.json')['per_query'][i]
                assert [s['output'] for s in q['stages'][:3]] == [want[str(s)] for s in (128, 256, 512)]
    for k, v in breakdown['candidate_ordering_CPU_means_ms'].items():
        close(float(np.mean([float(q[k]) for q in breakdown['ordering_records']])), v)
    source = load(PRIOR/'source/SOURCE_BYTES.json')['mean_coordinate_source_bytes']['decimal']
    assert source == c['CPU_gate']['source_bytes'] == 711680776
    decision = load(HERE/'evidence/DECISION.json')
    assert classify(source, stats['latency_ratio'], ratio, stats['wins'], stats['paired_95_CI'][1]) == decision['label'] == 'PRIOR_ART_WINS'
    assert decision['strong_secondary'] and stats['latency_ratio'] <= .8 and ratio <= .8
    close(stats['latency_ratio'], decision['latency_ratio']); close(ratio, decision['DRAM_ratio'])
    close(stats['paired_95_CI'], decision['paired95CI']); assert decision['paired_wins'] == stats['wins'] == 6
    # CSVs are a portable rendering contract, independent of plotting-library metadata.
    with (HERE/'figures/latency.csv').open() as f: rows = list(csv.DictReader(f))
    assert len(rows) == 12
    for x, y in zip(rows, timing['processes']): close(float(x['mean_ACK_ms']), y['mean_query_ms'])
    with (HERE/'figures/dram.csv').open() as f: rows = list(csv.DictReader(f))
    assert len(rows) == 2
    for x, mode in zip(rows, ('keeper', 'candidate')): close(float(x['all_kernel_DRAM_GB']), dram['modes'][mode]['means']['DRAM_bytes']/1e9)
    custody = load(HERE/'evidence/CUSTODY.json')
    assert custody['raw_files_sha256_checked'] == len(raw) == 1707 and custody['passed']
    a.out.mkdir(parents=True)
    save(a.out/'RECEIPT.json', dict(passed=True, public_files=len(files)+1,
         old_checkpoint_files_unchanged=47, fresh_GPU_or_CPU_population_starts=0,
         primary_processes=12, captured_kernels_reconstructed=832, quality_receipts_bound=26,
         label=decision['label'], public_subset_only=True,
         raw_membership_or_SASS_not_reexecuted=True, manifest_sha256=sha(HERE/'PUBLIC_MANIFEST.json')))
    print('PASS: public decision, timing/traffic reconstruction, source identities,26 receipts;no new GPU/CPU population')


if __name__ == '__main__': main()
