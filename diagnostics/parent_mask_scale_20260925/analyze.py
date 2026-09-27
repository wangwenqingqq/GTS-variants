#!/usr/bin/env python3
"""Audit and summarize three paired block-size rounds on 4090-left."""
import argparse
import csv
import json
import statistics
from pathlib import Path


GROUPS = (16, 32, 64, 128, 256, 512)
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
    assert len(complete['runs']) == 3 * len(DATASETS) * len(GROUPS)
    evidence = {'host': '4090-left', 'rounds': 3, 'datasets': {},
                'binary_sha256': None, 'gpu_snapshot': None, 'sanitizer': {}}
    binary_hashes = set()
    for dataset in DATASETS:
        records = []
        for round_id in range(3):
            means = {}
            outputs = {}
            for group in GROUPS:
                mode = f'B{group}'
                label = f'timing_{round_id}_{mode}'
                receipt, rows = read_run(args.root, dataset, label)
                assert receipt['mode'] == mode and receipt['tool'] == 'clean'
                binary_hashes.add(receipt['binary_sha256'])
                if evidence['gpu_snapshot'] is None:
                    path = args.root / 'data' / dataset / '1000000' / 'runs' / label
                    evidence['gpu_snapshot'] = json.loads(
                        (path / 'before.json').read_text())['gpu']
                means[mode] = statistics.mean(
                    float(row['query_us']) for row in rows) / 1000
                outputs[mode] = [(int(row['qid']), int(row['count']),
                                  row['ordered_hash']) for row in rows]
            assert all(outputs[f'B{g}'] == outputs['B32'] for g in GROUPS)
            records.append({'round': round_id, 'query_mean_ms': means,
                            'qids': [row[0] for row in outputs['B32']]})
        median_ms = {f'B{group}': statistics.median(
            row['query_mean_ms'][f'B{group}'] for row in records)
            for group in GROUPS}
        paired = {f'B{group}/B32': statistics.median(
            row['query_mean_ms'][f'B{group}'] /
            row['query_mean_ms']['B32'] for row in records)
            for group in GROUPS}
        evidence['datasets'][dataset] = {
            'median_query_ms': median_ms,
            'median_paired_latency_ratio': paired,
            'rounds': records,
        }
    assert len(binary_hashes) == 1
    evidence['binary_sha256'] = binary_hashes.pop()
    for dataset in DATASETS:
        for group in GROUPS[2:]:
            receipt, _ = read_run(args.root, dataset,
                                  f'{dataset.lower()}_B{group}_gate')
            assert receipt['binary_sha256'] == evidence['binary_sha256']
    receipt, _ = read_run(args.root, 'Deep', 'deep_B512_memcheck')
    assert receipt['tool'] == 'memcheck'
    assert receipt['binary_sha256'] == evidence['binary_sha256']
    evidence['sanitizer']['Deep_B512_memcheck'] = {
        'pass': True, 'rows': receipt['validation']['rows']}
    args.output.write_text(json.dumps(evidence, indent=2) + '\n')
    for dataset, result in evidence['datasets'].items():
        print(dataset, result['median_query_ms'],
              result['median_paired_latency_ratio'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path,
                        default=Path('/home/ls/tmp/gts_parent_mask_scale_20260925'))
    parser.add_argument('--output', type=Path, default=Path('EVIDENCE.json'))
    main(parser.parse_args())
