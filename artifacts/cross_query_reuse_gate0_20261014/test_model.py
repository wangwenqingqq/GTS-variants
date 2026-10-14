"""Runnable timer/cap, ownership, estimator and analytic regression checks."""
if not __debug__:
    raise SystemExit('Optimized Python disables mandatory checks; run without -O/PYTHONOPTIMIZE.')
import math
from replay import batches, analytic, classify, DB_BYTES, WINDOW_PS as W


def main():
    assert list(batches([0])) == [(0, 1, W)]
    assert list(batches([0, W - 1, W, W + 1])) == [(0, 3, W), (3, 4, 2 * W + 1)]
    assert list(batches([0] * 17)) == [(0, 8, 0), (8, 16, 0), (16, 17, W)]
    assert list(batches([0, W + 1])) == [(0, 1, W), (1, 2, 2 * W + 1)]
    for rate in [100, 500, 1000, 5000]:
        a = analytic(rate)
        assert math.isclose(sum(a['batch_probabilities']), 1, abs_tol=1e-14)
        assert 1 <= a['mean_B'] <= 1 + rate / 2000
        assert a['query_weighted_bytes'] > 1_000_000_000
    # Batches 1 and 8: query weighting and batch weighting are different.
    query_weighted, batch_weighted = 2 * DB_BYTES / 9, (DB_BYTES + DB_BYTES / 8) / 2
    assert query_weighted < batch_weighted
    # Conditional batch size but expensive source: NO_GO has priority.
    assert classify(35, 10, W)['label'] == 'NO_GO_CROSS_QUERY_REUSE'
    assert classify(64, 8, W + 1)['label'] == 'NO_GO_CROSS_QUERY_REUSE'
    print('PASS: timer equality, cap, no loss/duplication, cost weights, NO_GO priority, analytic bound')


if __name__ == '__main__':
    main()
