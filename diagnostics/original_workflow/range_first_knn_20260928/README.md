# Range-first kNN diagnostic artifacts

This directory preserves the source and small raw logs behind
[the experiment report](../RANGE_FIRST_KNN_PILOT_20260927.md). The pinned
starting point is `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
No original source file is changed in place.

`baseline.patch` applies the shared SIFT FP32 diagnostic changes, bounded
256 MiB query workspace, MAX_H=6, and timing instrumentation to the pinned
original `include/`. `hybrid.patch` then changes its range path to retain
and select in-radius distances. `bench_baseline.cu` measures the adapted GTS
kNN path; `bench_auto.cu` calibrates a radius from one kNN batch and runs
range-first search with exact kNN fallback for insufficient candidates.
`bench_baseline.cu` can also reproduce the fixed-radius pilot when compiled
against the hybrid headers with `-DHYBRID`.
These diagnostic programs return the kth **distance**, not neighbor IDs, and
require SIFT byte-valued 128-dimensional input. They are not a general GTS
query implementation.

The query ID files contain two disjoint sets of 32 self-inclusive SIFT1M
queries. The SIFT1M `sift_base.fvecs` file is not bundled; its SHA-256 must be
`21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816`.
The `evidence/` directories contain the retained 4090 and PRO 6000 stdout,
including the full-table kth-distance oracle checks and sanitizer summaries.
Load, index build, calibration, oracle, and warmups are excluded from each
timed query sample; fallback and CPU result delivery are included.

To reconstruct the two exact header variants, set `PINNED_GTS` to the
checked-out original GTS directory containing `include/`, `ARTIFACT` to
this directory's absolute path, and `SCRATCH` to a new scratch directory:

```sh
mkdir -p "$SCRATCH/baseline" "$SCRATCH/hybrid"
cp -a "$PINNED_GTS/include" "$SCRATCH/baseline/include"
(cd "$SCRATCH/baseline" && git apply -p2 "$ARTIFACT/baseline.patch")
cp -a "$SCRATCH/baseline/include" "$SCRATCH/hybrid/include"
(cd "$SCRATCH/hybrid" && git apply -p2 "$ARTIFACT/hybrid.patch")
sha256sum "$SCRATCH/baseline/include/search_v2.cuh" "$SCRATCH/hybrid/include/search_v2.cuh"
```

The two search-header hashes must respectively be
`af4d66012e8efaa3266230c53c7f8fc35d636834c6ddd2173bdef5215899996d`
and `5909a71addb34c7f3a0b909e0c21f46f80a991681b106731399455ce6831b9f5`.
They were verified by applying both patches to a fresh copy of the pinned
headers. On PRO 6000 Blackwell with CUDA 13.1, compile and run after selecting
an idle GPU:

```sh
nvcc -O3 -std=c++17 -arch=sm_120 --extended-lambda -DGTS_DIAG_NVTX \
  -I"$SCRATCH/baseline/include" "$ARTIFACT/bench_baseline.cu" -o "$SCRATCH/bench_baseline"
nvcc -O3 -std=c++17 -arch=sm_120 --extended-lambda -DGTS_DIAG_NVTX \
  -I"$SCRATCH/hybrid/include" "$ARTIFACT/bench_auto.cu" -o "$SCRATCH/bench_auto"
nvcc -O3 -std=c++17 -arch=sm_120 --extended-lambda -DGTS_DIAG_NVTX -DHYBRID \
  -I"$SCRATCH/hybrid/include" "$ARTIFACT/bench_baseline.cu" -o "$SCRATCH/bench_fixed_range"
"$SCRATCH/bench_baseline" "$SIFT_BASE" "$ARTIFACT/q32_holdout.txt" 10 299
"$SCRATCH/bench_auto" "$SIFT_BASE" "$ARTIFACT/q32_holdout.txt" \
  "$ARTIFACT/q32_1m.txt" 10 0
"$SCRATCH/bench_fixed_range" "$SIFT_BASE" "$ARTIFACT/q32_1m.txt" 10 300
```

The final argument to `bench_auto` is a radius override; `0` chooses the
radius from the calibration batch. The report identifies the GPU UUIDs,
driver versions, paired timings, fallback counts, and validation limits.
