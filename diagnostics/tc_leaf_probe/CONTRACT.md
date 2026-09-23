# GTS leaf Tensor Core feasibility probe (2026-09-23)

State before implementation: designed. Baseline repository a37e3ee. This is a
component feasibility experiment, not a new tree algorithm or end-to-end claim.

## Gate 0 and hypothesis
TED-JOIN (HiPC 2022) already groups queries sharing spatial candidates for Tensor
Core Euclidean distance evaluation. Hummingbird and GPU graph-frontier work also
preclude claiming that tree/graph-to-matrix conversion alone is new. No novelty
claim is admitted here. Test whether real GTS leaf candidates provide enough
reuse to pay for sparse masks, padded work, FP32-to-FP16 packing, and counting.

## Frozen input and semantics
- Original author source: 3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639, 18-file pins
  reused from original_tree_redundancy. Never edit the original.
- First 65,536 SIFT base vectors, D=128, checked integer values in [0,255].
  Query IDs floor(i*N/Q), Q in {32,128}; range radii {300,500}. Four required
  shapes. Smoke: N=2,000, Q=32, r=300. No distribution tuning after timing.
- Capture actual query/leaf pairs after original mergeLNode. Native N=2,000
  MAX_H=3; N=65,536 MAX_H=5 resource-adapted, MAX_SIZE=20 unchanged. Bound native
  workspace to 256 MiB to avoid original signed-int workspace overflow.
- Compact leaf metadata and IDs are static exported index representation,
  shared by both variants. Candidate pairs are resident GPU inputs. Traversal,
  export/file I/O, initial upload/allocation, and static vector norms are outside
  query timing; report setup separately. No GTS end-to-end speedup inferred.
- Output: exact per-query range count, including self. Validate candidate
  coverage and native GTS counts against independent full-table integer L2.
  Also validate every sparse candidate's squared distance exactly (not just count).
- FP16 inputs and FP32 dot products are exact under this integer contract:
  dot <=128*255^2=8,323,200, norms sum and twice dot <=16,646,400 <2^24.
  No floating-point approximation or correction is needed here; this proof
  does not apply to arbitrary floats, cosine or edit distance.

## Variants and denominator
A: SIMT, one 128-thread CTA per active (query,leaf), a warp per point, coalesced
128D loads, shuffle reduction, block-local count and one atomic query update.
B: synchronous WMMA 16x16x16 FP16/FP32. Build leaf/query bitmasks from the SAME
candidate pairs every call. Launch one warp per (leaf,16-query-group,16-point
chunk), skip empty groups, gather and convert native FP32 vectors into shared
memory, zero-pad, execute 8 WMMA steps, mask invalid pairs, recover squared L2
and count. No free precomputed per-query grouping, no host sorting in B.
Both include output clearing/counting. B additionally includes mask clear/build,
packing/padding/recovery. Allocation reuse is identical. Default stream, no
Graphs, no concurrent streams. No library comparator needed for this feasibility
probe; it is not a claim against optimized GEMM libraries or state of the art.

Primary timer: CUDA events for the complete resident candidate operator.
Secondary: host wall time including launches and event synchronization. Per-process
CPU rusage captured by runner; it is not a CPU attribution profile.
Warmups 20; 100 retained batch-1 observations and 20 batches of 64 consecutive
calls, per-call event time. Six fresh processes per shape, balanced AB/BA orders;
keep all observations, processes, hashes and negative results. Validate both
variants before timing. Require memcheck, synccheck, initcheck, racecheck on the
small case plus memcheck/synccheck on the largest case before promotion. Repeated
calls and fresh processes cover buffer reuse; Graph support is explicitly absent.

Decision: continue only for a shape with geometric process-paired A/B ratio
>1.10, bootstrap 95% lower bound >1.0, at least 5/6 process wins, and sustained
ratio >=1.0. Every required shape must be reported. A losing prototype does not
reject all Tensor Core mappings. Stop after one mapping; do not tune against
observed results. End-to-end integration remains a separate future gate.

## Design/resource card
Target: physical GPU 0, RTX PRO 6000 Blackwell Server Edition, SM120; CUDA13.1.115,
driver590.48.01 (freeze live state in receipts). Advisory lock plus idle/process
checks before/after each process; stop if foreign GPU0 work appears. Shared host,
foreign GPU6 job must remain untouched. No device settings changed.

WMMA ownership: one warp owns one 16x16 output tile. A/B shared operands occupy
8 KiB, output staging 1 KiB. No async pipeline/cluster/TMEM/barrier tokens. One
warp fills shared arrays -> syncwarp -> load fragments -> synchronous mma ->
store fragment -> syncwarp -> count -> warp reduction -> atomicAdd. Shared
operands are never overwritten within a CTA. Accumulator persists for eight K
steps, operand fragments die each step. Shared output becomes readable only
after store+syncwarp. Peak live registers are accumulator+one A/B fragment+
address state, measured by ptxas, not assumed. SIMT uses four shared integers
for warp counts, one CTA barrier. Unique CTA writes optional diagnostic distance
slots; exact pair uniqueness is checked on CPU.

Hypothesized saved work: reuse queries and points across active leaf pairs.
Added work: padded 256-cell tiles, static empty tile dispatch, mask traffic,
shared FP16 conversion/packing and norm recovery. Estimate fill as useful
candidate distances / executed 256-cell tiles; distinguish empty skipped CTAs
from issued WMMA tiles. Small cases may be launch-bound. A full dense tile can
still lose to conversion/feed overhead. Store resource/SASS and measured work
ledgers with results; do not substitute instruction counts for latency.

Rollback: remove only task-owned scratch if requested; no production dispatch,
original source, dataset, GPU settings, or other process is modified.

## Append-only execution outcome (2026-09-23)

All required shapes completed. No kernel candidate tuning/replacement occurred
after timing. All four pass the predeclared continuation gate, not a production
or novelty gate. See README/EVIDENCE for exact estimators and missing integration
gates. Optional Nsight Systems attribution was collected only after paired timing.
One source-anchor preparation failure and one zero-error sanitizer stdout-parser
failure were retained and repaired before timing; neither was a CUDA mismatch.
