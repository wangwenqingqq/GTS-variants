# SIFT range-first kNN pilot on RTX 4090

Date: 2026-09-27. This is a static-query diagnostic prototype, not a change to
the original GTS implementation or a general exact-kNN implementation.

## Compared paths

Both paths derive from the pinned original GTS source through the existing
FP32 SIFT query diagnostic. They use the same SIFT1M data, original index
construction, MAX_H=6, 256 MiB query workspace, RTX 4090 GPU0, and FP32
multiply/sqrt L2 specialization. The baseline follows GTS's kNN traversal and
sort. The prototype follows GTS's fixed-radius traversal, retains exact SIFT
integer squared distances from visited leaves, removes out-of-radius slots,
sorts the remaining integer keys, and selects the kth distance per query. Both
deliver a floating-point kth distance to the CPU. The prototype returns an
insufficient-candidates error when the chosen radius contains fewer than k
points (the harness flags the returned `-1`); radius expansion/fallback is not
implemented.

This comparison includes the compact integer-key selection pipeline, not just
the effect of range pruning. It does not isolate a pure RNN/kNN coupling gain.

## Results

SIFT1M: N=1,000,000, D=128, self-inclusive base-vector queries, Q=32,
k=10, radius=300. Each path passed an independent full-table integer kth-
distance oracle on every process. The warm-query timer starts at search
dispatch and ends after the kth distances are delivered to the CPU. It includes
query allocation, all kernels/sorts/synchronization, cleanup, and the
prototype's squared-distance-to-distance conversion. Loading, index build,
oracle, and warmups are outside the timer.

Three fresh-process pairs alternated A/B, B/A, A/B. Each process ran one
checked query, three checked warmups, and eight retained queries. Medians are
over the eight retained queries within each process.

| Pair | GTS kNN A (ms) | Range-first B (ms) | A/B |
|---|---:|---:|---:|
| 0 | 104.187 | 70.036 | 1.488 |
| 1 | 104.673 | 70.335 | 1.488 |
| 2 | 104.717 | 70.313 | 1.489 |

The paired geometric speedup is **1.488x** (about 32.8% less warm-query
latency). A fixed-seed, separate set of 32 base-vector query IDs also passed
the full-table kth-distance oracle: median 102.176 ms for A and 69.380 ms
for B in one fresh process per path. Radius 300 covered all 32 queries in
both sets, but the first set's in-radius count varied from 10 to 31,542 per
query. At radius 250, only 26/32 first-set queries had at least ten matches;
the prototype returned `-1`, which the oracle check flagged. Thus the fixed
radius is not a correctness guarantee for arbitrary queries or k values.

`compute-sanitizer --tool memcheck` reported zero errors for the final
prototype binary at SIFT65k/Q32/k10/r500. The same GPU kernel source also
passed at SIFT1M/Q32/k10/r300 before a host-only output conversion was added.
The full-table oracle covers kth distance, not neighbor IDs or tie ordering.

## Scope and evidence

The experiment ran on RTX 4090 UUID
`GPU-015723f9-1f4b-502b-017d-4530ee371ad9`, driver 580.159.04, under
`/tmp/gtspp_gpu0.lock` with no other compute app observed before/after runs.
Source is from `ZJU-DAILY/GTS@3bac1b7`, via the existing FP32 diagnostic; the
repository-root include/src tree is a different archived branch. This pilot
does not cover external query vectors, updates, other distance metrics, result
IDs, different k, learned radius selection, radius fallback, or full
load-build-query latency.

The temporary source generator and harness are at
`4090-left:/tmp/gts_range_knn_pilot_20260927`; raw stdout/stderr, binaries,
build logs, and fixed-seed holdout IDs are at
`4090-left:/tmp/gts_range_knn_run_20260927`. Final SHA-256 binary hashes:
A `f620326bca747eba0c653e1b9bf6ce1ee799a93e4eec00e71457a4c1bda516c1`,
B `ab60a03d3a6c5c82fadd0d2c1b5385ed1f6aad89cbda3c5407d75e40927c915c`.
No original source file was edited.
