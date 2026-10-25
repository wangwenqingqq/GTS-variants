# Repaired GTS versus exact scan — frozen protocol v1

Frozen before CUDA implementation or new GPU execution, 2026-10-25 UTC
(task identifier: 20261024). This is an attribution/positioning experiment,
not a novelty claim. Existing engineering repairs do not establish a new thesis.
Missing evidence is uncertainty, not evidence against metric trees.

## Execution and provenance

- Target: previously admitted physical GPU 0, RTX PRO 6000 Blackwell,
  UUID `GPU-9bd364a9-9d88-0b78-ef55-caac6f73d6b1`, sm_120.
- Live preflight: driver 590.48.01; CUDA 13.1.115. Never reuse old timings.
- Existing GPU-0 campaign advisory lock, plus task lock. Idle admission requires
  no compute applications, utilization 0%, memory <=256 MiB. Save before/after
  state and poll during each GPU process. On foreign activity stop only the
  task-owned process group, retain the failed observation, stop campaign;
  no replacement observations, migration, settings changes, or foreign signals.
  Other GPUs' tasks are not grounds to signal them or use their devices.
- New source, generated copies, binaries, data copies, and logs live only in the
  new task directory / matching remote scratch. Old source/evidence is read-only.
- Base repository: `backups/gts-evidence-20261008`, commit
  `5dea689fda0a26d2d638336f04131c75951c091c`.
- Author headers/main must match the eight GTS SHA-256 pins in
  `diagnostics/original_tree_redundancy/SOURCE_PINS.json` (author commit
  `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`). Do not use the modified
  top-level backup branch implementation as the original.

## Arms and ordered output

- A: pinned original `searchIndexRnnUpdate`, full-table edit distance, original
  allocation, traversal, counting, selection, projection and host delivery.
  This is the original path underlying the existing Graph/fusion repairs, not
  the separate author-V2 path. Disclose any required safety adapter separately.
- R: reuse fixed-capacity workspace and stable fused result selector, remove
  redundant candidate/result counts on the fused path, multi-CTA traversal with
  unchanged predicate/arithmetic, CUDA Graph replay. Full original leaf distance
  remains; optional L2 early stopping is not required and may only be added as
  an explicitly separate candidate after correctness. Never multiply old gains.
- S: exact GPU scan. Words: existing exact rolling-row Levenshtein helper;
  L2: existing flat L2 arithmetic. Use native parallel stable compaction, not
  device-side serial Thrust reduction. It must not need a metric tree.
- ArborX: native CUDA BVH range queries on Tloc only, if the existing environment
  can build it. Preserve native build/version failure logs. No handwritten proxy.
- Complete self-inclusive `(ID, distance, count)` output is CPU resident before
  timer stop. Public order is ascending original ID per query; common host
  canonicalization is charged. Additionally compare R's native ordered IDs and
  float32 distances byte-for-byte with A before canonicalization. Scan can use
  ID order directly. Full output validation, not count/hash alone, gates timing.
- L2 uses original float32 coordinates, non-fast-math original arithmetic;
  CPU oracle independently uses float64 sums and square root. Exact ID/count
  equality; distances within `4e-6 + 4e-6*abs(reference)`. A/R native distances
  must also be bit-identical. Edit distances are exact integers.

## Data, calibration, and query batches

Required: all 611,756 Words, SHA-256
`72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c`;
Tloc 1,000,000 x 2 float32, existing bit-preserving full fixture SHA-256
`bbc244a8c6632ad9a55e31b4b0a2ad07ab317d8e70855cd958b454cfdef80eda`
(original source SHA-256 `a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677`).
Deep 1M is optional and omitted unless the required matrix finishes.

Sample 16 calibration and 1024 distinct test object IDs with Python Random
seed 20261024, without replacement, calibration first. This is an in-dataset
query contract, not held-out external vectors. The two ID sets must be disjoint.
For each target 10/100/1000 hits, use the median across calibration queries of
the target-th smallest CPU distance (self included); convert radius to float32.
For Words choose the smallest nonnegative integer radius whose calibration
median count reaches the target. Ties/discrete distances may overshoot or give
duplicate radii; retain labels and actual hit counts, do not retune. Save and
hash calibration.json before any test-arm execution. Test data never tunes r.
Q=1/32/1024 uses nested test prefixes. Preserve all test oracle outputs.

The repairs are a batch-one path; bundling Q calls does not establish native
parallel batching. Use the same serial host-ready bundle for A/R/S if native
batching cannot preserve this repair contract. Report batch latency and Q,
never call it native batched throughput. This is a material boundary versus
strong scan/BVH batching; do not claim a universal best-scan comparison.

## Timing, inference and gates

- Timer: synchronized steady-clock host-ready bundle: host input submission,
  GPU execution, complete IDs/distances/count D2H, host canonicalization.
  Build, allocation/setup, Graph capture/instantiate, first call and warmup
  are excluded and reported separately. R's fixed-capacity output copying is
  charged, not replaced by a count-only timer. No oracle/file I/O inside timer.
- Fresh processes per arm per workload, 6 matched rounds. Three arms use
  `ARS, SRA, RAS, SAR, ASR, RSA`; each pair has three executions per order.
  With ArborX use a precomputed direction-balanced four-arm schedule and save it
  before timing. No retries or replaced samples. 3 complete-bundle warmups,
  3 retained complete bundles per process; per-process median is the statistic.
- Primary ratios R/S and R/A: exponentiated mean of 6 matched log ratios,
  Student-t 95% CI (df=5, t=2.5705818366). Also retain raw samples, marginal
  medians, p10/p90, order split and round wins. Never count queries/iterations
  as independent processes. Decisions are point-estimate rules below; a CI
  crossing a boundary makes support uncertain and must be stated.
- All complete outputs for every Q/radius must pass CPU oracle and A/R ordered
  comparison before that workload is eligible. Memcheck and synccheck must
  pass on a bounded real-data fixture for every arm (including empty/all-hit
  boundaries), plus full-data validation and 32 Graph replays with changing IDs.
  Sanitizer logs cannot be replaced by successful compilation.
- Separate instrumentation build, never timed: actual node/leaf/scan distance
  invocations, evaluated DP cells / coordinates, candidate leaves, active
  leaf/scan payload threads divided by launched payload threads (including
  inactive capacity CTAs), reported as algorithmic utilization, not an NCU
  SM occupancy metric. Preserve missing counters as missing, not estimates.
- Every binary, generated source, input, frozen radius/query file, runner and
  receipt is hash-bound. A failed correctness or resource gate is retained and
  blocks promotion; it does not prove the underlying mechanism impossible.

## Predeclared decisions

- R/S <=1 throughout the required tested matrix and >=2x faster than S on at
  least one workload: candidate evidence for a GPU metric-tree execution paper,
  subject to correctness, sanitizer, native-batching caveat and novelty Gate 0.
- R slower than S but substantially improved over A: attribution/experimental
  analysis positioning; quantify which implementation defects caused the gap.
  Do not claim this classification from incomplete required workloads.
- Tloc R/ArborX >=5 on the same contract: close the tested low-dimensional route.
  Missing ArborX, incomplete gates, or a mixed result means undecided, not closed.

## Failure handling

Append dated amendments before applying changes; never rewrite frozen v1.
On failure retain stdout/stderr, command, GPU telemetry, hashes and exact gate.
Report all 18 required workloads even if their values are NA. Never borrow the
old r4 results, infer an interval without 6 valid pairs, or claim an upload from
local commits. Publish only task-owned curated files to
`experiments/repaired-gts-vs-scan-20261024`; do not merge main.
