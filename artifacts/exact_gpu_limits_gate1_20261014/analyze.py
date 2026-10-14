"""Exact gates over public histograms and conditional models; writes a fresh output only."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
import hashlib
import importlib.util
import json
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rational(value):
    return {'numerator': value.numerator, 'denominator': value.denominator, 'decimal': float(value)}


def gate(original, pair, global_sum):
    assert original > 0 and pair > 0 and global_sum > 0
    state = ('B1_SATURATED' if 10 * pair >= 7 * original else
             'MODERATE_HEADROOM' if 10 * pair >= 4 * original else 'LARGE_HEADROOM')
    no_go = 10 * pair < 4 * original or 5 * global_sum < 3 * original
    return state, no_go


def model_b2(c):
    n, db, keeper = c['N'], c['full_coordinate_bytes_per_query'], c['keeper_source_bytes_per_query']
    rows = []
    for bits in c['B2']['metadata_bits_per_vector']:
        metadata = n * bits // 8
        required = Fraction(db + metadata - keeper, db)
        rows.append({'bits_per_vector': bits, 'bytes_per_vector': bits // 8,
                     'metadata_bytes': metadata, 'break_even_rejection_fraction': rational(required),
                     'strong_90_percent_barrier': required >= Fraction(9, 10),
                     'strict_win': 'f must be strictly greater than break-even'})
    return {'model': c['B2'], 'source_bytes_not_DRAM': True, 'rows': rows,
            'state': 'B2_BARRIER_STRONG' if all(r['strong_90_percent_barrier'] for r in rows) else 'B2_BARRIER_NOT_SUPPORTED',
            'achievable_representation': 'UNKNOWN', 'unknown_costs': ['query/control/output', 'updates', 'metadata access selectivity', 'cache/sectors', 'fallback implementation']}


def model_b3(c):
    db, keeper = c['full_coordinate_bytes_per_query'], c['keeper_source_bytes_per_query']
    product = Fraction(db - keeper, keeper)
    rates, windows = list(range(100, 10001, 100)), list(range(50, 2001, 50))
    source = lambda rate, us: Fraction(db * 1000000, 1000000 + rate * us)
    examples = []
    for rate, us in [(100, 500), (500, 500), (1000, 500), (5000, 500), (10000, 500), (5000, 100), (10000, 2000)]:
        value = source(rate, us)
        examples.append({'lambda_qps': rate, 'window_us': us, 'ideal_B': rational(Fraction(1000000 + rate * us, 1000000)),
                         'source_bytes_per_query': rational(value), 'over_keeper': rational(value / keeper),
                         'strict_source_win': value < keeper})
    corner = source(5000, 500)
    return ({'model': c['B3'], 'lambda_qps': rates, 'window_us': windows,
             'source_bytes_per_query_matrix': [[float(source(rate, us)) for rate in rates] for us in windows],
             'exact_generation': 'DB*1000000/(1000000+lambda_qps*window_us)',
             'keeper_source_bytes': keeper, 'break_even_lambda_times_W_seconds': rational(product),
             'gate_best_corner': {'lambda_qps': 5000, 'window_us': 500, 'bytes': rational(corner)},
             'state': 'B3_FROZEN_REGION_BARRIER' if corner >= keeper else 'B3_BARRIER_NOT_SUPPORTED',
             'universal_scheduler_bound': False, 'complete_SLA_or_dynamic_E2E': 'UNKNOWN'},
            {'rows': examples, 'break_even_qps_at_500us': rational(product * 2000),
             'break_even_qps_at_100us': rational(product * 10000),
             'break_even_window_us_at_5000qps': rational(product * 200),
             'rounding': 'Use exact rational thresholds for gates; displayed qps are not rounded admission thresholds.'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--results', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    c, data = load(HERE / 'CONTRACT.json'), load(a.results)
    assert data['complete'] and data['contract_sha256'] == sha(HERE / 'CONTRACT.json')
    assert data['GPU_starts'] == 0 and data['pairs'] == c['N'] * len(c['qids'])
    for name, digest in c['parents'].items():
        assert sha(a.repo / name) == digest, ('changed parent', name)
    spec = importlib.util.spec_from_file_location('parent_histogram_analysis', a.repo / 'artifacts/exact_representation_gate1_20261012/analyze.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    stats = old.histogram_stats
    totals = {name: [0] * (c['D'] + 1) for name in ('original', 'pair_nominal', 'pair_safe', 'global_nominal', 'global_safe')}
    rows, raw = [], {}
    for i, record in enumerate(data['records']):
        assert record['query_index'] == i and record['qid'] == c['qids'][i]
        assert record['N'] == c['N'] and record['D'] == c['D']
        assert record['full_score_bit_mismatches'] == record['safe_false_rejections'] == 0
        assert record['hits'] >= 0
        for name, hist in record['histograms'].items():
            assert name in totals and len(hist) == c['D'] + 1 and hist[0] == 0
            assert all(type(v) is int and v >= 0 for v in hist) and sum(hist) == c['N']
            assert hist[-1] >= record['hits']
            totals[name] = [x + y for x, y in zip(totals[name], hist)]
        assert set(record['histograms']) == set(totals)
        raw.update(record.get('raw', {}))
        rows.append({k: v for k, v in record.items() if k != 'diagnostic_wall_seconds_not_search_latency'})
    summary = {name: {**stats(hist), 'dimension_sum': sum(i * n for i, n in enumerate(hist)), 'histogram': hist} for name, hist in totals.items()}
    original = summary['original']['dimension_sum']
    assert original == c['original_ideal_dimension_sum']
    assert sum(r['hits'] for r in rows) == 6590
    pair, global_sum = summary['pair_nominal']['dimension_sum'], summary['global_nominal']['dimension_sum']
    safe_pair, safe_global = summary['pair_safe']['dimension_sum'], summary['global_safe']['dimension_sum']
    nominal_gate, nominal_no_go = gate(original, pair, global_sum)
    guarded_gate, guarded_no_go = gate(original, safe_pair, safe_global)
    stable = (nominal_gate, nominal_no_go) == (guarded_gate, guarded_no_go)
    b2 = model_b2(c)
    b3, examples = model_b3(c)
    if not stable:
        final = 'UNCLASSIFIED'
    elif nominal_no_go:
        final = 'NO_GO_LIMITS_THESIS'
    elif nominal_gate == 'B1_SATURATED' and 5 * global_sum >= 4 * original and b2['state'] == 'B2_BARRIER_STRONG' and b3['state'] == 'B3_FROZEN_REGION_BARRIER':
        final = 'GO_LIMITS_THESIS'
    else:
        final = 'UNCLASSIFIED'
    a.out.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        dest = a.out / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with dest.open('x') as f:
            json.dump(value, f, indent=2, allow_nan=False)
            f.write('\n')

    write('b1_information_floor/ORIGINAL_ORDER.json', {'scope': 'ideal original-order per-coordinate strict crossing, not checkpoint reads', **summary['original'],
          'p50': summary['original']['median'], 'true_hits': 6590, 'pairs': c['N'] * 32})
    for stem, kind in [('PAIR_ORACLE', 'pair'), ('QUERY_GLOBAL_ORACLE', 'global')]:
        write('b1_information_floor/' + stem + '.json', {'scope': c['B1']['pair_specific' if kind == 'pair' else 'query_global'],
              'nominal': summary[kind + '_nominal'], 'guarded': summary[kind + '_safe'],
              'p50_nominal': summary[kind + '_nominal']['median'], 'true_hits': 6590, 'pairs': c['N'] * 32})
    headroom = {'pairs': c['N'] * 32, 'B1_state': nominal_gate, 'B1_no_go': nominal_no_go, 'guarded_state': guarded_gate,
                'guarded_B1_no_go': guarded_no_go, 'gate_stability': stable,
                'primary_original_ideal_mean': rational(Fraction(original, c['N'] * 32)),
                'secondary_checkpoint_mean': rational(Fraction(c['keeper_source_bytes_per_query'], 4 * c['N'])),
                'pair_over_original': rational(Fraction(pair, original)), 'global_over_original': rational(Fraction(global_sum, original)),
                'pair_coordinate_savings_fraction': rational(Fraction(original - pair, original)),
                'global_coordinate_savings_fraction': rational(Fraction(original - global_sum, original)),
                'global_fraction_of_pair_headroom_removed': rational(Fraction(original - global_sum, original - pair)) if original != pair else None,
                'pair_over_checkpoint': rational(Fraction(pair * 4, 32 * c['keeper_source_bytes_per_query'])),
                'guard_changed_pairs': {'pair': sum(r['pair_audit_nominal_hit_cross_guard_fallback_difference'][2] for r in rows),
                                        'global': sum(r['global_audit_nominal_hit_cross_guard_fallback_difference'][2] for r in rows)},
                'source_model_not_traffic_or_speedup': True}
    write('b1_information_floor/HEADROOM.json', headroom)
    write('b2_metadata_floor/BREAK_EVEN.json', b2)
    write('b2_metadata_floor/PARETO.json', {'scope': 'conditional cost plane, not achievable representation frontier',
          'f_denominator': 'all objects; true-hit reads already included in complete raw fallback',
          'rows': [{'bits_per_vector': r['bits_per_vector'], 'rejection_fraction_percent': f,
                    'source_bytes_per_query': r['metadata_bytes'] + c['full_coordinate_bytes_per_query'] * (100 - f) // 100}
                   for r in b2['rows'] for f in range(101)], 'observed_points': 0})
    write('b3_online_reuse/BREAK_EVEN_SURFACE.json', b3)
    write('b3_online_reuse/EXAMPLES.json', examples)
    write('evidence/SCALARS.json', {'complete': True, 'contract_sha256': data['contract_sha256'], 'pairs': data['pairs'],
          'records': rows, 'CPU_workers': data['CPU_workers'], 'GPU_starts': 0})
    write('evidence/RAW_MANIFEST.json', {'files': raw, 'private_only': True, 'contains_dataset': False,
          'scope': 'per-pair dimensions, query-order and nonhit-mean arrays; hashes only'})
    write('evidence/ANALYSIS.json', {'final': final, 'B1': nominal_gate, 'B2': b2['state'], 'B3': b3['state'],
          'gate_stability': stable, 'GPU_starts': 0, 'population_pairs': data['pairs'],
          'results_sha256': sha(a.results), 'parent_histogram_helper_sha256': sha(a.repo / 'artifacts/exact_representation_gate1_20261012/analyze.py')})
    print(json.dumps({'final': final, 'B1': nominal_gate, 'pair_mean': summary['pair_nominal']['mean'],
                      'global_mean': summary['global_nominal']['mean'], 'guard_changed': headroom['guard_changed_pairs']}))


if __name__ == '__main__':
    main()
