# Original GTS query-stage attribution, 2026-09-23

Frozen before implementation/runs. Parent: 80e4d06. This is diagnosis of the
original range path, not a TC optimization, novelty claim or production keeper.
Gate 0: indexed TC distance is already prior art; no new thesis is proposed.

## Workload and invariants
- Same parent fixtures: N=65,536, 128D integer SIFT [0,255], Q=32/128,
  radii=300/500, deterministic IDs floor(i*N/Q). Smoke N=2,000/Q32/r300.
- Exact per-query counts, self included, independent full-table integer oracle.
  No result IDs, kNN/updates, cold startup, external query ingestion or all-tree claim.
- Pinned original GTS source, 18-file manifest. MAX_H=5 (3 for smoke), unchanged
  MAX_SIZE=20, 256 MiB workspace. Mute the same two prints as the parent; free
  managed result after every CPU delivery. No kernel body/launch, candidate,
  arithmetic, allocation policy or native synchronization change.
- No TC bridge or dense comparator is built into this driver. Reuse existing
  source preparation, fixture hashes, stats and GPU admission helpers.
- PRO 6000 Blackwell GPU0 only, CUDA13.1.115, driver590.48.01, shared host.
  Recheck admission per process under /tmp/gtspp_gpu0.lock; never change settings,
  profile permissions or foreign jobs. Stop on contamination/failing correctness.

## Measurement
- Compare fresh processes using native default wait policy D versus explicit
  cudaDeviceScheduleBlockingSync B. Query main-thread CPU/wall ratio is a
  one-core denominator, not host-wide CPU utilization. Runtime API wait is not
  automatically CPU arithmetic. All other execution paths identical.
- Primary timer: monotonic host wall, query dispatch to CPU counts, including
  query allocations/frees and result copy/free; resident data and prebuilt index.
  Secondary: main-thread CPU and whole-process CPU during the SAME query.
- Disjoint host stage scopes: allocation/init, host/metadata scheduling,
  internal node distance/pruning, leaf candidate formation, leaf distances,
  result aggregation, cleanup, and result delivery. Each includes original waits
  in its region. No extra GPU synchronization or event inserted within query.
  Host stages partition the path, but are not pure CPU time or pure arithmetic.
- Clear accumulated phase counters outside each timed call. Print/validate
  outside timing. Keep total-minus-stage accounting residual. Diagnostic phase
  instrumentation adds clocks and map updates; no zero-overhead claim.
- Six matched fresh-process pairs per shape, D/B then B/D alternated (3:3).
  One initial correctness call, 3 warmups, 8 retained calls; every result checked.
  This is repeated-query diagnosis, NOT an uninterrupted throughput promotion.
- Retain every process/order/sample. Report p10/median/p90, paired geometric
  process-median D/B ratio with 10k seed0 bootstrap CI, marginal ratio, pair wins
  and order splits. No best-order filtering or cross-campaign speedup claim.
- Correctness in both policies/all five shapes; memcheck/synccheck in default
  for all five and blocking for smoke plus largest case; initcheck/racecheck for
  default smoke. No Graph, concurrent-stream or production certification.

## Profiler gates / interpretation
- Nsight Systems: default-policy trace for every main shape, blocking trace for
  Q128/r500. Capture only 3 measured queries using cudaProfilerStart/Stop after
  correctness/warmup. cuda,nvtx; sampling/context switching disabled. Default
  lighter tracing; an additional Q128/r500 default trace enables UM page faults.
- Count and sum kernel/copy/memset intervals inside each query, compute interval
  unions rather than adding overlapping waits. Correlate CUDA APIs to stage
  labels. Trace percentages are diagnostic and not unprofiled latency results.
- NCU: attempt once for native leaf kernel after correctness/sanitizer gates.
  If counter access is denied, retain it and stop retrying; do not change driver
  permissions. Arithmetic-vs-memory throughput/stall cause then remains unknown.
- Long leaf-distance stage does not establish arithmetic saturation: it also
  contains loads, address work, sparse useful lanes, scheduling and resources.
  Static 47,528-byte generic-metric stacks are not causal proof. No ablation of
  memory residency, stack, math instructions or kernel geometry in this campaign.

## Delivery
Publish authored instrumentation/analysis, portable numeric evidence and frozen
contract only. Preserve original sources, previous experiments and raw private
receipts. No raw datasets, generated upstream copies, machine paths/addresses,
credentials or profiler binaries. Rebuild from committed archive before upload;
verify remote commit and every intended file. Report exact limits and next test.

## Appended outcome (2026-09-23; original frozen text preserved above)

All ten policy/shape correctness runs and all sixteen declared sanitizer runs
passed. All 48 fresh timing processes passed, retaining 384 query and 3,072
stage observations. Six NSYS traces passed validation and contain three measured
queries each. The NCU attempt returned ERR_NVGPUCTRPERM; application counts still
matched, but no hardware-counter measurement was obtained. No settings or
permissions were changed. No CUDA device kernel or launch was optimized.

Leaf distance processing dominates this SIFT L2 contract. Blocking waiting
greatly reduces query CPU but does not provide a latency improvement. This is
consistent with prior Words CPU wait sensitivity, while its aggregation
bottleneck belongs to a different metric/workload/denominator. Arithmetic versus
memory/scheduling cause inside the leaf kernel remains unknown. See README for
the measured distributions, scoped comparison and unexecuted next control.
