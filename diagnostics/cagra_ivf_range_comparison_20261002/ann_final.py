#!/usr/bin/env python3
"""One independent P6 final process: native top-K and strict range refinement."""
import argparse
import json
from pathlib import Path
import struct
import time

import cupy as cp
import numpy as np

from range_refine import KERNEL, collect_ordered, oracle, quality

ROOT = Path(__file__).resolve().parent
BASE = Path('/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928')
P0 = Path('/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001')
BITS = {'GIST': {'half': 0x3f34a3d8, 'normal': 0x3fb4a3d8},
        'Deep': {'normal': 0x3f8a3818}}
TRAIN_SEED = 2026100207
TRAIN_COUNT = 200000


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--method', choices=('cagra', 'faiss'), required=True)
    p.add_argument('--dataset', choices=('GIST', 'Deep'), required=True)
    p.add_argument('--k', type=int, required=True)
    p.add_argument('--nlist', type=int, default=0)
    p.add_argument('--nprobe', type=int, default=0)
    p.add_argument('--round', type=int, required=True)
    a = p.parse_args()
    assert 1 <= a.round <= 6
    data_path = BASE / f'data/{a.dataset}/1000000/fixtures/data.f32bin'
    with data_path.open('rb') as f:
        d, n, _ = np.fromfile(f, dtype='<i4', count=3)
    assert n == 1_000_000 and d == (960 if a.dataset == 'GIST' else 96)
    source = np.memmap(data_path, dtype='<f4', mode='r', offset=12, shape=(n, d))
    order = np.fromfile(BASE / f'reference_v2/{a.dataset}_idlist.i32', dtype='<i4')
    rank = np.empty(n, dtype=np.int32)
    rank[order] = np.arange(n, dtype=np.int32)
    qids = np.loadtxt(ROOT / 'fixtures' / f'{a.dataset}_p6_final1024.qid',
                      dtype=np.int32, skiprows=1)
    warm = np.loadtxt(P0 / 'fixtures' / f'{a.dataset}_dev256.qid',
                      dtype=np.int32, skiprows=1)
    assert len(qids) == 1024 and len(warm) == 256
    build = {}
    if a.method == 'cagra':
        from cuvs.neighbors import cagra
        begin = time.perf_counter()
        data = cp.asarray(source)
        cp.cuda.Stream.null.synchronize()
        build['data_layout_s'] = time.perf_counter() - begin
        begin = time.perf_counter()
        index = cagra.build(cagra.IndexParams(metric='sqeuclidean'), data)
        cp.cuda.Stream.null.synchronize()
        build['index_build_s'] = time.perf_counter() - begin
        params = cagra.SearchParams(algo='auto', itopk_size=max(64, a.k), search_width=1)
        build.update({'build_method': 'ivf_pq', 'graph_degree': 64,
                      'intermediate_graph_degree': 128, 'search_algo': 'auto',
                      'search_width': 1, 'itopk_size': max(64, a.k)})
    else:
        import faiss
        faiss.omp_set_num_threads(16)
        resources = faiss.StandardGpuResources()
        config = faiss.GpuIndexIVFFlatConfig()
        config.use_cuvs = False
        index = faiss.GpuIndexIVFFlat(resources, int(d), a.nlist,
                                      faiss.METRIC_L2, config)
        sample_ids = np.random.default_rng(TRAIN_SEED).choice(n, TRAIN_COUNT, replace=False)
        train_x = np.asarray(source[sample_ids], dtype=np.float32, order='C')
        begin = time.perf_counter()
        index.train(train_x)
        build['index_train_s'] = time.perf_counter() - begin
        begin = time.perf_counter()
        index.add(source)
        build['index_add_s'] = time.perf_counter() - begin
        assert index.ntotal == n
        index.nprobe = a.nprobe
        assert index.nprobe == a.nprobe
        begin = time.perf_counter()
        data = cp.asarray(source)
        cp.cuda.Stream.null.synchronize()
        build['verifier_layout_s'] = time.perf_counter() - begin
        build.update({'train_sample_count': TRAIN_COUNT, 'train_seed': TRAIN_SEED,
                      'backend': 'Faiss 1.15.1 source-built native GPU IVFFlat'})
    kernel = cp.RawKernel(KERNEL, 'refine', options=('--std=c++17', '--fmad=false'))
    workspace = {}

    def batch(ids_cpu, b, radius, refined):
        key = (b, a.k)
        if key not in workspace:
            workspace[key] = (cp.empty(key, dtype=cp.uint8),
                              cp.empty(key, dtype=cp.float32))
        keep, fields = workspace[key]
        begin = time.perf_counter()
        if a.method == 'cagra':
            qdev = cp.asarray(ids_cpu)
            query = data[qdev]
            native_dist, candidate = cagra.search(params, index, query, a.k)
            if not refined:
                host_ids = cp.asnumpy(candidate)
                host_dist = cp.asnumpy(native_dist)
                assert host_ids.shape == host_dist.shape == (b, a.k)
                return (time.perf_counter() - begin) * 1000, None
            dev_ids = cp.asarray(candidate).astype(cp.int64, copy=False)
            host_ids = None
        else:
            query = np.asarray(source[ids_cpu], dtype=np.float32, order='C')
            native_dist, host_ids = index.search(query, a.k)
            assert host_ids.shape == native_dist.shape == (b, a.k)
            if not refined:
                return (time.perf_counter() - begin) * 1000, None
            qdev = cp.asarray(ids_cpu)
            dev_ids = cp.asarray(host_ids, dtype=cp.int64)
        kernel(((b * a.k + 127) // 128,), (128,),
               (data, qdev, dev_ids, int(n), int(d), a.k, b, radius,
                keep, fields))
        if host_ids is None:
            host_ids = cp.asnumpy(dev_ids)
        keep_host = cp.asnumpy(keep)
        fields_host = cp.asnumpy(fields)
        result = collect_ordered(host_ids, keep_host, fields_host, rank)
        return (time.perf_counter() - begin) * 1000, result

    workloads = [(radius, b) for radius in BITS[a.dataset] for b in (8, 32)]
    workloads = workloads[(a.round-1) % len(workloads):] + workloads[:(a.round-1) % len(workloads)]
    timing = []
    audits = []
    for radius_name, b in workloads:
        radius = struct.unpack('<f', struct.pack('<I', BITS[a.dataset][radius_name]))[0]
        cutoff = float(radius) * float(radius)
        for start in range(0, 8*b, b):
            batch(warm[start:start+b], b, cutoff, True)
        modes = (True, False) if a.round % 2 else (False, True)
        for refined in modes:
            starts = list(range(0, 1024, b))
            if a.round % 2 == 0:
                starts.reverse()
            elapsed = []
            result_by_start = {}
            for start in starts:
                t, result = batch(qids[start:start+b], b, cutoff, refined)
                elapsed.append(t)
                if result is not None and a.round == 1:
                    result_by_start[start] = result
            timing.append({'round': a.round, 'dataset': a.dataset, 'radius': radius_name,
                           'B': b, 'method': a.method, 'nlist': a.nlist,
                           'nprobe': a.nprobe, 'K': a.k,
                           'mode': 'common_refined' if refined else 'native_topk',
                           'host_ready_ms': sum(elapsed),
                           'batch_p50_ms': float(np.median(elapsed)),
                           'batch_p95_ms': float(np.quantile(elapsed, .95)),
                           'qps': 1024000/sum(elapsed)})
            if refined and a.round == 1:
                output = [x for start in sorted(result_by_start)
                          for x in result_by_start[start]]
                truth = oracle(ROOT / 'runs' / f'oracle_p6_{a.dataset.lower()}_{radius_name}' / 'result.bin')
                assert len(truth) == len(output) == 1024
                audits.append({'dataset': a.dataset, 'radius': radius_name,
                               'B': b, 'method': a.method, 'nlist': a.nlist,
                               'nprobe': a.nprobe, 'K': a.k,
                               **quality(qids, truth, output, a.k)})
    print(json.dumps({'build': build, 'timing': timing, 'quality': audits},
                     sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
