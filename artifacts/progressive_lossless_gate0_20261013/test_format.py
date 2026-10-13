#!/usr/bin/env python3
"""Executable corner, prefix interval and exact range qualification; no GPU."""
import argparse
import math
from pathlib import Path
import random
import struct
import sys
import tempfile

import numpy as np

from run import encode_and_recover, load, pack_rows, require, search, validate


def value(u):
    return struct.unpack('<f', struct.pack('<I', u))[0]


def inverse(k):
    return k ^ 0x80000000 if k & 0x80000000 else k ^ 0xffffffff


def mapping(u):
    return u ^ 0xffffffff if u & 0x80000000 else u ^ 0x80000000


def reference(x, q):
    out = []
    for row in x:
        total = 0.0
        for a, b in zip(row, q):
            delta = float(a) - float(b)
            square = delta * delta
            total = total + square
        out.append(total)
    return np.array(out, dtype='<f8')


def check(lib):
    rng = random.Random(20261013)
    corners = [0, 0x80000000, 1, 0x80000001, 0x007fffff, 0x807fffff, 0x00800000,
               0x80800000, 0x3f800000, 0xbf800000, 0x7f7fffff, 0xff7fffff,
               0x7f800000, 0xff800000, 0x7fc00000, 0xffc00000, 0x7f800001, 0xff800001]
    patterns = corners + [rng.getrandbits(32) for _ in range(10007)]
    patterns.extend([0] * ((-len(patterns)) % 5))
    raw = np.array(patterns, dtype='<u4').reshape(-1, 5)
    layers = pack_rows(raw)
    restored = np.empty_like(raw)
    require(lib.recover(*(v.ctypes.data for v in layers), len(raw), 5, restored.ctypes.data) == 0, 'recovery failed')
    require(np.array_equal(raw, restored), 'corner/random bit reconstruction differs')
    require(all(np.all(v[:, -1] & 15 == 0) for v in layers[:2]), 'odd-D unused nibble differs')
    # Exercise the on-disk header, offsets and whole-file recovery, not just in-memory packing.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        fixture = np.array(corners[:12] + [0, 0, 0], dtype='<u4').reshape(3, 5)
        data = tmp / 'finite.bin'
        data.write_bytes(struct.pack('<iii', 5, 3, 2) + fixture.tobytes())
        q, stored, receipt = encode_and_recover(data, tmp / 'encoded.bin', lib, 3, 5, [0])
        require(receipt['checked_coordinates'] == 15 and receipt['bit_mismatches'] == 0, 'file recovery differs')
        require(receipt['raw_mapping_closed_before_search'], 'raw mapping remains open')
        require(receipt['representation_bytes'] == 64 + 3 * (3 + 3 + 5 + 10), 'odd-D file size differs')
        validate(*search(lib, stored, q[0], 0.), reference(fixture.view('<f4'), q[0]), 0.)
        for v in stored:
            v._mmap.close()
        data2 = tmp / 'nonfinite.bin'
        data2.write_bytes(struct.pack('<iii', 1, 1, 2) + struct.pack('<I', 0x7f800000))
        try:
            encode_and_recover(data2, tmp / 'inadmissible.bin', lib, 1, 1, [0])
        except RuntimeError as exc:
            require('nonfinite database' in str(exc), 'unexpected admission failure')
        else:
            raise RuntimeError('nonfinite object admission did not fail')
    intervals = 0
    bounds = np.empty(2, dtype='<f8')
    for width in (4, 8, 16):
        mask = (1 << (32 - width)) - 1
        for prefix in range(1 << width):
            key = prefix << (32 - width)
            lo = max(key, 0x00800000)
            hi = min(key | mask, 0xff7fffff)
            rc = lib.interval_key(key, width, bounds.ctypes.data)
            if lo > hi:
                require(rc == 1, 'nonfinite-only prefix must be empty')
            else:
                require(rc == 0, 'finite prefix unexpectedly empty')
                expected = [value(inverse(lo)), value(inverse(hi))]
                require(np.array_equal(bounds, expected), 'prefix endpoints differ')
                # Endpoints must be tight in key space, with the only numeric tie at signed zero.
                require(lo >> (32 - width) == hi >> (32 - width) == prefix, 'prefix coverage differs')
                require(bounds[0] <= bounds[1], 'reversed numerical interval')
            intervals += 1
    for u in patterns:
        key = mapping(u)
        require(inverse(key) == u, 'non-bijective mapping')
        rc = lib.interval_key(key, 32, bounds.ctypes.data)
        if math.isfinite(value(u)):
            require(rc == 0 and bounds[0] == bounds[1] == value(u), 'full key endpoint differs')
            for width in (4, 8, 16):
                require(lib.interval_key(key, width, bounds.ctypes.data) == 0, 'finite value has empty prefix')
                require(bounds[0] <= value(u) <= bounds[1], 'finite value not covered')
        else:
            require(rc == 1, 'nonfinite full key admitted as a finite interval')
    finite = np.array([u for u in patterns if math.isfinite(value(u))], dtype='<u4')
    finite = finite[:(len(finite) // 31) * 31].reshape(-1, 31).view('<f4')
    query = np.array(finite[0], dtype='<f4', copy=True)
    oracle = reference(finite, query)
    for cutoff in [0.0, float(np.median(oracle)), float(oracle.max())]:
        validate(*search(lib, pack_rows(finite.view('<u4')), query, cutoff), oracle, cutoff)
    # Equality continues to exact decode; duplicate coordinates do not collapse row occurrences.
    x = np.array([[0., 0., 0.], [-0., 0., -0.], [1., 0., 0.], [1., 0., 0.], [-1., 0., 0.], [2., 0., 0.]], dtype='<f4')
    q = np.zeros(3, dtype='<f4')
    oracle = reference(x, q)
    for cutoff, hits in [(0.0, 2), (math.nextafter(1.0, -math.inf), 2), (1.0, 5),
                         (math.nextafter(1.0, math.inf), 5), (4.0, 6)]:
        result = validate(*search(lib, pack_rows(x.view('<u4')), q, cutoff), oracle, cutoff)
        require(result['hits'] == hits, 'equality/duplicate count differs')
    empty_q = np.full(3, 100., dtype='<f4')
    result = validate(*search(lib, pack_rows(x.view('<u4')), empty_q, 0.0), reference(x, empty_q), 0.0)
    require(result['hits'] == 0, 'empty range differs')
    q[0] = np.nan
    layers = pack_rows(x.view('<u4'))
    bits = np.zeros(len(x), dtype='u1'); lower = np.zeros((3, len(x))); full = np.zeros(len(x))
    rc = lib.search(*(v.ctypes.data for v in layers), q.ctypes.data, len(x), len(q), 1., bits.ctypes.data, lower.ctypes.data, full.ctypes.data)
    require(rc == 2, 'nonfinite query must fail admission')
    print(f'PASS: {raw.size} bit patterns (NaN payloads/inf/signed zero/subnormals); '
          f'{intervals} exhaustive 4/8/16 prefixes; full-key and ordered-FP64 range fixtures')


if __name__ == '__main__':
    require(not sys.flags.optimize, 'run without Python -O')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library', required=True, type=Path)
    args = p.parse_args()
    check(load(args.library.resolve()))
