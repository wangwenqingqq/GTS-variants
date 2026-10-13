"""Curate scalar CPU evidence and independent numeric/novelty decisions."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from model import HERE, ROOT, read, save, sha


def percentile(values, p):
    v = sorted(values); location = (len(v) - 1) * p
    lo = math.floor(location); hi = math.ceil(location)
    return v[lo] + (v[hi] - v[lo]) * (location - lo)


def histogram_percentile(histogram, p):
    location = (sum(histogram) - 1) * p
    def at(rank):
        count = 0
        for value, frequency in enumerate(histogram):
            count += frequency
            if count > rank:
                return value
        raise AssertionError('invalid histogram')
    lo = math.floor(location); hi = math.ceil(location)
    return at(lo) + (at(hi) - at(lo)) * (location - lo)


def main(a):
    if sys.flags.optimize:
        raise SystemExit('Python optimized mode is unsupported: required checks must run')
    r = read(a.cpu / 'RESULTS.json'); c = read(HERE / 'CONTRACT.json')
    registration = read(a.cpu / 'REGISTERED.json'); raw = read(a.cpu / 'RAW_IDENTITY.json')
    qualification = read(a.cpu / 'QUALIFICATION.json')
    assert r['complete'] and r['GPU_starts'] == 0 and r['full_population_processes'] == 1
    assert r['registration_sha256'] == sha(a.cpu / 'REGISTERED.json')
    assert r['raw_identity_sha256'] == sha(a.cpu / 'RAW_IDENTITY.json')
    assert r['qualification_sha256'] == sha(a.cpu / 'QUALIFICATION.json')
    assert r['source_hashes'] == registration['source_hashes']
    for p, h in r['source_hashes'].items():
        assert sha(ROOT / p) == h, p
    for p, h in c['parent_files'].items():
        assert sha(ROOT / p) == h, p
    assert [x['qid'] for x in r['M2']] == c['workload']['range_qids']
    assert [x['qid'] for x in r['M3']] == c['workload']['knn_qids']
    assert len(qualification['queries']) == 64 and all(x['passed'] for x in qualification['queries'])
    n, d, q = 1000000, 960, 32; denominator = n * d * 4 * q
    g2 = read(ROOT / 'artifacts/progressive_gpu_gate2_20261013/cost/PRE_GPU_COST.json')
    x2 = r['M2']; base = sum(512 * (n + x['exact_survivors128']) for x in x2)
    candidate = sum(1024 * x['code_survivors256'] for x in x2)
    code_reads = sum(128 * (n + x['code_survivors128']) for x in x2)
    assert sum(x['exact_survivors128'] for x in x2) == g2['rows'][1]['input_pairs']
    assert sum(x['exact_survivors256'] for x in x2) == g2['rows'][2]['input_pairs']
    assert sum(x['hits'] for x in x2) == g2['rows'][-1]['output_pairs']
    assert all(x[k] == 0 for x in x2 for k in ('bound_violations', 'false_negative',
                                             'false_positive', 'fallback_score_bit_mismatch'))
    size = r['code_bytes'] + r['edges_bytes']; size_ratio = size / (n * d * 4)
    saving = 1 - candidate / base
    m2 = dict(complete=True, experiment='M2_INTERVAL_SCREEN', decision='KILL_M2',
              numeric_pass=size_ratio <= .25 and saving >= .50,
              novelty_admission=False, kill_axes=['known_interval_filter_refine'],
              CPU_screen_quality_pass=True, new_GPU_quality='NOT_TESTED',
              evidence_state='partial', interpretation='Observed CPU screening counts; counterfactual logical bytes, not DRAM/latency',
              representation_bytes=size, representation_fraction_of_raw=size_ratio,
              representation_code_bytes=r['code_bytes'], representation_boundary_bytes=r['edges_bytes'],
              raw_stage12_baseline_bytes_per_query=base / q,
              raw_stage12_candidate_bytes_per_query=candidate / q,
              raw_stage12_saving_fraction=saving,
              code_reads_bytes_per_query=code_reads / q, query_LUT_bytes=256*256*8,
              unchanged_later_coordinate_bytes_per_query=sum(x['coordinate_bytes'] for x in g2['rows'][2:]) / q,
              known_coordinate_code_LUT_payload_bytes_per_query=(candidate + code_reads) / q
                  + 256*256*8 + sum(x['coordinate_bytes'] for x in g2['rows'][2:]) / q,
              first_two_stages_per_query_saving_distribution={k:percentile(
                  [1-1024*x['code_survivors256']/(512*(n+x['exact_survivors128'])) for x in x2], p)
                  for k,p in (('min',0),('p10',.1),('p50',.5),('p90',.9),('max',1))},
              total_verified_range_hits=sum(x['hits'] for x in x2), query_object_pairs=n*q,
              omitted_from_payload=['state/ID/flags/compaction/cache sectors','kernel/control/waits',
                  'encoding/training/updates','complete output/release costs'],
              reason='The concrete8-bit interval screen does not establish a mechanism distinct from VA-file/BOND-style compression',
              reopen='A different non-incremental representation, exactness, dynamic maintenance and same-contract external evidence')
    public3, aggregate = [], []
    for index, name in enumerate(('oracle_final_cutoff', 'fixed_seed_cutoff')):
        rows = [x['variants'][index] for x in r['M3']]
        hist = [sum(v['required_dims_histogram'][i] for v in rows) for i in range(961)]
        assert sum(hist) == n*q
        assert all(v[k] == 0 for v in rows for k in ('false_negative','false_positive',
                      'full_score_bit_mismatch','first_crossing_violation'))
        bytes0 = sum(v['coordinate_bytes'] for v in rows)
        assert bytes0 == sum(i*x for i,x in enumerate(hist))*4
        stage = sum(v['four_stage_coordinate_bytes'] for v in rows)
        ag = dict(name=name, query_object_pairs=n*q, mean_required_dims=bytes0/(4*n*q),
                  required_dims_quantiles={k:histogram_percentile(hist,p) for k,p in
                                          (('p10',.1),('p50',.5),('p90',.9))},
                  query_mean_dims_distribution={k:percentile([v['mean_required_dims'] for v in rows],p)
                     for k,p in (('min',0),('p10',.1),('p50',.5),('p90',.9),('max',1))},
                  ideal_coordinate_bytes_per_query=bytes0/q, ideal_byte_reduction=1-bytes0/denominator,
                  four_stage_coordinate_bytes_per_query=stage/q,
                  four_stage_byte_reduction=1-stage/denominator,
                  retained_at_checkpoint=[sum(v['four_stage_survivors'][i] for v in rows) for i in range(4)],
                  required_dims_histogram=hist)
        if index == 1:
            charged = sum(v['seed_charged_coordinate_bytes'] for v in rows)
            charged_stage = sum(v['seed_charged_four_stage_bytes'] for v in rows)
            ag.update(seed_bytes_per_query=256*960*4, seed_charged_coordinate_bytes_per_query=charged/q,
                      seed_charged_ideal_byte_reduction=1-charged/denominator,
                      seed_charged_four_stage_bytes_per_query=charged_stage/q,
                      seed_charged_four_stage_byte_reduction=1-charged_stage/denominator)
        aggregate.append(ag)
    for row in r['M3']:
        variants = []
        for v in row['variants']:
            public = {k:x for k,x in v.items() if k not in ('exact_k_ids','exact_k_scores_hex')}
            public['topk_identity_sha256'] = hashlib.sha256(json.dumps(
                [v['exact_k_ids'],v['exact_k_scores_hex']],separators=(',',':')).encode()).hexdigest()
            variants.append(public)
        public3.append(dict(qid=row['qid'],query_index=row['query_index'],variants=variants))
    m3 = dict(complete=True, experiment='M3_INITIAL_K8_HEADROOM', decision='KILL_M3',
              numeric_pass=aggregate[0]['ideal_byte_reduction'] >= .40,
              novelty_admission=False, kill_axes=['shared_progressive_primitive_already_implemented'],
              CPU_quality_pass=True,new_GPU_quality='NOT_TESTED', evidence_state='partial',
              primary='Oracle-final-cutoff coordinate-only ideal; not a free deployable threshold',
              aggregate=aggregate, reason='No non-incremental mechanism beyond known partial-distance pruning and shared range/kNN threshold substitution',
              reopen='A genuinely different hardware/execution mechanism with charged threshold/selection/control and external same-contract evidence')
    output = a.output_dir.resolve() if a.output_dir else HERE
    if a.output_dir:
        if output == ROOT or ROOT in output.parents:
            raise ValueError('Fresh reanalysis output must be outside the repository')
        output.mkdir()
        for name in ('m1_layout', 'm2_representation', 'm3_unified_knn'):
            (output / name).mkdir()
    evidence = output / 'evidence'; evidence.mkdir(exist_ok=True)
    save(output / 'm1_layout/RESULT.json',read(a.m1))
    save(output / 'm2_representation/RESULT.json',m2)
    save(output / 'm3_unified_knn/RESULT.json',m3)
    save(evidence / 'CPU_QUERY_RECORDS.json',dict(M2=x2,M3=public3))
    save(evidence / 'RAW_IDENTITY.json',raw)
    save(evidence / 'SOURCE_IDENTITY.json',dict(parent_commit=c['parent_commit'],
        data_sha256=r['data_sha256'],measurement_source_hashes=r['source_hashes'],
        references=r['references'],binary_sha256=r['binary_sha256'],
        registration_sha256=r['registration_sha256'],results_sha256=sha(a.cpu/'RESULTS.json'),
        qualification_sha256=r['qualification_sha256'],raw_identity_sha256=r['raw_identity_sha256']))
    save(evidence / 'EXECUTION_CLOSURE.json',dict(complete=True,CPU_workers=4,GPU_starts=0,
        new_NCU_processes=0,full_population_processes=1,fixture_tests_passed=True,
        first4096_subset_query_checks=64,full_population_range_queries=32,
        full_population_knn_queries=32,query_object_pairs_each_candidate=n*q,
        new_GPU_implementation=False,external_comparisons='NOT_EXECUTED_NO_WINNER',
        operational_wall_seconds=r['seconds'],wall_seconds_are_performance=False,
        started_unix=registration['started_unix'],finished_unix=r['finished_unix'],
        failure_records=0,final_decision='NO_DISTINCT_MECHANISM',
        parent_Gate3_decision='UNCLASSIFIED',parent_files_unchanged=True))
    save(evidence / 'ENVIRONMENT.json',dict(CPU=c['execution']['hardware'],
         python=c['execution']['python'],numpy=c['execution']['numpy'],
         compiler=c['execution']['compiler'],compiler_flags=c['execution']['compiler_flags'],
         workers=4,nice=10,CUDA_visible_devices='empty',no_GPU_initialization=True,
         GPU_clocks_power_libraries='not changed/not used; historical GPU state is in parent evidence'))
    print('CURATED NO_DISTINCT_MECHANISM; M2/M3 numeric passes',m2['numeric_pass'],m3['numeric_pass'])


if __name__ == '__main__':
    p = argparse.ArgumentParser();p.add_argument('--cpu',type=Path,required=True)
    p.add_argument('--m1',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,help='Fresh report directory outside repository; never overwrites')
    main(p.parse_args())
