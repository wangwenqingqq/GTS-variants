# GTS exact-L2 tree versus dense Tensor Core continuation (2026-09-23)

State: designed before implementation and timing. Parent evidence: 642a37f,
`tc_leaf_probe`. No production dispatch or source originals are modified.

## Gate 0 / decision
The previous real-candidate replay found only 1.106-1.242x TC/SIMT component
speedups, with 34.34-40.72% tile fill and weak pruning. TED-JOIN already covers
indexed shared-candidate TC Euclidean distance; generic mapping is not novel.
This follow-up is a cheap falsification test, not an attempt to rescue a
subsumed thesis with a small implementation speedup.

Test both: (1) does TC improve the full GTS query over the SAME integrated SIMT
control? (2) does retaining the tree beat a simple exact dense TC scan?

## Frozen workload / hardware / outputs
- Same first 65,536 SIFT vectors, 128D integer [0,255], query IDs floor(i*N/Q),
  Q={32,128}, radius={300,500}. Reuse and verify the previous fixture hashes.
  Smoke N=2,000/Q=32/r=300. Include self, exact per-query range counts on CPU.
- GTS source commit 3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639, 18-file pins.
  MAX_H=5 for N=65,536 and native 3 for N=2,000; MAX_SIZE=20 unchanged.
  All tree variants retain the 256 MiB bounded workspace and native traversal,
  level scans, candidate formation, allocations/frees, and synchronization.
- Physical GPU0 only, live UUID and process checks, shared GPU0 advisory lock.
  RTX PRO 6000 Blackwell Server Edition, driver590.48.01, CUDA13.1.115.
  Preserve the foreign GPU6 process, original source, datasets and old scratch.
  No clocks/power changes. Blocking CUDA wait policy for all variants.
- FP16 inputs / FP32 TC products and accumulation under the exact integer proof
  in the parent contract. Not arbitrary FP32, cosine, edit distance or ANN.

## Four paths, one driver
O: resource-adapted original GTS query, including native leaf processing and
nested result counting. Reference, NOT the attribution control for Tensor Cores.
S: same GTS traversal plus the parent coalesced SIMT distance/count kernel.
T: same GTS traversal plus the parent WMMA distance/count kernel.
D: no tree traversal; directly scan all points with the SAME WMMA kernel using
flat contiguous 16-point tiles and all-active masks. No search index/pivots/pruning
are needed for D. This is a simple dense control, not optimized cuBLAS or a SOTA
nearest-neighbor library. A faster D is sufficient to falsify tree necessity on
these shapes, not to establish the fastest dense algorithm.

S and T both translate the live native query/leaf lists to the shared compact
index layout on GPU every call. T additionally clears/builds active masks.
D has static identity point IDs, flat-tile descriptors and all-active masks;
this is fixed O(N) tiling metadata, not data-dependent index construction.
All packed FP16 operands are produced within the TC kernel, not prepacked free.
S/T use the original live data, not captured/replayed candidate lists.

## Denominators
Primary: monotonic host wall time from query dispatch to the counts being
available in a CPU vector, including query allocation/free, traversal, scans,
list translation, mask work, conversion/padding, distance/count, synchronization
and result copy. Free the original managed result allocation inside the wrapper
on every call to prevent native result leaks across repeated queries.

Common file loading, context initialization, independent full-table CPU oracle,
index build, static metadata/norm preparation and warmup are outside warm-query
timing. Report their phases separately; do NOT add component medians to fabricate
cold-start totals. D executes in the same driver/process with the same loaded
vectors, but does not use the tree. Its cold startup is not measured in isolation.
Diagnostic printing within native query is suppressed identically for O/S/T.
Secondary: same-scope CUDA-event span (may include CPU gaps), main-thread CPU
clock, and calls/kernel times from one optional Nsight trace. Wall time remains
primary; this is not a kernel-only denominator.

Six fresh processes per shape, predeclared balanced orders: OSTD, TDOS, SODT,
DTSO, DSOT, TOSD. Each path occupies every ordinal position once or twice and
each paired precedence is balanced 3:3. 5 warmups/path, 20 retained batch-1
queries/path, then 5 batches of 16 calls/path, each delivering CPU counts.
Validate every timed result OUTSIDE its timed scope. No Graph/concurrent-stream
claim. Correctness, then memcheck/synccheck for all five shapes; initcheck and
racecheck on the small shape; repeated queries before/after timing.

Estimation: geometric mean of process-median ratios, paired process bootstrap
95% CI (10,000 draws, seed0), marginal ratio and order/process distributions.
Record all observations and rejects. Tree-TC continuation requires T faster
than S by >10%, lower CI >1, >=5/6 process wins, sustained nonregression, AND T
no slower than D on the same shape. If D is faster by >10%, lower CI >1,
>=5/6 wins and sustained nonregression, reject tree necessity for that shape.
Report every shape even if it fails. No post-timing kernel tuning.

## Design / ownership / resource card
Reuse parent WMMA16x16x16 FP16/FP32 kernel: one warp/CTA owns an output tile;
8 KiB operand shared memory +1 KiB result staging, eight synchronous K steps,
fill -> syncwarp -> fragment load/MMA -> store -> syncwarp -> masked counts.
No new async barriers, pipeline stages, clusters or TMEM. Operand fragments die
each step; accumulator persists for eight; no shared operand overwrite within
CTA. SIMT has four warps/CTA, warp-per-point, four shared integer counts and one
CTA barrier. GPU list translation has independent pair writes. Static maps,
norms, tiling descriptors and reusable bridge buffers have one driver owner and
are released after all queries. No persistent cross-query counts or masks.

Expected cost: native host/UM/allocation traffic can dwarf the small leaf gain.
Dense adds candidate distances but removes tree control and fills whole tiles.
Verify launch geometry/tails, static resources and actual TC instructions on
SM120; the parent is not proof for a newly linked binary. Stop after this one
mapping. No full-system/general-tree claims without further evidence.

Execution card: new task worktree/branch and matching new remote scratch only;
GPU0 no foreign apps before/after every process; logs/receipts/binary hashes
retained. Abort on foreign GPU0 use; never signal another user's process.
Rollback is removal of task-owned copies only, on request. Publication excludes
raw data, generated upstream source, machine configuration and private paths.

## Appended outcome (2026-09-23; frozen design above unchanged)

All five shapes passed exact-count validation, memcheck and synccheck; smoke
also passed initcheck and racecheck. All 24 fresh timing processes completed,
with every output checked and all 2,400 observations retained. No timed kernel
was tuned after seeing performance. All four tree-TC continuation gates failed;
all four dense-control gates passed. Q128 S/T performance is bimodal and
order/process-dependent, so no stable TC attribution is accepted. The current
implementation is not promoted. This does not reject every tree or the TC
mechanism in another workload. See README and the claim ledger for exact scope,
negative results, diagnostic limits and the unexecuted next control.

Clarification of the repeated-query denominator: each group reports the mean of
sixteen separately timed, CPU-delivered and validated calls, with event/check
gaps. It is not an uninterrupted throughput interval. All public latency numbers
exclude setup/index build; D's standalone cold startup was not measured.
