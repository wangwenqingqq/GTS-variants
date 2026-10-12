"""Deterministic balanced ownership and predeclared causal-test decision."""
import numpy as np

LEVELS = {3: 1000, 4: 100, 5: 10}
PARTITIONS = ['GTS_ORIGINAL', 'RANDOM_BALANCED', 'PCA_BALANCED']


def pca_partition(z, depth=5):
    """Ten-way max-spread splits in frozen coordinates; never consumes queries."""
    n = len(z)
    assert n == 10 ** (depth + 1) and z.shape[1] == 8
    perm = np.arange(n, dtype=np.int32)
    stats = dict(sort_count=0, sorted_object_occurrences=0,
                 explicit_peak_scratch_bytes=0, axis_counts=[0] * 8)
    for level in range(depth):
        size = n // (10 ** level)
        for start in range(0, n, size):
            ids = perm[start:start + size]
            coords = z[ids]
            axis = int(np.argmax(coords.max(axis=0) - coords.min(axis=0)))
            order = np.lexsort((ids, coords[:, axis]))
            replacement = ids[order]
            perm[start:start + size] = replacement
            stats['sort_count'] += 1
            stats['sorted_object_occurrences'] += size
            stats['axis_counts'][axis] += 1
            # Array storage only: allocator/sort-internal scratch is not included.
            stats['explicit_peak_scratch_bytes'] = max(stats['explicit_peak_scratch_bytes'],
                coords.nbytes + order.nbytes + replacement.nbytes)
    return perm, stats


def audit(perm, n=1000000, depth=5):
    assert perm.shape == (n,) and np.issubdtype(perm.dtype, np.integer)
    assert np.array_equal(np.sort(perm), np.arange(n)), 'invalid ownership'
    for level in range(1, depth + 1):
        size = n // 10 ** level
        assert size * 10 ** level == n
        blocks = perm.reshape(10 ** level, size)
        parent = perm.reshape(10 ** (level - 1), size * 10)
        assert np.array_equal(blocks.reshape(parent.shape), parent)
    return dict(status='PASS', objects=n, unique_objects=n, depth=depth,
                balanced=True, nested=True, exactly_one_leaf=True)


def metrics(remaining, truth_remaining, total):
    assert 0 <= truth_remaining <= remaining <= total
    return dict(truth_residual=truth_remaining / total,
                certificate_residual=remaining / total,
                alignment_efficiency=(total - remaining) / (total - truth_remaining),
                full_scan_work_reduction=1 - remaining / total)


def decide(rows):
    a = {(r['partition'], r['level']): r['alignment_efficiency']
         for r in rows if r['k'] == 8}
    gains = {l: dict(P2_minus_P0=a[(PARTITIONS[2], l)] - a[(PARTITIONS[0], l)],
                         P2_minus_P1=a[(PARTITIONS[2], l)] - a[(PARTITIONS[1], l)])
             for l in LEVELS}
    supported = [l for l in (3, 4) if a[(PARTITIONS[2], l)] >= .60 and
                 gains[l]['P2_minus_P0'] >= .30 and gains[l]['P2_minus_P1'] >= .20]
    ancestor = max(a[(PARTITIONS[2], l)] for l in (3, 4))
    if supported:
        decision = 'CERTIFICATE_AWARE_PARTITION_SUPPORTED'
    elif a[(PARTITIONS[2], 5)] >= .60 and ancestor < .30:
        decision = 'LEAF_ONLY_PARTITION_EFFECT'
    elif ancestor < .30:
        decision = 'LINEAR_PARTITION_REPRESENTATION_KILLED'
    elif any(a[(PARTITIONS[2], l)] >= .30 and min(gains[l].values()) > 0 for l in (3, 4)):
        decision = 'PARTIAL_CO_DESIGN_SIGNAL'
    else:
        decision = 'INSUFFICIENT_EVIDENCE'
    return dict(decision=decision, gains=gains, supported_levels=supported,
                K2_random_close_by_level={l: abs(gains[l]['P2_minus_P1']) < .10 for l in LEVELS})
