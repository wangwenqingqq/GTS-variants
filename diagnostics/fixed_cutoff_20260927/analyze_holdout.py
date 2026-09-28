#!/usr/bin/env python3
"""Audit and summarize held-out fixed-depth cutoff measurements."""
import csv
import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
RAW = HERE / 'local/holdout_artifacts/data'
DATASETS = ('GIST', 'Deep', 'Tloc')
KINDS = ('half', 'normal', 'double', 'quad', 'oct',
         'x16', 'x32', 'x64', 'all')
ORIGINAL_QIDS = {728999, 133791, 64023, 356678,
                 947731, 238099, 346554, 301735}


def run(dataset, label):
    folder = RAW / dataset / '1000000/runs' / label
    receipt = json.loads((folder / 'receipt.json').read_text())
    rows = list(csv.DictReader((folder / 'result.csv').open()))
    assert len(rows) == 24
    assert receipt['exit_code'] == 0 and not receipt['stop_reason']
    assert not receipt['runtime_errors'] and receipt['post_gpu_clear']
    assert receipt['warmup'] == 8 and receipt['repeats'] == 1
    mean_ms = statistics.mean(float(row['query_us']) for row in rows) / 1000
    return receipt, rows, mean_ms


def ratio_rounds(dataset, kind, numerator, denominator, rounds):
    num = [run(dataset, f'{kind}_{numerator.lower()}_{i}')[2]
           for i in rounds]
    den = [run(dataset, f'{kind}_{denominator.lower()}_{i}')[2]
           for i in rounds]
    ratios = [a / b for a, b in zip(num, den)]
    return {'numerator_ms': num, 'denominator_ms': den,
            'ratio_by_round': ratios, 'median_ratio': statistics.median(ratios),
            'numerator_wins': sum(x < 1 for x in ratios)}


def main():
    receipts = []
    output = {'host': '4090-left', 'gpu': 'NVIDIA GeForce RTX 4090',
              'n': 1000000, 'holdout_queries': 24,
              'warmup': 8, 'repeats': 1, 'input_sha256': {},
              'screen_ms': {}, 'paired': {}, 'tloc_candidates': {}}
    for dataset in DATASETS:
        qids = [int(x) for x in (RAW / dataset / '1000000/fixtures/queries.qid').read_text().split()]
        assert qids[0] == 24 and len(qids) == 25
        assert len(set(qids[1:])) == 24 and not ORIGINAL_QIDS.intersection(qids[1:])
        if dataset == 'GIST':
            output['query_ids'] = qids[1:]
        else:
            assert qids[1:] == output['query_ids']
        output['screen_ms'][dataset] = {}
        kinds = ('half', 'normal') if dataset != 'Tloc' else KINDS
        for kind in kinds:
            ref_receipt, ref_rows, ref_ms = run(dataset, f'{kind}_f_0')
            assert ref_receipt['mode'] == 'F'
            assert ref_receipt['validation']['pass'] is False
            reference = [(row['qid'], row['count'], row['ordered_hash'])
                         for row in ref_rows]
            assert [int(row['qid']) for row in ref_rows] == qids[1:]
            modes = ('F', 'C1', 'C3') if dataset != 'Tloc' else {
                'half': ('F', 'C1', 'C2', 'C3', 'C4', 'C5', 'J'),
                'normal': ('F', 'C1', 'C2', 'C3', 'C4', 'C5', 'J'),
                'double': ('F', 'C1', 'C2', 'C3', 'C4', 'C5', 'J'),
                'quad': ('F', 'C2', 'C3', 'C4', 'J'),
                'oct': ('F', 'C2', 'C3', 'C4', 'J'),
                'x16': ('F', 'C3', 'J'),
                'x32': ('F', 'C3', 'J'),
                'x64': ('F', 'C3', 'J'),
                'all': ('F', 'C3', 'J'),
            }[kind]
            output['screen_ms'][dataset][kind] = {'F': ref_ms}
            for mode in modes[1:]:
                receipt, rows, ms = run(dataset, f'{kind}_{mode.lower()}_0')
                assert receipt['validation']['pass']
                assert receipt['radius'] == ref_receipt['radius']
                observed = [(row['qid'], row['count'], row['ordered_hash'])
                            for row in rows]
                assert observed == reference, (dataset, kind, mode)
                output['screen_ms'][dataset][kind][mode] = ms
            output['input_sha256'][dataset] = ref_receipt['input_sha256']
    for dataset in DATASETS:
        for path in (RAW / dataset / '1000000/runs').glob('*/receipt.json'):
            receipt = json.loads(path.read_text())
            receipts.append(receipt)
            assert receipt['exit_code'] == 0 and not receipt['stop_reason']
            assert not receipt['runtime_errors'] and receipt['post_gpu_clear']
            assert receipt['validation']['pass'] or (receipt['mode'] == 'F' and
                receipt['label'].endswith('_f_0'))
    assert len(receipts) == 93
    assert sum(not x['validation']['pass'] for x in receipts) == 13
    hashes = {x['binary_sha256'] for x in receipts}
    assert len(hashes) == 1
    output['binary_sha256'] = hashes.pop()
    output['run_count'] = len(receipts)
    output['validated_nonreference_runs'] = 80
    output['paired']['Tloc_normal_F_over_C3'] = ratio_rounds('Tloc', 'normal', 'F', 'C3', range(1, 4))
    output['paired']['Tloc_normal_J_over_C3'] = ratio_rounds('Tloc', 'normal', 'J', 'C3', range(1, 4))
    for kind in ('x64', 'all'):
        output['paired'][f'Tloc_{kind}_F_over_C3'] = ratio_rounds('Tloc', kind, 'F', 'C3', range(1, 6))
    for kind in KINDS:
        folder = RAW / 'Tloc/1000000/runs' / f'{kind}_c3_9_dump'
        receipt, rows, _ = run('Tloc', f'{kind}_c3_9_dump')
        assert receipt['validation']['pass'] and receipt['dump']
        counts = [int(row['candidates']) for row in
                  csv.DictReader((folder / 'result.work.csv').open())]
        assert len(counts) == 24
        # Dump runs have more host work, so use only their candidate counts.
        output['tloc_candidates'][kind] = {
            'mean': statistics.mean(counts), 'min': min(counts),
            'max': max(counts), 'mean_fraction': statistics.mean(counts) / 1000000}
    cpu_audit = json.loads((HERE / 'local/holdout_artifacts/cpu_membership_audit.json').read_text())
    assert cpu_audit['dataset'] == 'Tloc' and cpu_audit['queries'] == 24
    assert cpu_audit['radii'] == list(KINDS)
    assert cpu_audit['checks'] == 216 and cpu_audit['mismatches'] == []
    output['cpu_membership_audit'] = cpu_audit
    (HERE / 'HOLDOUT_EVIDENCE.json').write_text(json.dumps(output, indent=2) + '\n')
    print('Audited', len(receipts), 'runs; binary', output['binary_sha256'])
    for name, result in output['paired'].items():
        print(name, 'median ratio', round(result['median_ratio'], 6),
              'numerator wins', result['numerator_wins'])


if __name__ == '__main__':
    main()
