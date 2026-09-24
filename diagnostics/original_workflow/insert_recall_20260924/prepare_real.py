#!/usr/bin/env python3
"""Prepare exact-insertion probes from real fvecs for GTS's short-valued L2 path."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def prepare(source, out, n, scale, radius, binary):
    assert not out.exists()
    dim = int(np.fromfile(source, dtype='<i4', count=1)[0])
    assert dim in (128, 960) and source.stat().st_size % (4 * (dim + 1)) == 0
    raw = np.memmap(source, dtype='<f4', mode='r').reshape(-1, dim + 1)
    assert n <= len(raw) and np.all(raw[:n, 0].view('<i4') == dim)
    values = raw[:n, 1:]
    assert np.isfinite(values).all()
    scaled = np.rint(values * scale)
    assert scaled.min() >= -32768 and scaled.max() <= 32767
    if scale == 1:
        assert np.array_equal(values, scaled), 'SIFT values must be exact integers'
    vectors = scaled.astype(np.int16)

    sources = [0, n//4, n//2, 3*n//4, n-1, 31, n//3, n//5, n//7, 0]
    ops = []
    for source_id in sources:
        ops += [(0, source_id), (2, source_id)]
    ops += [(2, n), (2, n+4), (2, 0), (2, n-1), (1, n),
            (2, 0), (2, n//4), (0, n//2), (2, n//2)]
    base_hits = {}
    wide = vectors.astype(np.int32) if radius else None
    for s in set(sources):
        if radius:
            delta = wide - wide[s]
            d2 = np.einsum('ij,ij->i', delta, delta, dtype=np.int64)
            ids = np.flatnonzero(d2 <= radius*radius)
            base_hits[s] = {int(i): math.sqrt(int(d2[i])) for i in ids}
        else:
            base_hits[s] = {int(i): 0.0 for i in np.flatnonzero(np.all(vectors == vectors[s], axis=1))}
    active, buffered, rebuilds, deleted, queries = [], 0, 0, False, []
    for op, (flag, idx) in enumerate(ops):
        if flag == 0:
            active.append((idx, op))
            buffered += 1
            if buffered == 10:
                buffered = 0
                rebuilds += 1
        elif flag == 1:
            active.pop(idx-n)
            deleted = True
        else:
            qsource = idx if idx < n else active[idx-n][0]
            hits = dict(base_hits[qsource])
            inserted = []
            for j, (s, token) in enumerate(active):
                delta = vectors[s].astype(np.int32) - vectors[qsource].astype(np.int32)
                d2 = int(np.dot(delta.astype(np.int64), delta.astype(np.int64)))
                if d2 <= radius*radius:
                    inserted.append((n+j, token))
                    hits[n+j] = math.sqrt(d2)
            queries.append({'op_index': op, 'query_id': idx,
                            'phase': 'after_rebuild' if rebuilds else 'before_rebuild',
                            'after_delete': deleted, 'rebuilds': rebuilds,
                            'buffered': buffered, 'live_count': n+len(active),
                            'hits': hits, 'inserted_ids': [i for i, _ in inserted],
                            'inserted_tokens': [t for _, t in inserted]})

    (out/'fixtures').mkdir(parents=True)
    (out/'bin').mkdir()
    (out/'runs').mkdir()
    (out/'logs').mkdir()
    with (out/'fixtures/data.txt').open('w', buffering=8 << 20) as f:
        f.write(f'{dim} {n} 2\n')
        for start in range(0, n, 10000):
            np.savetxt(f, vectors[start:start+10000], fmt='%d')
    updates = out/'fixtures/realdata.updates'
    updates.write_text(str(len(ops))+'\n'+''.join(f'{flag} {idx}\n' for flag, idx in ops))
    (out/'bin/gts_h6_audit').symlink_to(binary.resolve())
    manifest = {'dataset_source': str(source), 'source_sha256': sha(source),
                'n': n, 'dimensions': dim, 'metric': 'integer L2 after quantization',
                'quantization_scale': scale, 'data_sha256': sha(out/'fixtures/data.txt'),
                'cases': {'realdata': {'radius': radius, 'operations': len(ops),
                           'updates_sha256': sha(updates),
                           'expected_counts': [len(q['hits']) for q in queries],
                           'queries': queries}}}
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'n': n, 'dim': dim, 'queries': len(queries),
                      'expected_hits': sum(map(lambda q: len(q['hits']), queries)),
                      'inserted_pairs': sum(map(lambda q: len(q['inserted_ids']), queries)),
                      'data_sha256': manifest['data_sha256']}), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('out', type=Path)
    p.add_argument('--n', type=int, required=True)
    p.add_argument('--scale', type=int, required=True)
    p.add_argument('--radius', type=int, default=0)
    p.add_argument('--binary', type=Path, required=True)
    a = p.parse_args()
    prepare(a.source, a.out, a.n, a.scale, a.radius, a.binary)
