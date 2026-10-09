"""Frozen synthetic cases and integer-distance live-multiset oracle."""
import csv
import functools
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

PARENT = Path(__file__).resolve().parent.parent / 'par_range_update'
sys.path.insert(0, str(PARENT))
from fixtures import data_bytes, events_bytes, full_operations, boundary_operations, DATA_SHA, EVENT_SHA


def mixed(ops):
    count = 0; result = []
    for flag, index in ops:
        if flag == 2:
            flag = 2 + count % 2; count += 1
        result.append((flag, index))
    return result


def sparse():
    queries = [(2, 0), (3, 0)]
    return (queries + [(1, 0)] * 999 + queries + [(1, 0)] + queries
            + [(0, 0)] * 3 + queries + [(1, 1)] + queries + [(1, 1)] + queries
            + [(0, 0)] * 9 + queries + [(1, 0)] * 10 + queries + [(0, 0)] * 10 + queries)


def validate_contract(data, ops, radius, k):
    assert data.shape == (1000, 128) and np.all(np.isfinite(data))
    assert np.all((data >= 0) & (data <= 255)) and np.all(data == np.floor(data))
    assert radius in (0, 10000) and k in (8, 32) and 0 < len(ops) <= 12000
    alive = [True] * 1000; buffer = 0; queries = 0
    for flag, index in ops:
        assert flag in (0, 1, 2, 3) and isinstance(index, (int, np.integer)) and index >= 0
        live = sum(alive)
        if flag == 1:
            assert index < live + buffer
            if index >= live: buffer -= 1
            else: alive[[i for i, keep in enumerate(alive) if keep][index]] = False
        else:
            assert index < len(alive)
            if flag == 0:
                buffer += 1
                if buffer == 10: alive = [True] * (live + buffer); buffer = 0
            else: queries += 1
        assert len(alive) + buffer <= 1024 and sum(alive) + buffer <= 1010
    assert 0 < queries <= 10000


def generate(root):
    full = mixed(full_operations()); edge = mixed(boundary_operations())
    zeros = ('128 1000 2\n' + (' '.join(['0'] * 128) + '\n') * 1000).encode()
    specs = [('legacy', data_bytes(), full_operations(), 0, 8),
             ('full8', data_bytes(), full, 0, 8), ('full32', data_bytes(), full, 0, 32),
             ('boundary0', data_bytes(), edge, 0, 8), ('boundary10000', data_bytes(), edge, 10000, 32),
             ('ties8', zeros, edge, 0, 8), ('ties32', zeros, edge, 0, 32),
             ('sparse8', data_bytes(), sparse(), 0, 8), ('sparse32', data_bytes(), sparse(), 0, 32)]
    cases = {}
    for name, raw, ops, radius, k in specs:
        path = root / name; path.mkdir(parents=True)
        (path / 'data.txt').write_bytes(raw); (path / 'events.txt').write_bytes(events_bytes(ops))
        data = np.loadtxt(path / 'data.txt', skiprows=1, dtype=np.int64)
        validate_contract(data, ops, radius, k)
        cases[name] = dict(radius=radius, k=k, events=len(ops), queries=sum(f >= 2 for f, _ in ops),
                           range_queries=sum(f == 2 for f, _ in ops), knn_queries=sum(f == 3 for f, _ in ops),
                           data_sha256=hashlib.sha256(raw).hexdigest(),
                           events_sha256=hashlib.sha256(events_bytes(ops)).hexdigest())
    assert cases['legacy']['data_sha256'] == DATA_SHA and cases['legacy']['events_sha256'] == EVENT_SHA
    return cases


def oracle(data, ops, radius, k, direct=False):
    data = np.asarray(data, dtype=np.int64)
    if direct:
        sq = ((data[:, None, :] - data[None, :, :]) ** 2).sum(2)
    else:
        norms = (data * data).sum(1); sq = norms[:, None] + norms[None, :] - 2 * data @ data.T
    assert sq.min() == 0 and sq.max() < 2 ** 24
    base = list(range(len(data))); alive = [True] * len(base); buffer = []
    queries = []; states = []; rebuilds = 0
    for step, (flag, index) in enumerate(ops):
        before = (len(base), len(buffer)); rebuilt = False
        if flag == 0:
            buffer.append(base[index])
            if len(buffer) == 10:
                base = [v for v, keep in zip(base, alive) if keep] + buffer
                alive = [True] * len(base); buffer = []; rebuilt = True; rebuilds += 1
        elif flag == 1:
            positions = [i for i, keep in enumerate(alive) if keep]
            if index < len(positions): alive[positions[index]] = False
            else: buffer.pop(index - len(positions))
        else:
            assert flag in (2, 3)
            live = [v for v, keep in zip(base, alive) if keep] + buffer
            scores = sq[base[index], live]
            if flag == 2:
                ids = np.flatnonzero(scores <= radius ** 2).astype('<i4')
                fields = np.sqrt(scores[ids].astype(np.float64)).astype('<f4')
            else:
                chosen = np.lexsort((np.arange(len(live)), scores))[:k]
                ids = np.full(k, -1, dtype='<i4'); fields = np.full(k, np.inf, dtype='<f4')
                ids[:len(chosen)] = chosen; fields[:len(chosen)] = np.sqrt(scores[chosen].astype(np.float64)).astype('<f4')
            queries.append((step, index, len(base), len(buffer), flag, ids, fields))
        states.append((*before, len(base), len(buffer), rebuilt))
    return queries, states, rebuilds


