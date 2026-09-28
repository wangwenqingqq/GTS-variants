#!/usr/bin/env python3
"""Audit four paired 4090-left rounds and summarize complete hot queries."""
import argparse
import csv
import json
import statistics
from pathlib import Path


MODES = ('Q', 'B16', 'B32')
DATASETS = ('GIST', 'Deep')


def read_run(root, dataset, label):
    path = root / 'data' / dataset / '1000000' / 'runs' / label
    receipt = json.loads((path / 'receipt.json').read_text())
    rows = list(csv.DictReader((path / 'result.csv').open()))
    assert receipt['exit_code'] == 0 and receipt['stop_reason'] is None
    assert receipt['validation']['pass'] and receipt['post_gpu_clear']
    assert not receipt['runtime_errors'] and len(rows) == 8
    return receipt, rows


def main(args):
    complete = json.loads((args.root / 'logs' / 'timing_COMPLETE.json').read_text())
    assert len(complete['runs']) == 4 * len(DATASETS) * len(MODES)
    evidence = {'host': '4090-left', 'rounds': 4, 'datasets': {},
                'binary_sha256': None, 'gpu_snapshot': None,
                'sanitizer': {}}
    all_binary_hashes = set()
    for dataset in DATASETS:
        results = []
        for round_id in range(4):
            round_rows = {}
            round_means = {}
            for mode in MODES:
                receipt, rows = read_run(args.root, dataset,
                                         f'timing_{round_id}_{mode}')
                assert receipt['mode'] == mode and receipt['tool'] == 'clean'
                all_binary_hashes.add(receipt['binary_sha256'])
                if evidence['gpu_snapshot'] is None:
                    evidence['gpu_snapshot'] = json.loads(
                        (args.root / 'data' / dataset / '1000000' / 'runs' /
                         f'timing_{round_id}_{mode}' / 'before.json').read_text())['gpu']
                round_rows[mode] = [(int(row['qid']), int(row['count']),
                                     row['ordered_hash']) for row in rows]
                round_means[mode] = statistics.mean(
                    float(row['query_us']) for row in rows) / 1000
            assert round_rows['Q'] == round_rows['B16'] == round_rows['B32']
            results.append({'round': round_id, 'query_mean_ms': round_means,
                            'qids': [row[0] for row in round_rows['Q']]})
        stats = {mode: statistics.median(
            result['query_mean_ms'][mode] for result in results)
            for mode in MODES}
        ratios = {f'{a}/{b}': statistics.median(
            result['query_mean_ms'][a] / result['query_mean_ms'][b]
            for result in results)
            for a, b in (('Q', 'B16'), ('Q', 'B32'), ('B16', 'B32'))}
        evidence['datasets'][dataset] = {
            'median_query_ms': stats, 'median_paired_speedup': ratios,
            'rounds': results,
        }
    assert len(all_binary_hashes) == 1
    evidence['binary_sha256'] = all_binary_hashes.pop()
    for dataset in DATASETS:
        for mode in MODES:
            receipt, rows = read_run(args.root, dataset,
                                     f'{dataset.lower()}_{mode}_gate')
            assert receipt['binary_sha256'] == evidence['binary_sha256']
    receipt, _ = read_run(args.root, 'Deep', 'deep_B32_memcheck2')
    assert receipt['tool'] == 'memcheck'
    assert receipt['binary_sha256'] == evidence['binary_sha256']
    evidence['sanitizer']['Deep_B32_memcheck'] = {
        'pass': True, 'rows': receipt['validation']['rows']}
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    for dataset, result in evidence['datasets'].items():
        print(dataset, result['median_query_ms'],
              result['median_paired_speedup'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path,
                        default=Path('/home/ls/tmp/gts_parent_mask_20260925'))
    parser.add_argument('--output', type=Path, default=Path('EVIDENCE.json'))
    main(parser.parse_args())
