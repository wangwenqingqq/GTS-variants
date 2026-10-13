#!/usr/bin/env python3
"""Independent ordered NumPy reference; native fixtures before population work."""
import argparse
import ctypes as C
from pathlib import Path

import numpy as np


def load(path):
    lib = C.CDLL(str(Path(path).resolve()))
    lib.oracle_scores.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.c_int,
                                  C.c_int, C.c_void_p, C.c_void_p, C.c_void_p]
    lib.oracle_scores.restype = C.c_int
    lib.subset_scores.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.c_int,
                                  C.c_void_p, C.c_int, C.c_void_p]
    lib.subset_scores.restype = C.c_int
    return lib


def oracle(lib, x, q, k=128):
    assert x.dtype == q.dtype == np.dtype('<f4') and x.flags.c_contiguous
    assert q.flags.c_contiguous and q.shape == (x.shape[1],)
    outputs = [np.full(len(x), np.nan, dtype='<f8') for _ in range(3)]
    rc = lib.oracle_scores(x.ctypes.data, q.ctypes.data, len(x), x.shape[1], k,
                           *(v.ctypes.data for v in outputs))
    if rc:
        raise ValueError(('oracle_scores', rc))
    return outputs


def subset(lib, x, q, indices):
    assert x.dtype == q.dtype == np.dtype('<f4') and x.flags.c_contiguous
    assert q.flags.c_contiguous and q.shape == (x.shape[1],)
    indices = np.ascontiguousarray(indices, dtype='<u2')
    out = np.full(len(x), np.nan, dtype='<f8')
    rc = lib.subset_scores(x.ctypes.data, q.ctypes.data, len(x), x.shape[1],
                           indices.ctypes.data, len(indices), out.ctypes.data)
    if rc:
        raise ValueError(('subset_scores', rc))
    return out


def golden(x, q, k):
    delta = x.astype(np.float64)-q.astype(np.float64)
    terms = delta*delta
    # Stable sorting independently verifies native partitioning and tie ownership.
    chosen = np.argsort(-terms, axis=1, kind='stable')[:, :k]
    mask = np.zeros(x.shape, dtype=bool)
    np.put_along_axis(mask, chosen, True, axis=1)
    first, top, full = (np.zeros(len(x), dtype='<f8') for _ in range(3))
    for j in range(x.shape[1]):
        full += terms[:, j]
        if j < k:
            first += terms[:, j]
        top += np.where(mask[:, j], terms[:, j], 0.)
    return first, top, full


def same_bits(a, b):
    return np.array_equal(a.view('<u8'), b.view('<u8'))


def fixtures(lib):
    rng = np.random.default_rng(20261013)
    checked = 0
    for d in (1, 3, 16, 129, 960):
        k = min(128, d)
        x = rng.normal(0, .1, (53, d)).astype('<f4')
        q = x[0].copy()
        x[1] = q  # Duplicate occurrence, not a deduplicated member.
        x[2] = 0.; x[3] = -0.
        x[4] = np.nextafter(np.float32(0), np.float32(1))
        x[5] = np.finfo(np.float32).max
        x[6] = -np.finfo(np.float32).max
        for got, want in zip(oracle(lib, x, q, k), golden(x, q, k)):
            assert same_bits(got, want), ('golden bits', d)
        indices = np.sort(rng.choice(d, k, replace=False)).astype('<u2')
        got = subset(lib, x, q, indices)
        expected = np.zeros(len(x), dtype='<f8')
        for j in indices:
            delta = x[:, j].astype(np.float64)-float(q[j])
            expected += delta*delta
        assert same_bits(got, expected)
        full = golden(x, q, k)[2]
        assert np.all(got <= full)
        for cutoff in (0., float(got[10]), float(full[11]), 1e-300, 1e80):
            assert not np.any((got > cutoff) & (full <= cutoff))
        for bad in (indices[::-1].copy(), np.full(k, d, dtype='<u2')):
            if len(bad) == 1 and int(bad[0]) < d:
                continue
            try:
                subset(lib, x, q, bad)
            except ValueError:
                pass
            else:
                raise AssertionError('invalid subset admitted')
        checked += len(x)
    # Equal contributions must select exactly k despite extensive ties.
    x = np.ones((7, 960), dtype='<f4'); q = np.zeros(960, dtype='<f4')
    a, b, full = oracle(lib, x, q)
    assert np.all(a == 128) and np.all(b == 128) and np.all(full == 960)
    assert not np.any(b > 128), 'strict radius equality must survive'
    for target in ('data', 'query'):
        for value in (np.nan, np.inf, -np.inf):
            xx = x.copy(); qq = q.copy()
            if target == 'data': xx[0, 0] = value
            else: qq[0] = value
            try:
                oracle(lib, xx, qq)
            except ValueError:
                pass
            else:
                raise AssertionError('nonfinite input admitted')
    try:
        oracle(lib, x, q, 0)
    except ValueError:
        pass
    else:
        raise AssertionError('zero budget admitted')
    print(f'PASS: {checked+7} rows; independent stable-top-k/ordered bits, subset safety, ties, duplicates, equality, signed zero, subnormal, extreme finite, nonfinite and index guards')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--library', type=Path, required=True)
    fixtures(load(p.parse_args().library))
