"""Rational formula identity/nonidentity witness only; no real population or GPU."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def witness():
    # Two contiguous32-coordinate blocks. Only one coordinate in each is active.
    q = [F(0)] * 64
    q[0], q[32] = F(2), F(1)
    zero = [F(0)] * 64
    low, high = zero.copy(), zero.copy()
    low[32], high[32] = F(-10), F(10)
    rows = [low, high]
    mu = [sum(row[j] for row in rows) / len(rows) for j in range(64)]
    nu = [sum(row[j] ** 2 for row in rows) / len(rows) for j in range(64)]
    expanded = [q[j]**2 - 2*q[j]*mu[j] + nu[j] for j in range(64)]
    decomposed = [(q[j]-mu[j])**2 + nu[j]-mu[j]**2 for j in range(64)]
    empirical = [sum((q[j]-row[j])**2 for row in rows) / len(rows) for j in range(64)]
    assert expanded == decomposed == empirical
    mean_only = [sum((q[j]-mu[j])**2 for j in range(b*32, (b+1)*32)) for b in range(2)]
    expected = [sum(expanded[b*32:(b+1)*32]) for b in range(2)]
    rank = lambda values: sorted(range(len(values)), key=lambda b: (-values[b], b))
    assert mean_only == [F(4), F(1)] and expected == [F(4), F(101)]
    assert rank(mean_only) == [0, 1] and rank(expected) == [1, 0]
    # Equal total block variance only adds a common ranking offset.
    equal_variance = [v + 32 for v in mean_only]
    assert rank(equal_variance) == rank(mean_only)
    return {'arithmetic': 'exact rational,not a FP64 numerical-safety test',
            'fixture': 'synthetic2 vectors x64 coordinates,2 contiguous32-d blocks',
            'identity': 'E[(q-x)^2]=(q-mu)^2+variance',
            'empirical_expanded_decomposed_equal': True,
            'heterogeneous_variance': {'mean_only_block_scores': list(map(str, mean_only)),
                                       'moment_block_scores': list(map(str, expected)),
                                       'mean_only_order': rank(mean_only), 'moment_order': rank(expected)},
            'constant_block_variance_ranking_equal': True,
            'interpretation': 'The score can change rankings;no literal equivalence to a mean-only rule is asserted. It changes the priority statistic,not the partial-distance certificate or zone-visitation mechanism.',
            'real_dataset_loaded': False, 'CPU_population_starts': 0, 'GPU_starts': 0,
            'candidate_quality_latency_traffic': 'NOT_RUN'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True, help='Fresh task-owned JSON path')
    a = p.parse_args()
    result = witness()
    result['contract_sha256'] = hashlib.sha256((HERE/'CONTRACT.json').read_bytes()).hexdigest()
    result['executed_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print('PASS: rational identity and nonidentity witness;not a population or novelty pass')


if __name__ == '__main__':
    main()
