# Stable result-selection fusion

Experiment: gts_20260923_fused_result. State: designed before implementation.
Engineering attribution only: cooperative scan/select and epilogue fusion are
established techniques, not a new GTS++ thesis. Reuse installed CUB BlockScan;
no custom scan framework, distance rewrite, source repair or new dependency.

## Frozen scope and mechanism

Reuse graph_query_20260923 at commit 7938ed6: original immutable Words N=2000,
64 distinct changing query IDs, batch one, height 3, 111 candidate slots and
2220 result slots, int flags/IDs and exact original float distances. Full ordered
IDs, distances and count delivered to host. No inserts/deletes in full-query
workloads; synthetic selection tests additionally cover nonidentity ID prefixes.
Larger shapes fail closed. No concurrency or larger-tree claim.

B/C retain the previous stream/Graph functions unchanged. D/E substitute one
512-thread CTA for F4+F5: duplicate reductions, result-count scan, hit scan,
scatter and separate projection. One integer exclusive block scan yields both
rank and total. Process consecutive 512-slot tiles with a per-thread identical
carry; read only candidate_count*20 flags, load payload only for hits, preserve
leaf-major/item-major order, and write count even at zero candidates. The
separate deletion-prefix scan is retained before the fused store; all other
traversal, candidate selection, leaf work, allocation and host delivery remain.
Expected GPU launch delta: 24 -> 17 per query (8 old operations -> 1); verify by
NSYS rather than treating this source ledger as a measurement.

Comparators: A native functions for full-output/order anchors; B unfused stream;
C unfused Graph; D fused stream; E fused Graph. Primary C/E, secondary B/D:
remeasure all four in this campaign, never divide by previous measurements.

## Ownership, resources and readiness

| Phase | Owner / live state | Ready / release edge |
|---|---|---|
| Leaf output | Existing independent leaf CTAs; unchanged distance DP | Same-stream completion before selection |
| Prefix maintenance | Existing CUB deletion scan | Completes before fused projection; still charged |
| Select tile | All 16 warps, one lane per flag; int predicate/rank/aggregate/carry; CUB shared scratch | All threads participate including tail lanes; CTA barrier before scratch reuse |
| Emit | Hit lane owns unique carry+rank output; ID/float payload loaded only for hit | Last input use at store; no intermediate compacted payload |
| Count / delivery | Thread 0 publishes aggregate; stream copies count/full capacity to pinned host buffers | Completion before host reads or workspace overwrite |

No cross-block barrier, spin loop, atomics, Tensor Core arithmetic, TMA, cluster
or special swizzle. Expected working set: CUB scan scratch plus a few ints per
thread; no distance DP state, stack array or payload tile in shared memory.
Inspect compiled REG/STACK/LOCAL/SHARED and selected SASS. Reject spills/large
stack or excessive barriers unless a documented exception precedes promotion.
Useful distance work is invariant. Saved traffic includes repeated flag passes
and intermediate compacted ID/float stores+loads; extra costs include single-CTA
tiled scan and barriers. Roofline hypothesis: serial count/launch-bound here,
not a claim that one CTA can saturate the device or scales to arbitrary lengths.
CUB collective scratch reuse follows the installed API and
https://nvidia.github.io/cccl/unstable/cub/developer/block_scope.html.

## Verification and measurement

GPU 0 only, RTX PRO 6000 Blackwell Server, CUDA 13.1.115 / driver 590.48.01,
sm_120; live idle/process check and existing nonblocking GPU lock. Do not change
settings or touch foreign jobs. Preserve originals, previous graph campaign and
all failed observations. Fresh separate scratch, standard original build flags.

1. Standalone selector test: zero/one/max candidate counts, partial tiles and
   512-boundary crossings, dense/sparse/zero predicates, nonidentity prefixes,
   poisoned inactive capacity, alternating large/small/zero states and pointer
   churn. Check count, every ordered ID/distance and output tail guard.
2. Full independent CPU byte-edit-distance membership/distance/count checks
   and same-round native A order at radii 0,4,256 for A/B/C/D/E. Radius -1 is a
   robustness probe for B/C/D/E only; original A has a retained zero-grid fault.
3. Fresh binaries: memcheck/synccheck for B/C/D/E; initcheck and racecheck for
   D/E; standalone selector memcheck/synccheck/initcheck/racecheck. Correctness
   precedes timing. Leak checking is excluded as in the comparator campaign.
4. Stress each B/C/D/E for 16384 changing queries, warmup 64. Six fresh-process
   radius-4 rounds, 4096 queries each, orders BCDE, EDCB, CEBD, DBEC, DEBC, CBED.
   Primary statistic: ratio of medians of process-mean completed-query wall time.
   Also report p10/p50/p90, exact paired-bootstrap 95% interval of log ratios,
   order split, process wins, CPU time/query, first query and setup separately.
5. Sustained checks at radii 0,4,256: 16384 queries, orders BCDE and EDCB.
   All six primary C/E rounds must favor E, paired lower bound >1.05 and every
   sustained C/E and B/D row must avoid >5% regression for admission. Scope
   remains this bounded prototype; missing production gates limit promotion.
6. NSYS node traces for C/E after clean gates: first+64 warmup+128 timed queries;
   verify removed kernels, same unchanged phase signatures and host copies.
   Profiler durations are diagnostic, never the public latency denominator.

Per-query wall scope includes input staging/copy, device work, completed host
count/ID/distance delivery, but excludes output hashing. Loop CPU includes hashes.
Setup/capture/tree construction are not silently moved into the hot-loop result;
report them separately. Same stream/Graph copies and full 2220-slot capacity for
B/C/D/E. Abort on mismatch, runtime failure, foreign GPU activity or harness
limits; signal only owned process groups. Raw order/logs/reports remain excluded
from Git with reproducible hashes and curated evidence. No broad paper claim.

## Collection closure (append-only)

All 90 preregistered observations completed; the hot-query admission gates pass.
Full-output, sanitizer, stress, clean timing and NSYS evidence are separate.
The original eight source hashes and previous comparator remain unchanged.
The first build via a relocated nvcc launcher failed header resolution before
GPU work; use the actual toolkit executable. Raw failure is retained.

Limitation discovered in the inherited driver: load/tree-construction is not
independently timed. Setup, capture, first query and process-before-cleanup are
retained, but no cold-start or whole-program claim is admitted. The accepted
scope is the declared completed hot query, not full cold-start attribution.
No production, concurrency, larger-tree or dynamic-update promotion.
