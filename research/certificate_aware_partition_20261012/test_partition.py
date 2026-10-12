#!/usr/bin/env python3
"""Small deterministic regression check, not evidence for real-data G1-G4."""
import numpy as np
from partitions import pca_partition, audit, decide, metrics, PARTITIONS


def main():
    z = np.zeros((1000, 8))
    p, stats = pca_partition(z, depth=2)
    assert np.array_equal(p, np.arange(1000)) and stats['sort_count'] == 11
    assert stats['axis_counts'][0] == 11
    audit(p, n=1000, depth=2)
    z[:, 7] = np.arange(1000)[::-1]; p, _ = pca_partition(z, depth=2)
    assert np.array_equal(p, np.arange(1000)[::-1])
    try: audit(np.zeros(1000, dtype=np.int32), n=1000, depth=2)
    except AssertionError: pass
    else: raise AssertionError('duplicate ownership accepted')
    assert metrics(500, 100, 1000)['alignment_efficiency'] == 5 / 9
    def rows(values):
        return [dict(partition=p, level=l, k=8, alignment_efficiency=values[pi][li])
                for pi, p in enumerate(PARTITIONS) for li, l in enumerate([3, 4, 5])]
    assert decide(rows([[.1] * 3, [.2] * 3, [.61, .7, .9]]))['decision'] == 'CERTIFICATE_AWARE_PARTITION_SUPPORTED'
    assert decide(rows([[.1] * 3, [.2] * 3, [.2, .29, .7]]))['decision'] == 'LEAF_ONLY_PARTITION_EFFECT'
    assert decide(rows([[.1] * 3, [.2] * 3, [.2, .29, .5]]))['decision'] == 'LINEAR_PARTITION_REPRESENTATION_KILLED'
    assert decide(rows([[.1] * 3, [.2] * 3, [.35, .45, .5]]))['decision'] == 'PARTIAL_CO_DESIGN_SIGNAL'
    assert decide(rows([[.4] * 3, [.4] * 3, [.35, .45, .5]]))['decision'] == 'PARTIAL_CO_DESIGN_SIGNAL'
    assert decide(rows([[.5] * 3, [.5] * 3, [.35, .45, .5]]))['decision'] == 'INSUFFICIENT_EVIDENCE'
    print('PASS: deterministic spread/value ties, ownership, nested sizes, metrics and decision precedence')


if __name__ == '__main__': main()
