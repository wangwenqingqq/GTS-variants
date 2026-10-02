#!/usr/bin/env python3
"""Export every Faiss IVFFlat list ID in list order for full GPU enumeration."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import faiss
import numpy as np

ROOT = Path(__file__).resolve().parent
BASE = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
TRAIN_SEED = 2026100207
TRAIN_COUNT = 200000


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', choices=('GIST', 'Deep'), required=True)
    p.add_argument('--nlist', type=int, default=1024)
    a = p.parse_args()
    path = BASE / f'data/{a.dataset}/1000000/fixtures/data.f32bin'
    with path.open('rb') as f:
        d, n, _ = np.fromfile(f, dtype='<i4', count=3)
    assert int(n) == 1_000_000
    source = np.memmap(path, dtype='<f4', mode='r', offset=12, shape=(n, d))
    faiss.omp_set_num_threads(16)
    resource = faiss.StandardGpuResources()
    config = faiss.GpuIndexIVFFlatConfig()
    config.use_cuvs = False
    index = faiss.GpuIndexIVFFlat(resource, int(d), a.nlist, faiss.METRIC_L2, config)
    sample_ids = np.random.default_rng(TRAIN_SEED).choice(n, TRAIN_COUNT, replace=False)
    train = np.asarray(source[sample_ids], dtype=np.float32, order='C')
    start = time.perf_counter()
    index.train(train)
    train_s = time.perf_counter() - start
    start = time.perf_counter()
    index.add(source)
    add_s = time.perf_counter() - start
    start = time.perf_counter()
    cpu = faiss.index_gpu_to_cpu(index)
    lists = cpu.invlists
    chunks = []
    sizes = []
    for list_id in range(a.nlist):
        size = lists.list_size(list_id)
        sizes.append(size)
        if size:
            chunks.append(faiss.rev_swig_ptr(lists.get_ids(list_id), size).astype('<i4', copy=True))
    order = np.concatenate(chunks)
    assert len(order) == n and np.array_equal(np.sort(order), np.arange(n, dtype=np.int32))
    export_s = time.perf_counter() - start
    target = ROOT / f'fixtures/{a.dataset}_ivf_n{a.nlist}_order.i32'
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(order.tobytes())
    print(json.dumps({'dataset': a.dataset, 'nlist': a.nlist,
                      'train_seed': TRAIN_SEED, 'train_samples': TRAIN_COUNT,
                      'train_s': train_s, 'add_s': add_s, 'export_s': export_s,
                      'records': int(len(order)), 'min_list_size': min(sizes),
                      'max_list_size': max(sizes),
                      'nonempty_lists': sum(bool(x) for x in sizes),
                      'order_sha256': hashlib.sha256(target.read_bytes()).hexdigest()},
                     sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
