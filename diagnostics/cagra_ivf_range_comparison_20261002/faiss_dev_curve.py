#!/usr/bin/env python3
"""P6 native Faiss GPU IVFFlat top-K and strict range-refined dev curve."""
import argparse
import json
import struct
import time

import cupy as cp
import faiss
import numpy as np

from range_refine import KERNEL, collect_ordered, oracle, quality


DATA = "/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/data/GIST/1000000/fixtures/data.f32bin"
ORDER = "/home/data/wangxuran/tmp/gts_arithmetic_path_boundary_20260928/reference_v2/GIST_idlist.i32"
QIDS = "/home/data/wangxuran/tmp/gts_batch_exact_highdim_20261001/fixtures/GIST_dev256.qid"
REFERENCE = "/home/data/wangxuran/tmp/gts_p4_tree_batch_20261002/runs/scan_e_dev256_b8/result.bin"
RADIUS_BITS = 0x3F34A3D8
TRAIN_SEED = 2026100207
TRAIN_COUNT = 200000


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--nlist", type=int, choices=(1024, 4096), required=True)
    p.add_argument("--nprobe", type=int, required=True)
    p.add_argument("--k", type=int, choices=(128, 512, 2048), required=True)
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--bucket-audit", action="store_true")
    a = p.parse_args()
    if a.nprobe > a.nlist or a.nprobe < 1:
        raise ValueError("invalid nprobe")
    faiss.omp_set_num_threads(16)
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

    sample_ids = np.random.default_rng(TRAIN_SEED).choice(n, TRAIN_COUNT, replace=False)
    train_x = np.asarray(source[sample_ids], dtype=np.float32, order="C")
    resources = faiss.StandardGpuResources()
    config = faiss.GpuIndexIVFFlatConfig()
    config.use_cuvs = False
    index = faiss.GpuIndexIVFFlat(resources, int(d), a.nlist, faiss.METRIC_L2,
                                  config)
    start = time.perf_counter()
    index.train(train_x)
    train_s = time.perf_counter() - start
    start = time.perf_counter()
    index.add(source)
    add_s = time.perf_counter() - start
    assert index.ntotal == n
    index.nprobe = a.nprobe
    assert index.nprobe == a.nprobe
    start = time.perf_counter()
    data = cp.asarray(source)
    cp.cuda.Stream.null.synchronize()
    verifier_layout_s = time.perf_counter() - start
    kernel = cp.RawKernel(KERNEL, "refine", options=("--std=c++17", "--fmad=false"))
    keep = cp.empty((32, a.k), dtype=cp.uint8)
    fields = cp.empty((32, a.k), dtype=cp.float32)

    def one_batch(start, refined):
        begin = time.perf_counter()
        batch_ids = qids[start:start + 32]
        query = np.asarray(source[batch_ids], dtype=np.float32, order="C")
        native_distances, ids_host = index.search(query, a.k)
        assert ids_host.shape == native_distances.shape == (32, a.k)
        if not refined:
            return (time.perf_counter() - begin) * 1000, None
        dev_ids = cp.asarray(ids_host, dtype=cp.int64)
        dev_qids = cp.asarray(batch_ids)
        kernel(((32 * a.k + 127) // 128,), (128,),
               (data, dev_qids, dev_ids, int(n), int(d), a.k, 32, cutoff, keep, fields))
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
            records.append({"round": round_no,
                            "mode": "common_refined" if refined else "native_topk",
                            "k": a.k, "nlist": a.nlist, "nprobe": a.nprobe,
                            "queries": 256, "host_ready_ms": sum(batch_times),
                            "batch_p50_ms": float(np.median(batch_times)),
                            "batch_p95_ms": float(np.quantile(batch_times, .95))})
            if refined and first_results is None:
                first_results = all_results
    bucket_audit = None
    if a.bucket_audit:
        cpu_index = faiss.index_gpu_to_cpu(index)
        assigned = np.full(n, -1, dtype=np.int32)
        lists = cpu_index.invlists
        for list_id in range(a.nlist):
            size = lists.list_size(list_id)
            if size:
                ids = faiss.rev_swig_ptr(lists.get_ids(list_id), size)
                assigned[ids] = list_id
        assert np.all(assigned >= 0)
        query = np.asarray(source[qids], dtype=np.float32, order="C")
        probes = sorted({x for x in (1, 4, 16, 64, 256, 1024, a.nlist)
                         if x <= a.nlist and x <= 2048})
        bucket_audit = []
        for nprobe in probes:
            _, selected_lists = index.quantizer.search(query, nprobe)
            covered = 0
            after_budget = 0
            for (_, expected, _), selected in zip(truth, selected_lists):
                count = int(np.count_nonzero(np.isin(assigned[expected], selected)))
                covered += count
                after_budget += min(a.k, count)
            total = sum(len(x[1]) for x in truth)
            bucket_audit.append({"nprobe": nprobe, "bucket_covered_true_ids": covered,
                                 "bucket_coverage_micro": covered / total,
                                 "bucket_then_K_ceiling_micro": after_budget / total})
    print(json.dumps({"dataset": "GIST", "radius": "half", "B": 32,
                      "nlist": a.nlist, "nprobe": a.nprobe, "k": a.k,
                      "train_sample_count": TRAIN_COUNT, "train_sample_seed": TRAIN_SEED,
                      "backend": "Faiss 1.15.1 source-built native GpuIndexIVFFlat",
                      "train_s": train_s, "add_s": add_s,
                      "verifier_layout_s": verifier_layout_s,
                      "timing": records,
                      "quality": quality(qids, truth, first_results, a.k),
                      "bucket_audit": bucket_audit},
                     sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
