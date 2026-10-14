"""Verify frozen inputs, accounting and (optionally) every synthetic trace row."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
from replay import analytic, classify, percentile, DB_BYTES, KEEPER_BYTES, WINDOW_PS, N, RATES
from test_model import main as fixtures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--raw', type=Path)
    args = parser.parse_args()
    artifact = Path(__file__).resolve().parent
    contract = json.loads((artifact / 'CONTRACT.json').read_text())
    results = json.loads((artifact / 'evidence/RESULTS.json').read_text())
    assert results['contract_sha256'] == hashlib.sha256((artifact / 'CONTRACT.json').read_bytes()).hexdigest()
    assert contract['novelty_admission'] == 'NOT_ADMITTED' and contract['bounded_CPU_exception']['human_confirmed']
    for path, digest in contract['parent_input_sha256'].items():
        assert hashlib.sha256((args.repo / path).read_bytes()).hexdigest() == digest
    admission = json.loads((artifact / 'evidence/ADMISSION.json').read_text())
    for name in ['PRIOR_ART', 'SOURCE_IDENTITIES']:
        ext = '.md' if name == 'PRIOR_ART' else '.json'
        assert admission[name + '_sha256'] == hashlib.sha256((artifact / (name + ext)).read_bytes()).hexdigest()
    assert admission['GPU_authorized'] is False
    identity = json.loads((artifact / 'evidence/EXECUTED_SOURCE_IDENTITY.json').read_text())
    delivered = (artifact / 'replay.py').read_text()
    guard = "if not __debug__:\n    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')\n"
    assert delivered.count(guard) == 1
    assert hashlib.sha256(delivered.encode()).hexdigest() == identity['delivered_replay_sha256']
    assert hashlib.sha256(delivered.replace(guard, '', 1).encode()).hexdigest() == identity['executed_replay_sha256']
    fixtures()
    assert [r['rate_qps'] for r in results['rows']] == list(RATES)
    shared = json.loads((artifact / 'cost/SHARED_DB_BYTES.json').read_text())['rows']
    distribution = json.loads((artifact / 'workload/BATCH_DISTRIBUTIONS.json').read_text())['rows']
    queues = json.loads((artifact / 'workload/QUEUEING.json').read_text())['rows']
    for row, cost, dist, queue in zip(results['rows'], shared, distribution, queues):
        counts, nb = row['batch_counts_B1_to_B8'], row['batches']
        assert sum(counts) == nb and sum((b + 1) * c for b, c in enumerate(counts)) == N == row['queries']
        assert row['mean_B_batch_weighted'] == N / nb
        assert row['query_weighted_source_bytes'] == DB_BYTES * nb / N
        assert row['query_weighted_over_keeper'] == DB_BYTES * nb / (N * KEEPER_BYTES)
        assert row['mean_B_query_experienced'] == sum((b + 1)**2 * c for b, c in enumerate(counts)) / N
        assert row['batch_weighted_E_source_bytes_over_B'] == sum(DB_BYTES / (b + 1) * c for b, c in enumerate(counts)) / nb
        assert row['seed'] == 2026101400 + row['rate_qps']
        assert row['fraction_batches_B_ge_2'] == (nb - counts[0]) / nb
        assert row['fraction_batches_B_ge_4'] == sum(counts[3:]) / nb
        assert row['fraction_batches_B_eq_8'] == counts[7] / nb
        assert row['fraction_queries_B_ge_2'] == (N - counts[0]) / N
        assert row['fraction_queries_B_ge_4'] == sum((b + 1) * c for b, c in enumerate(counts) if b >= 3) / N
        assert row['fraction_queries_B_eq_8'] == 8 * counts[7] / N
        assert row['point_decision'] == classify(N, nb, row['query_wait_ps']['max'])
        assert row['point_decision']['label'] == 'NO_GO_CROSS_QUERY_REUSE'
        assert row['analytic'] == analytic(row['rate_qps'])
        bound = row['analytic']['source_model_lower_bound_fraction']
        assert bound['numerator'] > 1_000_000_000 * bound['denominator']
        assert cost['exact_primary_fraction'] == {'numerator': DB_BYTES * nb, 'denominator': N}
        assert cost['query_weighted_bytes'] == row['query_weighted_source_bytes']
        assert cost['batch_weighted_E_bytes_over_B'] == row['batch_weighted_E_source_bytes_over_B']
        assert all(value == row[key] for key, value in dist.items())
        assert all(queue[key] == value for key, value in row['query_wait_ps'].items())
        assert row['query_wait_ps']['p90'] <= row['query_wait_ps']['max'] <= WINDOW_PS
        if args.raw:
            raw = args.raw / row['raw_trace']['file']
            assert raw.stat().st_size == row['raw_trace']['bytes']
            assert hashlib.sha256(raw.read_bytes()).hexdigest() == row['raw_trace']['sha256']
            sizes, waits, kinds, mixed, next_qid, previous_arrival, prior_deadline = [], [], Counter(), 0, 0, -1, None
            with gzip.open(raw, 'rt', newline='') as f:
                grouped = itertools.groupby(csv.DictReader(f), lambda r: int(r['batch_id']))
                for expected_bid, (bid, records) in enumerate(grouped):
                    records = list(records)
                    assert bid == expected_bid and 1 <= len(records) <= 8
                    arrival = [int(r['arrival_ps']) for r in records]
                    assert arrival == sorted(arrival) and arrival[0] >= previous_arrival
                    if prior_deadline is not None:
                        assert arrival[0] > prior_deadline
                    dispatch = int(records[0]['dispatch_ps'])
                    expected = arrival[-1] if len(records) == 8 else arrival[0] + WINDOW_PS
                    assert dispatch == expected and arrival[-1] <= arrival[0] + WINDOW_PS
                    mixed += len({r['kind'] for r in records}) == 2
                    sizes.append(len(records))
                    for r, time in zip(records, arrival):
                        assert int(r['query_id']) == next_qid
                        next_qid += 1
                        assert int(r['dispatch_ps']) == dispatch
                        wait = int(r['wait_ps'])
                        assert wait == dispatch - time and 0 <= wait <= WINDOW_PS
                        kinds[r['kind']] += 1
                        waits.append(wait)
                    previous_arrival = arrival[-1]
                    prior_deadline = dispatch if len(records) < 8 else None
            assert next_qid == N and kinds == Counter(range=N // 2, knn=N // 2)
            assert counts == [sizes.count(b) for b in range(1, 9)]
            assert mixed == row['mixed_type_batches']
            assert row['query_wait_ps'] == {'mean': sum(waits) / N, 'p50': percentile(waits, .5),
                                           'p90': percentile(waits, .9), 'p99': percentile(waits, .99), 'max': max(waits)}
    closure = json.loads((artifact / 'evidence/EXECUTION_CLOSURE.json').read_text())
    assert closure['CPU_primary_starts'] == closure['CPU_primary_successes'] == 1
    assert closure['synthetic_queries'] == 400000 and closure['exact_distance_evaluations'] == 0
    assert closure['quality_FN'] is None and closure['quality_FP'] is None
    assert closure['GPU_starts'] == closure['remote_compute_starts'] == 0
    manifest = artifact / 'PUBLICATION_SET.json'
    if manifest.exists():
        items = json.loads(manifest.read_text())['files']
        expected = {item['path'] for item in items} | {'PUBLICATION_SET.json'}
        actual = {file.relative_to(artifact).as_posix() for file in artifact.rglob('*')
                  if file.is_file() and '__pycache__' not in file.parts}
        assert expected == actual
        for item in items:
            target = artifact / item['path']
            assert target.stat().st_size == item['bytes']
            assert hashlib.sha256(target.read_bytes()).hexdigest() == item['sha256']
    print(json.dumps({'passed': True, 'raw_queries_checked': 400000 if args.raw else 0,
                      'scope': 'synthetic admission, not search correctness or SLA',
                      'final': results['final'], 'GPU_starts': 0}))


if __name__ == '__main__':
    main()
