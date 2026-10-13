"""Runnable CPU numerical, tie, interval-tail and accounting checks; no GPU."""
import argparse
from pathlib import Path
import numpy as np
from model import sector_model, warp_sectors
from replay import (crossings, encode, exact_k, functions, interval, table,
                    validate_crossings, validate_interval)


def ordered(x, q):
    result = []
    for row in x:
        score = 0.
        for a, b in zip(row, q):
            delta = float(a) - float(b)
            score = score + delta * delta
        result.append(score)
    return np.array(result, dtype='<f8')


def check(binary):
    assert warp_sectors(0, 0, 0) == 4
    assert warp_sectors(0, 0, 0, base=4) == 5
    for row in (0, 1, 7, 1000039):
        for start, end in ((0, 128), (128, 256), (256, 512), (512, 960)):
            assert all(warp_sectors(row, start, it) == 4 for it in range((end-start)//32))
    model = sector_model()
    assert model['coordinate_sector_headroom_fraction'] == 0 and model['decision'] == 'KILL_M1'
    f, g = functions(binary)
    rng = np.random.default_rng(2026101304)
    x = (rng.integers(-1024, 1025, size=(65, 960)).astype('<f4') / 1024).astype('<f4')
    x[1:10] = x[0]  # More than k identical occurrences, including self match.
    x[:, 17] = .25  # Constant-dimension encoding must remain safe.
    code, edges = encode(x)
    assert code.dtype == np.uint8 and code.nbytes == 65*256
    assert np.isneginf(edges[:, 0]).all() and np.isposinf(edges[:, -1]).all()
    # Tail codes cover future outside-envelope values without changing learned edges.
    outside = np.array((-4., 4.))
    assert outside[0] <= edges[0, 1] and outside[1] >= edges[0, -2]
    for q in (x[0].copy(), x[24].copy(), np.full(960, 2., '<f4')):
        reference = ordered(x, q)
        _, t0 = exact_k(reference); _, t1 = exact_k(reference[:32])
        full, dims, bc = crossings(g, x, q, t0, t1)
        stats = validate_crossings(full, dims, bc, reference, (t0, t1))
        for threshold in (t0, float(np.median(reference)), float(np.max(reference)), 0.):
            out = interval(f, x, q, code, edges, threshold)
            good = validate_interval(out, reference, threshold)
            assert good['false_negative'] == good['false_positive'] == 0
            corrupt = [v.copy() for v in out]; corrupt[2][0] = corrupt[0][0] + 1
            try:
                validate_interval(corrupt, reference, threshold)
                raise RuntimeError('corrupted lower bound was accepted')
            except AssertionError:
                pass
        assert all(sum(s['required_dims_histogram']) == len(x) for s in stats)
    # Strict equality and cutoff ties must be retained, even when more than k tie.
    reference = ordered(x, x[0]); ids, cutoff = exact_k(reference)
    assert cutoff == 0. and ids.tolist() == list(range(8))
    full, dims, bc = crossings(g, x, x[0].copy(), 0., 0.)
    assert (dims[0][:10] == 960).all()
    assert np.all(table(x[0].astype('<f8'), edges) >= 0.)
    try:
        crossings(g, x, x[0].copy(), -1., 0.)
        raise RuntimeError('invalid threshold was accepted')
    except AssertionError:
        pass
    print('PASS CPU boundary/tie/interval-tail/sector checks; GPU starts=0')


if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--binary', type=Path, required=True)
    check(p.parse_args().binary)
