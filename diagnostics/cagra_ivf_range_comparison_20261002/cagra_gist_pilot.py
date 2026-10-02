#!/usr/bin/env python3
"""P6 GIST 1M CAGRA feasibility and static build-cost pilot."""
import json
import time

import cupy as cp
import numpy as np
from cuvs.neighbors import cagra


DATA = "/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/data/GIST/1000000/fixtures/data.f32bin"
QIDS = "/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/fixtures/GIST_dev256.qid"


def main():
    with open(DATA, "rb") as f:
        d, n, _ = np.fromfile(f, dtype="<i4", count=3)
    assert (int(n), int(d)) == (1_000_000, 960)
    source = np.memmap(DATA, dtype="<f4", mode="r", offset=12, shape=(n, d))
    with open(QIDS) as f:
        count = int(f.readline())
        qids = np.array([int(f.readline()) for _ in range(count)], dtype=np.int32)
    assert count == 256
    start = time.perf_counter()
    data = cp.asarray(source)
    cp.cuda.Stream.null.synchronize()
    copy_s = time.perf_counter() - start
    params = cagra.IndexParams(metric="sqeuclidean")
    start = time.perf_counter()
    index = cagra.build(params, data)
    cp.cuda.Stream.null.synchronize()
    build_s = time.perf_counter() - start
    query = data[cp.asarray(qids[:8])]
    search_params = cagra.SearchParams(algo="auto", itopk_size=128)
    start = time.perf_counter()
    distances, ids = cagra.search(search_params, index, query, 128)
    cp.cuda.Stream.null.synchronize()
    search_ms = (time.perf_counter() - start) * 1000
    ids = cp.asnumpy(ids)
    distances = cp.asnumpy(distances)
    assert ids.shape == (8, 128) and distances.shape == (8, 128)
    assert np.issubdtype(ids.dtype, np.integer) and np.issubdtype(distances.dtype, np.floating)
    print(json.dumps({"n": int(n), "d": int(d), "copy_s": copy_s,
                      "build_s": build_s, "first_search_ms_including_jit": search_ms,
                      "first_ids": ids[0, :5].tolist(),
                      "first_distances": distances[0, :5].tolist(),
                      "graph_degree": 64, "intermediate_graph_degree": 128,
                      "build_algo": "ivf_pq", "search_algo": "auto",
                      "itopk_size": 128, "k": 128}), flush=True)


if __name__ == "__main__":
    main()
