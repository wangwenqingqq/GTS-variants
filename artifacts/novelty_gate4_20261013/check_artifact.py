"""Recheck public scalar accounting and frozen identities without raw data/GPU."""
import hashlib
import json
import math
import sys
from pathlib import PurePosixPath
from analyze import histogram_percentile, percentile
from model import HERE, ROOT, read, sector_model, sha


def same(actual, expected):
    if isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def quantiles(values, histogram=False):
    f = histogram_percentile if histogram else percentile
    pairs = [('p10', .1), ('p50', .5), ('p90', .9)]
    if not histogram:
        pairs = [('min', 0), *pairs, ('max', 1)]
    return {k: f(values, p) for k, p in pairs}


def main():
    if sys.flags.optimize:
        raise SystemExit('Python optimized mode is unsupported: required checks must run')
    c = read(HERE / 'CONTRACT.json')
    source = read(HERE / 'evidence/SOURCE_IDENTITY.json')
    closure = read(HERE / 'evidence/EXECUTION_CLOSURE.json')
    raw = read(HERE / 'evidence/RAW_IDENTITY.json')
    records = read(HERE / 'evidence/CPU_QUERY_RECORDS.json')
    same(source['parent_commit'], c['parent_commit'])
    same(source['data_sha256'], c['workload']['data_sha256'])
    same(sha(HERE / 'evidence/RAW_IDENTITY.json'), source['raw_identity_sha256'])
    assert len(source['measurement_source_hashes']) == 13
    for p, h in {**c['parent_files'], **source['measurement_source_hashes']}.items():
        same(sha(ROOT / p), h)
    parent = read(ROOT / 'artifacts/progressive_dynamic_gate3_20261013/evidence/INPUT_IDENTITY.json')
    pools = set(map(str, c['workload']['range_qids'] + c['workload']['knn_qids']))
    same(set(source['references']), pools)
    for q, h in source['references'].items():
        same(h, parent['input_hashes'][f'cache/{q}.f64'])
    assert len(raw['files']) == 456
    for name, meta in raw['files'].items():
        path = PurePosixPath(name)
        assert not path.is_absolute() and '..' not in path.parts
        assert meta['bytes'] >= 0 and len(meta['sha256']) == 64
    same(raw['files']['REGISTERED.json']['sha256'], source['registration_sha256'])
    same(raw['files']['QUALIFICATION.json']['sha256'], source['qualification_sha256'])
    same(raw['files']['build/replay.so']['sha256'], source['binary_sha256'])
    same(raw['files']['raw/codes.u8']['bytes'], 256000000)
    same(raw['files']['raw/edges.f64']['bytes'], 256*257*8)
    recheck = read(HERE / 'evidence/RAW_RECHECK.json')
    same(recheck['raw_identity_sha256'], source['raw_identity_sha256'])
    same(recheck['results_sha256'], source['results_sha256'])
    same(recheck['raw_files_rehashed'], len(raw['files']))
    same(recheck['raw_bytes_rehashed'], sum(v['bytes'] for v in raw['files'].values()))
    same(recheck['saved_array_query_checks'], 64)
    same(recheck['fresh_population_replays'], 0)
    same(recheck['GPU_starts'], 0)
    assert recheck['complete'] and recheck['seed_charge_rechecked_from_saved_dims']
    assert recheck['ordered_membership_score_crossing_checks_passed']
    pins = read(HERE / 'prior_art/PINNED_SOURCE_IDENTITY.json')['sources']
    originals = {s['id']: s for s in read(HERE / 'prior_art/SOURCES.json')['sources'] if 'commit' in s}
    same({s['id'] for s in pins}, set(originals))
    for s in pins:
        same(s['url'], originals[s['id']]['url'])
        same(s['commit'], originals[s['id']]['commit'])
        assert s['bytes'] > 0 and len(s['sha256']) == 64
    same(closure['GPU_starts'], 0)
    same(closure['new_NCU_processes'], 0)
    same(closure['full_population_processes'], 1)
    same(closure['first4096_subset_query_checks'], 64)
    same(closure['failure_records'], 0)
    assert closure['complete'] and closure['fixture_tests_passed']
    assert not closure['new_GPU_implementation'] and not closure['wall_seconds_are_performance']
    same(closure['final_decision'], 'NO_DISTINCT_MECHANISM')
    same(closure['parent_Gate3_decision'], 'UNCLASSIFIED')
    same(closure['external_comparisons'], 'NOT_EXECUTED_NO_WINNER')
    assert closure['parent_files_unchanged']
    m1 = read(HERE / 'm1_layout/RESULT.json')
    same(m1, sector_model())
    same(m1['numeric_pass'], False)

    n, d, queries = c['workload']['N'], c['workload']['D'], 32
    full_bytes = n*d*4*queries
    for kind, key in (('M2', 'range_qids'), ('M3', 'knn_qids')):
        same([r['qid'] for r in records[kind]], c['workload'][key])
        same([r['query_index'] for r in records[kind]], list(range(queries)))
        same(closure['full_population_' + ('range' if kind == 'M2' else 'knn') + '_queries'], queries)
    same(closure['query_object_pairs_each_candidate'], n*queries)
    cost = read(ROOT / 'artifacts/progressive_gpu_gate2_20261013/cost/PRE_GPU_COST.json')
    r2 = read(HERE / 'm2_representation/RESULT.json')
    base = candidate = codes = hits = 0
    fractions = []
    for row in records['M2']:
        assert n >= row['code_survivors128'] >= row['code_survivors256'] >= row['hits']
        assert row['code_survivors128'] >= row['exact_survivors128']
        assert row['code_survivors256'] >= row['exact_survivors256'] >= row['hits']
        same(row['n'], n)
        for key in ('bound_violations', 'false_negative', 'false_positive', 'fallback_score_bit_mismatch'):
            same(row[key], 0)
        b, v = 512*(n+row['exact_survivors128']), 1024*row['code_survivors256']
        base += b; candidate += v; codes += 128*(n+row['code_survivors128']); hits += row['hits']
        fractions.append(1-v/b)
        name = f"M2.{row['query_index']:02d}.{row['qid']}.json"
        same(hashlib.sha256((json.dumps(row, indent=2)+'\n').encode()).hexdigest(), raw['files'][name]['sha256'])
    same(sum(x['exact_survivors128'] for x in records['M2']), cost['rows'][1]['input_pairs'])
    same(sum(x['exact_survivors256'] for x in records['M2']), cost['rows'][2]['input_pairs'])
    same(hits, cost['rows'][-1]['output_pairs'])
    size = n*256+256*257*8
    later = sum(x['coordinate_bytes'] for x in cost['rows'][2:])/queries
    lut = 256*256*8
    for key, value in dict(representation_bytes=size, representation_fraction_of_raw=size/(n*d*4),
            raw_stage12_baseline_bytes_per_query=base/queries,
            raw_stage12_candidate_bytes_per_query=candidate/queries, raw_stage12_saving_fraction=1-candidate/base,
            code_reads_bytes_per_query=codes/queries, query_LUT_bytes=lut,
            unchanged_later_coordinate_bytes_per_query=later,
            known_coordinate_code_LUT_payload_bytes_per_query=(candidate+codes)/queries+lut+later,
            first_two_stages_per_query_saving_distribution=quantiles(fractions),
            total_verified_range_hits=hits, query_object_pairs=n*queries).items():
        same(r2[key], value)
    same(r2['numeric_pass'], size/(n*d*4) <= .25 and 1-candidate/base >= .5)
    same(r2['numeric_pass'], True)

    r3 = read(HERE / 'm3_unified_knn/RESULT.json')
    for variant, aggregate in enumerate(r3['aggregate']):
        hist = [0]*(d+1); means = []; payload = stage_payload = seed_payload = seed_stage = 0
        survivors = [0]*4
        for row in records['M3']:
            v = row['variants'][variant]; h = v['required_dims_histogram']
            assert len(h) == d+1 and h[0] == 0 and all(isinstance(x, int) and x >= 0 for x in h)
            same(sum(h), n)
            byte_count = sum(i*f for i, f in enumerate(h))*4
            count = [sum(h[s+1:]) for s in (128, 256, 512)]+[v['retained']]
            stage = 512*n+512*count[0]+1024*count[1]+1792*count[2]
            same(v['coordinate_bytes'], byte_count)
            same(v['mean_required_dims'], byte_count/(4*n))
            same(v['required_dims_quantiles'], quantiles(h, histogram=True))
            same(v['four_stage_survivors'], count)
            same(v['four_stage_coordinate_bytes'], stage)
            assert c['workload']['knn_k'] <= v['retained'] <= h[-1]
            for key in ('false_negative', 'false_positive', 'full_score_bit_mismatch', 'first_crossing_violation'):
                same(v[key], 0)
            assert len(v['topk_identity_sha256']) == 64
            same(v['topk_identity_sha256'], row['variants'][0]['topk_identity_sha256'])
            hist = [a+b for a, b in zip(hist, h)]; means.append(v['mean_required_dims'])
            payload += byte_count; stage_payload += stage
            survivors = [a+b for a, b in zip(survivors, count)]
            if variant == 1:
                same(v['seed_bytes'], 256*d*4)
                assert byte_count <= v['seed_charged_coordinate_bytes'] <= byte_count+v['seed_bytes']
                assert stage <= v['seed_charged_four_stage_bytes'] <= stage+v['seed_bytes']
                assert float.fromhex(v['threshold_hex']) >= float.fromhex(row['variants'][0]['threshold_hex'])
                seed_payload += v['seed_charged_coordinate_bytes']; seed_stage += v['seed_charged_four_stage_bytes']
        for key, value in dict(query_object_pairs=n*queries, mean_required_dims=payload/(4*n*queries),
                required_dims_quantiles=quantiles(hist, histogram=True), query_mean_dims_distribution=quantiles(means),
                ideal_coordinate_bytes_per_query=payload/queries, ideal_byte_reduction=1-payload/full_bytes,
                four_stage_coordinate_bytes_per_query=stage_payload/queries,
                four_stage_byte_reduction=1-stage_payload/full_bytes,
                retained_at_checkpoint=survivors, required_dims_histogram=hist).items():
            same(aggregate[key], value)
        if variant == 1:
            for key, value in dict(seed_bytes_per_query=256*d*4,
                    seed_charged_coordinate_bytes_per_query=seed_payload/queries,
                    seed_charged_ideal_byte_reduction=1-seed_payload/full_bytes,
                    seed_charged_four_stage_bytes_per_query=seed_stage/queries,
                    seed_charged_four_stage_byte_reduction=1-seed_stage/full_bytes).items():
                same(aggregate[key], value)
    same(r3['numeric_pass'], r3['aggregate'][0]['ideal_byte_reduction'] >= .4)
    same(r3['numeric_pass'], True)
    for result, decision in ((m1, 'KILL_M1'), (r2, 'KILL_M2'), (r3, 'KILL_M3')):
        same(result['decision'], decision)
    assert not r2['novelty_admission'] and not r3['novelty_admission']
    for result in (r2, r3):
        same(result['new_GPU_quality'], 'NOT_TESTED')
    same(percentile([1, 3, 8], .5), 3)
    same(histogram_percentile([0, 1, 0, 1], .5), 2.)
    manifest = HERE / 'PUBLICATION_SET.json'
    if manifest.exists():
        entries = read(manifest)['files']
        actual = [str(p.relative_to(ROOT)) for p in sorted(HERE.rglob('*'))
                  if p.is_file() and p != manifest and '__pycache__' not in p.parts]
        same([x['path'] for x in entries], actual)
        for entry in entries:
            p = ROOT / entry['path']
            assert not p.is_symlink()
            same(p.stat().st_size, entry['bytes'])
            same(sha(p), entry['sha256'])
    print('PASS: frozen source/parent identities,64 query scalar records,456 raw identities, independent numeric/novelty gates; no GPU or raw-data replay')


if __name__ == '__main__':
    main()
