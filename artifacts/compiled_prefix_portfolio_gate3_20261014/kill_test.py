"""Exact-rational CPV4 payload/source accounting only; no population or GPU."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import argparse
from fractions import Fraction as F
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def witness():
    n, d, prefix, k, item_bytes = 1000000, 960, 128, 4, 4
    raw = n * d * item_bytes
    first = n * prefix * item_bytes
    sidecars = k * first
    keeper = 1014828776
    ratio = F(raw + sidecars, raw)
    targets = {'keeper_strict_break_even': keeper, 'capacity_pass': 700000000,
               'router_source_pass': 750000000, 'strong_source': 650000000}
    fractions = {name: F(value - first, raw) for name, value in targets.items()}
    assert (raw, first, sidecars, raw+sidecars) == (3840000000, 512000000, 2048000000, 5888000000)
    assert ratio == F(23, 15) and ratio <= F(8, 5)
    assert (raw + sidecars) // n == 5888 and sidecars // n == 2048
    assert fractions == {'keeper_strict_break_even': F(20951199, 160000000),
                         'capacity_pass': F(47, 960), 'router_source_pass': F(119, 1920),
                         'strong_source': F(23, 640)}
    for name, value in targets.items():
        boundary = fractions[name]
        assert first + raw * boundary == value
        assert first + raw * (boundary-F(1, n)) < value < first + raw * (boundary+F(1, n))
    return {'scope': 'exact-rational design algebra;not measured survivors,allocations,quality or latency',
            'raw_vector_payload_bytes': raw, 'one_prefix_payload_bytes': first,
            'four_prefix_payload_bytes': sidecars, 'total_vector_payload_bytes': raw+sidecars,
            'payload_total_over_raw': str(ratio), 'extra_payload_over_raw': str(ratio-1),
            'insert_vector_write_bytes': 5888, 'extra_insert_vector_write_bytes': 2048,
            'survivor_fraction_thresholds': {name: str(value) for name, value in fractions.items()},
            'keeper_equality_is_not_strict_improvement': True,
            'full_raw_fallback_rereads_prefix_coordinates': True,
            'real_dataset_loaded': False, 'population_starts': 0, 'GPU_starts': 0}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True, help='Fresh task-owned JSON file')
    a = p.parse_args()
    result = witness()
    result['contract_sha256'] = hashlib.sha256((HERE/'CONTRACT.json').read_bytes()).hexdigest()
    result['executed_source_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with a.out.open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False)
        f.write('\n')
    print('PASS: rational accounting only;not portfolio capacity,exactness or novelty admission')


if __name__ == '__main__':
    main()
