"""Curate scalar synthetic-model results; never ship full traces or GPU claims."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True, help='Fresh scratch output, not the source artifact')
    args = p.parse_args()
    artifact = Path(__file__).resolve().parent
    data = json.loads(args.results.read_text())
    rows = data['rows']
    contract = json.loads((artifact / 'CONTRACT.json').read_text())
    assert data['contract_sha256'] == hashlib.sha256((artifact / 'CONTRACT.json').read_bytes()).hexdigest()
    assert data['final'] == 'NO_GO_CROSS_QUERY_REUSE' and data['GPU_starts'] == 0
    args.out.mkdir(parents=True, exist_ok=False)

    def write(path, value):
        dest = args.out / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(value, indent=2) + '\n')

    write('evidence/RESULTS.json', data)
    write('workload/ARRIVAL_MODEL.json', {
        'model': 'iid exponential gaps rounded to1ps; no device service',
        'rates_qps': contract['rates_qps'], 'queries_per_rate': 100000,
        'mix': contract['query_mix'], 'seed_rule': contract['seed_rule'],
        'warmup': 0, 'final_partial_batch': 'ordinary timer drain',
        'real_arrivals': False, 'GIST_vectors_loaded': False})
    fields = ['rate_qps', 'queries', 'batches', 'batch_counts_B1_to_B8',
              'mean_B_batch_weighted', 'mean_B_query_experienced', 'p50_B_batch_weighted',
              'p90_B_batch_weighted', 'fraction_batches_B_ge_2', 'fraction_batches_B_ge_4',
              'fraction_batches_B_eq_8', 'fraction_queries_B_ge_2', 'fraction_queries_B_ge_4',
              'fraction_queries_B_eq_8', 'mixed_type_batches']
    write('workload/BATCH_DISTRIBUTIONS.json', {
        'mean_and_quantile_weighting': 'batch weighted; query experienced mean/fractions separate',
        'rows': [{k: r[k] for k in fields} for r in rows]})
    write('workload/QUEUEING.json', {
        'scope': 'deliberate collection only; not device backlog or Host-ready SLA',
        'unit': 'picoseconds', 'maximum_allowed': 500000000,
        'rows': [{'rate_qps': r['rate_qps'], **r['query_wait_ps']} for r in rows],
        'total_p99_SLA': 'UNKNOWN', 'device_stability': 'NOT_MODELED'})
    write('cost/SHARED_DB_BYTES.json', {
        'scope': 'optimistic source model only; not DRAM or total traffic',
        'DB_SHARED_BYTES_per_batch': 3840000000,
        'QUERY_STATE_UNKNOWN': True, 'OUTPUT_UNKNOWN': True, 'CONTROL_UNKNOWN': True,
        'rows': [{'rate_qps': r['rate_qps'], 'query_weighted_bytes': r['query_weighted_source_bytes'],
                  'exact_primary_fraction': {'numerator': 3840000000 * r['batches'], 'denominator': r['queries']},
                  'batch_weighted_E_bytes_over_B': r['batch_weighted_E_source_bytes_over_B'],
                  'point_decision': r['point_decision']} for r in rows]})
    timing = json.loads((args.repo / 'artifacts/progressive_gpu_gate2_20261013/timing/PRIMARY_TIMING.json').read_text())
    write('cost/KEEPER_COMPARISON.json', {
        'scope': 'reference comparison; original fixed32 range workload, not same-contract mixed range/kNN E2E',
        'keeper_source_bytes': 1014828776,
        'keeper_range_Host_ready_ms': timing['modes']['P1']['median'],
        'strengthened_B1_range_Host_ready_ms': timing['modes']['B1']['median'],
        'keeper_mixed_or_knn_source_bytes': 'UNKNOWN', 'new_GPU_performance': 'NOT_RUN',
        'rows': [{'rate_qps': r['rate_qps'], 'query_weighted_bytes': r['query_weighted_source_bytes'],
                  'over_frozen_range_reference': r['query_weighted_over_keeper']} for r in rows]})
    write('evidence/ANALYTIC_OPPORTUNITY.json', {
        'scope': 'continuous-Poisson long-run oracle; Decimal60 approximations except explicit rational bounds; not a finite-sample bound',
        'derivation': 'B=min(1+Poisson(lambda/2000),8); E[B]<=1+lambda/2000; long-run bytes/query=DB_BYTES/E[B], not E_batch[DB_BYTES/B].',
        'bound_proves': 'at all frozen rates even uncapped long-run source lower bound exceeds1GB; cap8 cannot improve it',
        'rows': [{'rate_qps': r['rate_qps'], **r['analytic']} for r in rows]})
    print('PASS: scalar curation; raw source results unchanged')


if __name__ == '__main__':
    main()
