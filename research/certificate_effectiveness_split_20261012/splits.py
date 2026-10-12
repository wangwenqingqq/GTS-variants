"""Query-independent proposals and immediate-child oracle scoring."""
import sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'projection_certificate_20261011'))
from projection_math import endpoints, prefix_bounds
NAMES = ['MAX_SPREAD'] + ['PC' + str(i) for i in range(1, 9)] + ['CYCLIC', 'TWO_AXIS', 'RADIAL']
PARTITIONS = ['GTS_ORIGINAL', 'PCA_BALANCED', 'ORACLE_ALL8', 'ORACLE_HARD6']
LEVELS = {3: 1000, 4: 100, 5: 10}


def centroid(z, ids):
    ordered = z[np.sort(ids)]
    return np.array([np.add.accumulate(ordered[:, j])[-1] / len(ids) for j in range(8)])


def candidates(z, ids, depth):
    """No query, score, threshold, or label is accepted by this function."""
    assert len(ids) % 10 == 0 and z.shape[1] == 8
    coords = z[ids]
    axes = np.lexsort((np.arange(8), -(coords.max(0) - coords.min(0))))
    axis = int(axes[0]); second = int(axes[1])
    out = np.empty((12, len(ids)), dtype=np.int32)
    for proposal, dim in [(0, axis)] + [(i + 1, i) for i in range(8)] + [(9, depth % 8)]:
        out[proposal] = ids[np.lexsort((ids, coords[:, dim]))]
    out[10] = ids[np.lexsort((ids, coords[:, second], coords[:, axis]))]
    c = centroid(z, ids); radius = np.zeros(len(ids))
    for j in range(8):
        delta = coords[:, j] - c[j]
        np.add(radius, np.multiply(delta, delta), out=radius)
    out[11] = ids[np.lexsort((ids, radius))]
    return out


def score_proposals(z, proposals, queries, u, scores=None):
    size = proposals.shape[1] // 10
    lo = np.empty((120, 8), dtype=np.float32); hi = np.empty_like(lo)
    truth = np.empty((8, 120)) if scores is not None else None
    for s in range(12):
        grouped = z[proposals[s]].reshape(10, size, 8)
        lo[s * 10:(s + 1) * 10], hi[s * 10:(s + 1) * 10] = endpoints(grouped.min(1), grouped.max(1))
        if scores is not None:
            for qi in range(8):
                truth[qi, s * 10:(s + 1) * 10] = scores[qi, proposals[s]].reshape(10, size).min(1)
    bounds = np.array([prefix_bounds(lo, hi, q)[8] for q in queries])
    if truth is not None:
        assert np.all(bounds <= np.sqrt(truth)), 'candidate bound exceeds truth'
        assert not np.any((bounds > u[:, None]) & (np.sqrt(truth) <= u[:, None])), 'unsafe candidate prune'
    counts = (bounds.reshape(8, 12, 10) > u[:, None, None]).sum(2).T * size
    widths = hi.astype(np.float64) - lo.astype(np.float64)
    diagonal = np.sqrt((widths * widths).sum(1)).reshape(12, 10)
    return counts, diagonal


def decision(rows):
    # Gates use exact count ratios; binary subtraction must not flip a 25 pp tie.
    from fractions import Fraction
    a = {(r['partition'], r['level']): r for r in rows}
    def value(partition, level, hard=False):
        row = a[(partition, level)]; prefix = 'hard_' if hard else ''
        n = 6000000 if hard else 8000000
        if prefix + 'certificate_remaining_objects' in row:
            return Fraction(n - row[prefix + 'certificate_remaining_objects'],
                            n - row[prefix + 'truth_retained_objects'])
        return Fraction(str(row['hard_alignment' if hard else 'alignment']))
    high = [l for l in (3, 4) if value('ORACLE_HARD6', l, True) >= Fraction(3, 5) and
            value('ORACLE_HARD6', l, True) - value('PCA_BALANCED', l, True) >= Fraction(1, 4)]
    strong = [l for l in high if value('ORACLE_HARD6', l, True) >= Fraction(7, 10) and
              value('ORACLE_ALL8', l) >= Fraction(3, 5)]
    low = max(value('ORACLE_HARD6', l, True) for l in (3, 4)) < Fraction(2, 5)
    easy = low and any(value('ORACLE_ALL8', l) >= Fraction(3, 5) for l in (3, 4))
    verdict = ('CERTIFICATE_EFFECTIVENESS_CONSTRUCTION_SUPPORTED' if strong else
               'SPLIT_OBJECTIVE_HEADROOM_HIGH' if high else 'EASY_QUERY_ONLY' if easy else
               'LINEAR_SPLIT_OBJECTIVE_HEADROOM_LOW' if low else 'INSUFFICIENT_EVIDENCE')
    return dict(decision=verdict, promotion_levels=high, strong_levels=strong,
                K2_small_hard_gain_both_ancestors=all(value('ORACLE_HARD6', l, True) -
                    value('PCA_BALANCED', l, True) < Fraction(1, 10) for l in (3, 4)))
