#!/usr/bin/env python3
"""P6 GPU API smoke; invoke separately in pinned cuVS and Faiss environments."""
import argparse
import json
import time

import numpy as np


def smoke_cagra(x, q, k):
    import cupy as cp
    import cuvs
    from cuvs.neighbors import cagra

    data = cp.asarray(x)
    queries = cp.asarray(q)
    cp.cuda.Stream.null.synchronize()
    start = time.perf_counter()
    index = cagra.build(cagra.IndexParams(metric="sqeuclidean"), data)
    cp.cuda.Stream.null.synchronize()
    build_s = time.perf_counter() - start
    params = cagra.SearchParams(algo="auto", itopk_size=max(64, k))
    start = time.perf_counter()
    distances, ids = cagra.search(params, index, queries, k)
    cp.cuda.Stream.null.synchronize()
    search_ms = (time.perf_counter() - start) * 1000
    ids = cp.asnumpy(ids)
    distances = cp.asnumpy(distances)
    assert ids.shape == distances.shape == (len(q), k)
    assert np.issubdtype(ids.dtype, np.integer)
    assert np.issubdtype(distances.dtype, np.floating)
    assert np.all((ids >= 0) & (ids < len(x)))
    return {
        "library": "cuVS", "version": cuvs.__version__, "backend": "native CAGRA GPU",
        "metric": "sqeuclidean", "distance_unit": "squared L2",
        "build_params": {"intermediate_graph_degree": 128, "graph_degree": 64,
                         "build_algo": "ivf_pq"},
        "search_params": {"algo": "auto", "itopk_size": max(64, k), "search_width": 1},
        "build_s": build_s, "search_ms": search_ms,
        "first_ids": ids[0, :5].tolist(),
        "first_distances": distances[0, :5].tolist(),
        "has_native_range_search": hasattr(cagra, "range_search"),
    }


def smoke_faiss(x, q, k, use_cuvs):
    import faiss

    assert faiss.get_num_gpus() == 1
    faiss.omp_set_num_threads(16)
    resources = faiss.StandardGpuResources()
    config = faiss.GpuIndexIVFFlatConfig()
    config.use_cuvs = use_cuvs
    index = faiss.GpuIndexIVFFlat(resources, x.shape[1], 64, faiss.METRIC_L2,
                                  config)
    start = time.perf_counter()
    index.train(x)
    train_s = time.perf_counter() - start
    start = time.perf_counter()
    index.add(x)
    add_s = time.perf_counter() - start
    index.nprobe = 64
    assert index.nprobe == 64
    start = time.perf_counter()
    distances, ids = index.search(q, k)
    search_ms = (time.perf_counter() - start) * 1000
    assert ids.shape == distances.shape == (len(q), k)
    assert np.all((ids >= 0) & (ids < len(x)))
    native_range = {"status": "UNTESTED"}
    try:
        lims, range_d, range_i = index.range_search(q[:1], np.float32(4.0))
        native_range = {"status": "SUPPORTED", "hits": len(range_i),
                        "lim_last": int(lims[-1])}
    except Exception as exc:
        native_range = {"status": "UNSUPPORTED_API", "exception": type(exc).__name__,
                        "message": str(exc)[:500]}
    return {
        "library": "Faiss", "version": faiss.__version__,
        "compile_options": faiss.get_compile_options(),
        "backend": "GpuIndexIVFFlat cuVS GPU" if use_cuvs else "GpuIndexIVFFlat native GPU",
        "metric": "METRIC_L2",
        "distance_unit": "squared L2", "nlist": 64, "nprobe": 64,
        "train_s": train_s, "add_s": add_s, "search_ms": search_ms,
        "first_ids": ids[0, :5].tolist(),
        "first_distances": distances[0, :5].tolist(),
        "native_range_search": native_range,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("backend", choices=("cagra", "faiss"))
    p.add_argument("--n", type=int, default=4096)
    p.add_argument("--d", type=int, default=96)
    p.add_argument("--batch", type=int, default=8)
    p.add_argument("--k", type=int, default=128)
    p.add_argument("--use-cuvs", action="store_true")
    a = p.parse_args()
    rng = np.random.default_rng(20261002 + a.n + a.d)
    x = rng.normal(size=(a.n, a.d)).astype(np.float32)
    q = x[:a.batch].copy()
    result = (smoke_cagra(x, q, a.k) if a.backend == "cagra" else
              smoke_faiss(x, q, a.k, a.use_cuvs))
    result.update(n=a.n, d=a.d, batch=a.batch, k=a.k,
                  self_in_first_five=0 in result["first_ids"])
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
