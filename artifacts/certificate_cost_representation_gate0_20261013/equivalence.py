"""Exact rational fixtures for a bound identity; no training or performance."""
import argparse
import hashlib
import json
import random
import sys
from fractions import Fraction as F
from pathlib import Path

if sys.flags.optimize:
    raise SystemExit('Python optimized mode is unsupported: required checks must run')

HERE = Path(__file__).resolve().parent


def norm2(v):
    return sum((x*x for x in v), F(0))


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), F(0))


def distance(a, b):
    return sum(((x-y)*(x-y) for x, y in zip(a, b)), F(0))


def part(rng, width, numerators):
    out = [F(0)]*width
    for index, number in zip(rng.sample(range(width), len(numerators)), numerators):
        out[index] = F(number * rng.choice((-1, 1)), 16)
    return out


def check():
    contract = json.loads((HERE/'CONTRACT.json').read_text())
    spec = contract['cheap_test']
    # Dyadic coordinates realize the prescribed energies exactly, without sqrt.
    prototypes = {
        '0': ([16], []),
        '1/32': ([14, 6, 4], [2, 2]),
        '1/16': ([14, 6, 2, 2], [4]),
        '1/8': ([12, 8, 4], [4, 4]),
        '1/4': ([8, 8, 8], [8]),
    }
    rng = random.Random(spec['seed'])
    rows = []
    for d, k in spec['D_K_pairs']:
        for energy in spec['suffix_energy_fractions']:
            alpha = F(energy); major, minor = prototypes[energy]
            pairs = checks = tight = max_gap = equality_checks = 0
            for i in range(spec['pairs_per_shape_energy']):
                q = part(rng, k, major) + part(rng, d-k, minor)
                if i % 4 == 0:
                    x = q[:]
                elif i % 4 == 1:
                    x = q[:k] + [-v for v in q[k:]]
                elif i % 4 == 2:
                    x = part(rng, k, major) + q[k:]
                else:
                    x = part(rng, k, major) + part(rng, d-k, minor)
                for v in (q, x):
                    assert norm2(v) == 1
                    assert norm2(v[:k]) == 1-alpha and norm2(v[k:]) == alpha
                s = dot(q[:k], x[:k])
                upper = s+alpha
                prefix = distance(q[:k], x[:k])
                full = distance(q, x)
                assert dot(q, x) <= upper
                assert 2-2*upper == prefix
                assert full == 2-2*dot(q, x)
                assert prefix <= full <= prefix+4*alpha
                tight += int(prefix == full)
                max_gap += int(full-prefix == 4*alpha)
                for cutoff in (F(0), prefix, (prefix+full)/2, full):
                    reject_l2 = prefix > cutoff
                    reject_ip = upper < 1-cutoff/2
                    assert reject_l2 == reject_ip
                    assert not (reject_l2 and full <= cutoff)
                    if prefix == cutoff:
                        assert not reject_l2
                        equality_checks += 1
                    checks += 1
                pairs += 1
            assert tight > 0 and max_gap > 0 and equality_checks > 0
            rows.append(dict(D=d,K=k,suffix_energy=energy,pairs=pairs,
                             strict_range_certificate_checks=checks,
                             lower_bound_tight_witnesses=tight,
                             maximum_suffix_gap_witnesses=max_gap,
                             equality_continuation_checks=equality_checks,
                             bound_identity_mismatches=0,
                             synthetic_false_rejections=0))
    count = sum(x['pairs'] for x in rows)
    tests = sum(x['strict_range_certificate_checks'] for x in rows)
    assert count == 1600 and tests == 6400
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    return dict(experiment=spec['id'],complete=True,evidence_state='partial',
                scope='Exact arithmetic fixtures plus algebra; not trained features, CIFAR quality, numerical-library qualification or timing',
                arithmetic='stdlib Fraction',seed=spec['seed'],pairs=count,
                strict_range_certificate_checks=tests,rows=rows,
                universal_identity='Under the stated exact norm constraints,2-2*(dot_prefix+alpha)=prefix_squared_L2',
                loss_identity_established=False,original_metric_preservation_established=False,
                floating_point_implementation_qualified=False,
                training_processes=0,GPU_starts=0,CIFAR_queries=0,
                source_sha256=digest(HERE/'equivalence.py'),
                contract_sha256=digest(HERE/'CONTRACT.json'))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path)
    a = p.parse_args(); result = check()
    if a.output:
        with a.output.open('x') as f:
            f.write(json.dumps(result, indent=2)+'\n')
    print('PASS1600 rational descriptor pairs/6400 strict certificate checks; no training/GPU/CIFAR performance')