@functools.lru_cache(maxsize=None)
def expected(path, radius, k):
    path = Path(path); data = np.loadtxt(path / 'data.txt', skiprows=1, dtype=np.int64)
    ops = np.loadtxt(path / 'events.txt', skiprows=1, dtype=np.int64).tolist()
    validate_contract(data, ops, radius, k)
    return ops, oracle(data, ops, radius, k)


def check(prefix, case_path, metadata, mode, knn_mode=None):
    prefix = str(prefix); ops, (queries, states, rebuilds) = expected(str(case_path), metadata['radius'], metadata['k'])
    ids = np.fromfile(prefix + '.ids.i32', dtype='<i4'); fields = np.fromfile(prefix + '.dist.f32', dtype='<f4')
    with open(prefix + '.queries.csv') as stream: rows = list(csv.DictReader(stream))
    assert len(rows) == len(queries); offset = 0
    for row, (step, qid, n, buffer, flag, want_ids, want_fields) in zip(rows, queries):
        assert [int(row[v]) for v in ('step', 'qid', 'tree_size', 'buffer', 'offset', 'count')] == [step, qid, n, buffer, offset, len(want_ids)]
        count = len(want_ids); got_ids = ids[offset:offset+count]; got_fields = fields[offset:offset+count]
        if flag == 3:
            assert got_ids.tobytes() == want_ids.tobytes() and got_fields.tobytes() == want_fields.tobytes(), (prefix, step, 'ordered kNN')
        else:
            actual = dict(zip(map(int, got_ids), map(bytes, got_fields)))
            want = dict(zip(map(int, want_ids), map(bytes, want_fields)))
            assert len(actual) == count and actual == want, (prefix, step, 'range fields')
        offset += count
    assert offset == len(ids) == len(fields)
    assert Path(prefix + '.ids.i32').stat().st_size == Path(prefix + '.dist.f32').stat().st_size == 4 * offset
    with open(prefix + '.ops.csv') as stream: rows = list(csv.DictReader(stream))
    assert len(rows) == len(states)
    for step, (row, state) in enumerate(zip(rows, states)):
        assert int(row['step']) == step and int(row['flag']) == ops[step][0]
        assert tuple(int(row[v]) for v in ('base_before', 'buffer_before', 'base_after', 'buffer_after')) == state[:4]
        assert (float(row['rebuild_ms']) > 0) == state[4]
        assert float(row['ack_ms']) >= float(row['rebuild_ms']) >= 0
    def read(suffix): return json.loads(Path(prefix + suffix).read_text())
    region = read('.region.json'); summary = read('.summary.json')
    assert region['mode'] == {'PAR_STRONG': 1, 'NATIVE': 0}[mode] and region['final_owned_bytes'] == 0
    assert region['refreshes'] == (rebuilds + 1 if mode == 'PAR_STRONG' else 0)
    assert summary['observe'] and not summary['tree_audit'] and summary['results'] == offset
    assert np.isfinite(summary['trace_ms']) and summary['trace_ms'] > 0
    suffixes = ['.ids.i32', '.dist.f32', '.queries.csv', '.ops.csv', '.summary.json', '.region.json']
    unified = None
    if knn_mode:
        unified = read('.unified.json'); suffixes += ['.unified.json']
        assert unified['knn_mode'] == knn_mode and unified['k'] == metadata['k']
        assert unified['queries'] == metadata['knn_queries'] and unified['refreshes'] == rebuilds + 1
        assert unified['final_owned_bytes'] == 0 and unified['allocations'] == 10
        assert len(unified['refresh_ms']) == rebuilds + 1 and all(t > 0 for t in unified['refresh_ms'])
    return dict(queries_checked=len(queries), events_checked=len(states), rebuilds=rebuilds,
                summary=summary, region=region, unified=unified,
                outputs={s: hashlib.sha256(Path(prefix + s).read_bytes()).hexdigest() for s in suffixes})


def self_test():
    # Scalar difference-squared reference is independent of the norm/dot identity.
    data = np.array([[0, 0], [2, 1], [2, 1], [9, 3]], dtype=np.int64)
    ops = [(3, 0), (1, 0), (3, 0), (0, 1), (0, 1), (3, 1), (1, 3), (3, 1)] + [(0, 1)] * 9 + [(3, 0), (2, 0)]
    for radius in (0, 10000):
        for k in (8, 32):
            left = oracle(data, ops, radius, k); right = oracle(data, ops, radius, k, direct=True)
            assert left[1:] == right[1:]
            for a, b in zip(left[0], right[0]):
                assert a[:5] == b[:5] and a[5].tobytes() == b[5].tobytes() and a[6].tobytes() == b[6].tobytes()
    valid = np.zeros((1000, 128), dtype=np.int64)
    for ops in ([(4, 0)], [(1, 1000)], [(3, 1000)], [(0, -1)], [(2, 0)] + [(0, 0)] * 11):
        try: validate_contract(valid, ops, 0, 8)
        except AssertionError: pass
        else: raise AssertionError(('malformed contract accepted', ops))
    validate_contract(valid, sparse(), 0, 32)
    q, _, rebuilt = oracle(valid, sparse(), 0, 32)
    assert rebuilt == 2 and any(flag == 3 and np.all(ids == -1) for _, _, _, _, flag, ids, _ in q)
    print('CPU_PROTOCOL_PASS', flush=True)


if __name__ == '__main__': self_test()
