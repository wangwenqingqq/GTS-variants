#!/usr/bin/env python3
"""P6 CAGRA candidate-budget development curve with strict common refinement."""
import argparse
import json
import struct
import time

import cupy as cp
import numpy as np
from cuvs.neighbors import cagra


DATA = "/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/data/GIST/1000000/fixtures/data.f32bin"
ORDER = "/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/reference_v2/GIST_idlist.i32"
QIDS = "/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/fixtures/GIST_dev256.qid"
REFERENCE = "/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002/runs/scan_e_dev256_b8/result.bin"
RADIUS_BITS = 0x3F34A3D8
from range_refine import KERNEL, collect_ordered, oracle, quality

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--k", type=int, required=True)
    p.add_argument("--rounds", type=int, default=3)
    a = p.parse_args()
    if a.k < 1 or a.k > 1024:
        raise ValueError("cuVS 26.08 CAGRA topk limit is 1024")
    with open(DATA, "rb") as f:
        d, n, _ = np.fromfile(f, dtype="<i4", count=3)
    assert (int(n), int(d)) == (1_000_000, 960)
    source = np.memmap(DATA, dtype="<f4", mode="r", offset=12, shape=(n, d))
    with open(QIDS) as f:
        count = int(f.readline())
        qids = np.asarray([int(f.readline()) for _ in range(count)], dtype=np.int32)
    assert count == 256
    rank = np.empty(n, dtype=np.int32)
    rank[np.fromfile(ORDER, dtype="<i4")] = np.arange(n, dtype=np.int32)
    truth = oracle(REFERENCE)
    assert [int(i) for i in qids] == [x[0] for x in truth]
    radius = struct.unpack("<f", struct.pack("<I", RADIUS_BITS))[0]
    cutoff = float(radius) * float(radius)
    setup = time.perf_counter()
    data = cp.asarray(source)
    cp.cuda.Stream.null.synchronize()
    layout_s = time.perf_counter() - setup
    setup = time.perf_counter()
    index = cagra.build(cagra.IndexParams(metric="sqeuclidean"), data)
    cp.cuda.Stream.null.synchronize()
    build_s = time.perf_counter() - setup
    params = cagra.SearchParams(algo="auto", itopk_size=max(64, a.k), search_width=1)
    kernel = cp.RawKernel(KERNEL, "refine", options=("--std=c++17", "--fmad=false"))
    keep = cp.empty((32, a.k), dtype=cp.uint8)
    fields = cp.empty((32, a.k), dtype=cp.float32)

    def one_batch(start, refined):
        batch_ids = qids[start:start + 32]
        begin = time.perf_counter()
        dev_qids = cp.asarray(batch_ids)
        query = data[dev_qids]
        distances, ids = cagra.search(params, index, query, a.k)
        if not refined:
            ids_host = cp.asnumpy(ids)
            native_distances = cp.asnumpy(distances)
            assert ids_host.shape == native_distances.shape == (32, a.k)
            return (time.perf_counter() - begin) * 1000, None
        ids = cp.asarray(ids).astype(cp.int64, copy=False)
        kernel(((32 * a.k + 127) // 128,), (128,),
               (data, dev_qids, ids, int(n), int(d), a.k, 32, cutoff, keep, fields))
        ids_host = cp.asnumpy(ids)
        keep_host = cp.asnumpy(keep)
        fields_host = cp.asnumpy(fields)
        results = collect_ordered(ids_host, keep_host, fields_host, rank)
        return (time.perf_counter() - begin) * 1000, results

    for start in range(0, 256, 32):
        one_batch(start, True)
    records = []
    first_results = None
    for round_no in range(1, a.rounds + 1):
        for refined in ((round_no % 2 == 1), (round_no % 2 == 0)):
            batch_times = []
            all_results = []
            for start in range(0, 256, 32):
                elapsed, results = one_batch(start, refined)
                batch_times.append(elapsed)
                if results is not None:
                    all_results.extend(results)
            row = {"round": round_no, "mode": "common_refined" if refined else "native_topk",
                   "k": a.k, "queries": 256, "host_ready_ms": sum(batch_times),
                   "batch_p50_ms": float(np.median(batch_times)),
                   "batch_p95_ms": float(np.quantile(batch_times, .95))}
            records.append(row)
            if refined and first_results is None:
                first_results = all_results
    result = {"dataset": "GIST", "radius": "half", "B": 32, "k": a.k,
              "radii_bits": hex(RADIUS_BITS), "layout_s": layout_s,
              "graph_build_s": build_s, "build_algo": "ivf_pq",
              "graph_degree": 64, "intermediate_graph_degree": 128,
              "search_algo": "auto", "search_width": 1, "itopk_size": max(64, a.k),
              "timing": records, "quality": quality(qids, truth, first_results, a.k)}
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
