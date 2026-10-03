#!/usr/bin/env python3
"""Fail-closed six-round summary; missed quality anchors are never wins."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random
import statistics as st


def read(path):
    return json.loads(path.read_text())


def percentile(xs, p):
    xs = sorted(xs)
    i = (len(xs)-1)*p
    j = int(i)
    return xs[j] + (xs[min(j+1, len(xs)-1)]-xs[j])*(i-j)


def distribution(xs):
    assert len(xs) == 6 and all(math.isfinite(x) and x > 0 for x in xs)
    return {'raw_ms': xs, 'p10_ms': percentile(xs, .1), 'median_ms': st.median(xs),
            'p90_ms': percentile(xs, .9), 'arithmetic_mean_ms': st.mean(xs),
            'geometric_mean_ms': math.exp(st.mean(map(math.log, xs)))}


def ratio_stats(gts, ivf, paired=True):
    assert len(gts) == len(ivf) == 6
    rng = random.Random(20261003)
    logs = [math.log(a/b) for a, b in zip(gts, ivf)]
    if paired:
        samples = [math.exp(st.mean(rng.choices(logs, k=6))) for _ in range(20000)]
    else:
        samples = [math.exp(st.mean(map(math.log, rng.choices(gts, k=6))) -
                            st.mean(map(math.log, rng.choices(ivf, k=6)))) for _ in range(20000)]
    result = {'geomean_ratio': math.exp(st.mean(logs)),
              'bootstrap_95': [percentile(samples, .025), percentile(samples, .975)],
              'marginal_median_ratio': st.median(gts)/st.median(ivf),
              'method': ('paired' if paired else 'independent') +
                        ' process log-ratio bootstrap; 20000 resamples; seed20261003'}
    if paired:
        result.update({'process_wins_ivf': sum(a > b for a, b in zip(gts, ivf)),
                       'raw_paired_ratios': [a/b for a, b in zip(gts, ivf)],
                       'order_split_geomean': {
                           'GTS_then_IVF': math.exp(st.mean(logs[::2])),
                           'IVF_then_GTS': math.exp(st.mean(logs[1::2]))}})
    return result


def clean(root, label):
    folder = root/'runs'/label
    receipt = read(folder/'receipt.json')
    assert receipt['runtime_valid'] and receipt['exit_code'] == 0
    assert receipt['stop_reason'] is None, label
    assert not read(folder/'before.json')['apps'].strip(), label
    assert not read(folder/'after.json')['apps'].strip(), label
    assert all(not c['foreign'] for c in read(folder/'checks.json')), label
    return receipt


def quality_summary(qualities):
    assert len(qualities) == 6
    assert all(len(q['per_query_recall']) == 256 for q in qualities)
    assert all(all(0 <= x <= 1 for x in q['per_query_recall']) and
               math.isclose(st.mean(q['per_query_recall']), q['recall_tie_aware'], abs_tol=1e-14)
               for q in qualities)
    return {'tie_aware_min': min(q['recall_tie_aware'] for q in qualities),
            'deterministic_min': min(q['recall_deterministic'] for q in qualities),
            'complete_query_fraction_min': min(q['complete_query_fraction'] for q in qualities),
            'field_gate_pass': all(q['distance_tolerance_pass'] for q in qualities),
            'max_squared_distance_error_scale1': max(q['squared_distance_max_relative_scale1'] for q in qualities),
            'missing_slots_max': max(q['missing_neighbor_slots'] for q in qualities)}


def analyze(root):
    contract = read(root/'CONTRACT.json')
    assert contract['timing']['formal_pairs'] == 6
    frozen = read(root/'FROZEN_CONFIG.json')
    queries = read(root/'QUERY_SETS.json')
    frozen_hash = hashlib.sha256((root/'FROZEN_CONFIG.json').read_bytes()).hexdigest()
    for dataset in ('GIST', 'Deep'):
        assert queries[dataset]['frozen_config_sha256'] == frozen_hash
        for phase in ('development','final'):
            path = root/queries[dataset][f'{phase}_file']
            assert hashlib.sha256(path.read_bytes()).hexdigest() == queries[dataset][f'{phase}_sha256']
    expected_order = []
    for r in range(1, 7):
        for dataset in (('GIST','Deep') if r % 2 else ('Deep','GIST')):
            for method in (('gts','ivf') if r % 2 else ('ivf','gts')):
                if method == 'ivf': expected_order.append(f'formal_r{r}_ivf_{dataset}')
                else:
                    cases = [(k,b) for k in (8,32) for b in (1,32)]
                    for k,b in (cases if r % 2 else cases[::-1]):
                        expected_order.append(f'formal_r{r}_gts_{dataset}_k{k}_b{b}')
    observed_order = [line.split()[1] for line in (root/'formal_console.log').read_text().splitlines()
                      if line.startswith('PASS formal_')]
    assert observed_order == expected_order, 'Missing or reordered process observations'
    rows = []
    for dataset in ('GIST', 'Deep'):
        ivf_rounds = []
        for r in range(1, 7):
            label = f'formal_r{r}_ivf_{dataset}'
            clean(root, label)
            ivf_rounds.append(read(root/f'{label}.json')['rows'])
        for a in frozen[dataset]['anchors']:
            assert a['status'] == 'selected_from_development'
            gts_times, gts_quality, ivf_times, ivf_quality = [], [], [], []
            for r in range(1, 7):
                label = f'formal_r{r}_gts_{dataset}_k{a["K"]}_b{a["B"]}'
                receipt = clean(root, label)
                assert receipt['binary_sha256'] == read(root/'PREFLIGHT.json')['gts_binary_sha256']
                values = list(csv.DictReader((root/f'{label}.csv').open()))
                assert len(values) == 1 and int(values[0]['sample']) == 0
                gts_times.append(float(values[0]['total_ms']))
                gts_quality.append(read(root/f'{label}.quality.json'))
                matches = [v for v in ivf_rounds[r-1]
                           if all(v[k] == a[k] for k in ('K', 'B', 'nlist', 'nprobe'))]
                assert len(matches) == 1 and matches[0]['sample'] == 0
                ivf_times.append(matches[0]['total_ms'])
                ivf_quality.append(matches[0]['quality'])
            gq, iq = quality_summary(gts_quality), quality_summary(ivf_quality)
            admitted = all(q['tie_aware_min'] >= a['anchor'] and q['field_gate_pass'] for q in (gq, iq))
            rows.append({'dataset': dataset, **a, 'gts': distribution(gts_times),
                         'ivf': distribution(ivf_times), 'gts_quality': gq, 'ivf_quality': iq,
                         'same_anchor_admitted': admitted,
                         'ratio': ratio_stats(gts_times, ivf_times) if admitted else None})
    supplement = []
    if (root/'EXHAUSTIVE_CONTROL.json').is_file():
        control = read(root/'EXHAUSTIVE_CONTROL.json')
        for dataset in ('GIST', 'Deep'):
            for k in (8, 32):
                for b in (1, 32):
                    base = next(v for v in rows if v['dataset'] == dataset and v['K'] == k and v['B'] == b and v['anchor'] == 1)
                    times, qualities = [], []
                    for r in range(1, 7):
                        label = f'control_r{r}_ivf_{dataset}'
                        clean(root, label)
                        values = read(root/f'{label}.json')['rows']
                        matches = [v for v in values if v['K'] == k and v['B'] == b]
                        assert len(matches) == 1 and matches[0]['nlist'] == matches[0]['nprobe'] == 1024
                        times.append(matches[0]['total_ms']); qualities.append(matches[0]['quality'])
                    iq = quality_summary(qualities)
                    admitted = iq['tie_aware_min'] == base['gts_quality']['tie_aware_min'] == 1 and iq['field_gate_pass'] and base['gts_quality']['field_gate_pass']
                    supplement.append({'dataset': dataset, 'K': k, 'B': b, 'nlist': 1024, 'nprobe': 1024,
                                       'gts': base['gts'], 'ivf': distribution(times), 'ivf_quality': iq,
                                       'same_anchor_admitted': admitted,
                                       'ratio': ratio_stats(base['gts']['raw_ms'], times, paired=False) if admitted else None,
                                       'scope': control['comparison_scope']})
    return {'denominator': 'Host-ready total milliseconds per 256-query pass; six processes per method/configuration',
            'primary': rows, 'exhaustive_supplement': supplement}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--check-only', action='store_true', help='Recompute without replacing the collection summary')
    args = parser.parse_args()
    result = analyze(args.root)
    if args.check_only:
        def same(a,b):
            if isinstance(a,dict):return a.keys()==b.keys() and all(same(a[k],b[k]) for k in a)
            if isinstance(a,list):return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
            if isinstance(a,(int,float)) and not isinstance(a,bool):return math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)
            return a==b
        assert same(result,read(args.root/'SUMMARY.json')), 'Stored/recomputed summary differs'
    else:
        (args.root/'SUMMARY.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PASS six-round receipts, quality, raw order and summary')


if __name__ == '__main__':
    main()
