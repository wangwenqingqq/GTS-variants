"""Read-only input and workload feasibility audit; never repairs a frozen case."""
import argparse, hashlib, json
from pathlib import Path
import numpy as np

SPECS = {
    'sift': ('fbin/sift1m_base.fbin', 'fbin/sift1m_query.fbin', 'fbin', 2),
    'gist': ('fbin/gist1m_base.fbin', 'fbin/gist1m_query.fbin', 'fbin', 2),
    'deep': ('fbin/deep1m_base.fbin', 'fbin/deep1m_query.fbin', 'fbin', 2),
    'tloc': ('T-loc/tloc.txt', 'T-loc/tloc_qid.txt', 'text', 2),
    'word': ('word/word.txt', 'word/word_qid.txt', 'text', 6),
    'protein': ('dna_barcode/protein.txt', 'dna_barcode/protein_qid.txt', 'text', 6),
    'chembl': ('chembl/chembl_50k.txt', 'chembl/chembl_50k_qid.txt', 'text', 8),
}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()

def load(root, name):
    base, query, fmt, metric = SPECS[name]
    if fmt == 'fbin':
        n, dim = np.fromfile(root/base, dtype='<i4', count=2)
        x = np.memmap(root/base, dtype='<f4', mode='r', offset=8, shape=(int(n), int(dim)))
        nq, qdim = np.fromfile(root/query, dtype='<i4', count=2)
        assert dim == qdim
        q = np.memmap(root/query, dtype='<f4', mode='r', offset=8, shape=(int(nq), int(dim)))
        assert (root/base).stat().st_size == 8 + 4*int(n)*int(dim)
        assert (root/query).stat().st_size == 8 + 4*int(nq)*int(dim)
        qids = None
    else:
        with (root/base).open(encoding='latin1') as f:
            dim, n, kind = map(int, f.readline().split()); assert kind == metric
            rows = [line.rstrip('\r\n') for line in f]
        assert len(rows) == n
        if metric == 6:
            x = rows
            assert max(map(len, rows)) <= dim
        else:
            x = np.array([np.fromstring(line, sep=' ', dtype=np.float32) for line in rows])
            assert x.shape == (n, dim)
            if metric == 8: assert np.isin(x, [0, 1]).all()
        ids = np.loadtxt(root/query, dtype=np.int64, skiprows=1, ndmin=1)
        assert len(ids) == int((root/query).read_text().splitlines()[0])
        assert (ids >= 0).all() and (ids < n).all()
        qids = ids.tolist(); q = [x[i] for i in ids] if metric == 6 else x[ids]
    return x, q, qids, int(dim)

def rowkey(row):
    if isinstance(row, str): return row.encode('latin1')
    a = np.asarray(row, dtype='<f4').copy()
    assert np.isfinite(a).all()
    a[a == 0] = 0  # Treat +0 and -0 as equal features.
    return a.tobytes()

def capacity(n, arrivals, length, ratio, k=8):
    weights = list(map(int, ratio.split(':')))
    assert length % sum(weights) == 0
    ins, dele, que = [length*w//sum(weights) for w in weights]
    reasons = []
    if ins > arrivals: reasons.append('fresh_arrival_exhausted')
    if n-arrivals+ins-dele < k: reasons.append('final_active_cardinality_below_k')
    return dict(inserts=ins, deletes=dele, queries=que, reasons=reasons,
                status='contract-infeasible' if reasons else 'capacity-feasible')

def main():
    p = argparse.ArgumentParser(); p.add_argument('--data-root', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); a = p.parse_args()
    result = {'schema': 1, 'seed': 20261026, 'query_policy': 'native-unmodified', 'datasets': {}}
    for name, (base, query, fmt, metric) in SPECS.items():
        x, q, ids, dim = load(a.data_root, name); n = len(x); na = n//10
        qkeys = {rowkey(row) for row in q}
        matches = []
        for i, row in enumerate(x):
            if rowkey(row) in qkeys: matches.append(i)
        split = np.random.Generator(np.random.PCG64(20261026)).permutation(n)
        arrival_ids = set(map(int, split[:na]))
        ds = dict(n=n, dim=dim, metric=metric, arrival_rows=na, initial_base_rows=n-na,
                  corpus={'file': base, 'sha256': sha(a.data_root/base)},
                  query={'file': query, 'sha256': sha(a.data_root/query), 'count': len(q), 'id_based': ids is not None},
                  split_permutation_sha256=hashlib.sha256(split.astype('<i8').tobytes()).hexdigest(),
                  query_feature_overlap_rows=len(matches),
                  overlap_in_arrival=sum(i in arrival_ids for i in matches),
                  overlap_in_base=sum(i not in arrival_ids for i in matches),
                  input_status='input-contract-blocked' if matches else 'input-pass',
                  loads=[])
        for length in (10000, 100000):
            for ratio in ('4:4:2', '8:1:1', '1:8:1'):
                for order in ('random', 'skew'):
                    for k in ((8, 10) if metric == 2 else (8,)):
                        ds['loads'].append(dict(length=length, ratio=ratio, order=order, k=k,
                                                **capacity(n, na, length, ratio, k)))
        result['datasets'][name] = ds
        print(name, n, 'query overlaps', len(matches), flush=True)
    with a.out.open('x') as f: json.dump(result, f, indent=2); f.write('\n')

if __name__ == '__main__': main()
