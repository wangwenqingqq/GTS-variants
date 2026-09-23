# Preregistered pivot-locality screen

Recorded before candidate implementation and execution, 2026-09-23.
Experiment: `gts_20260923_pruning_locality_screen_l2_2000`.

## Question and novelty boundary

The previous dimension-major layout destroyed root-pivot spatial locality.
Test two alternatives without changing arithmetic or thread ownership. Generic
row-major/AoSoA layouts are established engineering controls, not novelty claims.
The negative prior result is retained; this screen does not rescue a paper thesis.

## Frozen contract

Reuse the exact GIST/Deep/Tloc float32 fixtures, 64 query IDs, four radii and CPU
float64 oracle from `pruning_layout_20260923` at a184d7a. N=2000, dimensions
960/96/2, immutable height 3, fanout 10, batch one, full stable host results.
Source pins and all distance expressions, loop/reduction order, child predicates,
thread-to-child mapping, level boundaries and query vectors remain unchanged.
No pow replacement, distance reuse, warp cooperation, batching or approximation.

Modes: E/D original pruning; S/U metadata SoA; L/V previous dimension-major
layout; R/B compact row-major pivots; T/C tiled pivots. First letter is Graph,
second stream. All use the common fused-result driver. Native A anchors outputs,
not performance against an untouched executable.

R stores 11 pivots as [parent][dimension]. T stores the root alone, padded to a multiple of
8 floats; the 10 other parents occupy three tiles of 4 parents, each dimension
block containing [4 parents][8 consecutive dimensions]. Final parents/dimensions
are zero padded. T offset for parent g>0 is root_span +
(((g-1)/4)*ceil(D/8)+j/8)*32 + ((g-1)%4)*8+j%8.

Both retain SoA metadata. Primary attribution is S/R and S/T; E/R and E/T assess
net gain relative to native pruning. R/T separates contiguous from tiled packing.
L is a newly remeasured diagnostic negative control, not a primary selection arm.

## Design and costs

All kernels retain one 512-thread CTA per query/level, one thread per child flag.
No new shared state or query barrier. Each thread owns its existing accumulator,
metric temporaries, node and loop index; only addressing adds group/tile offsets.
Packing finishes before capture, immutable buffers remain live through all query
completion, and free follows synchronization. No producer/consumer overlap.

Expected: R/T restore root and within-vector sector reuse; R compacts scattered
pivots, T groups four nearby parent rows in 8-coordinate blocks. Unlike the old
transpose, neither is expected to reduce one instruction's pivot sectors much.
Counterhypotheses: original caches already suffice; index arithmetic or padding
cost outweighs locality; unchanged scalar math dominates. Measure setup/bytes
and first-query separately; never credit packing as free.

## Device and safety

Admit physical GPU 0 only after fresh UUID check: RTX PRO 6000 Blackwell Server
Edition, 188 SMs, CUDA 13.1.115, driver 590.48.01, existing 600-W limit.
Other GPUs 1-4 are occupied and excluded. No clocks/power/driver settings changes;
locked-clock state is not independently established. CPU shared/unpinned.
One existing GPU-0 advisory flock surrounds every stage; existing monitored
runner checks processes nominally every 200 ms and records 100-ms telemetry.
These are sampled safeguards, not proof of exclusive access. Abort only owned
children on interference, preserve failed runs, and do not silently replace them.
Use a new scratch root; previous source, binary, data and observations remain intact.

## Gates and screen

1. CPU address bijection/bounds/padding checks for all shapes and kernel source
   inverse-transform equality. Compile with identical -O2 sm_120 flags; record
   resource and selected-function SASS/container hashes. Validate native function
   against the previous same-toolkit binary; different SASS is an attribution caveat.
2. Full outputs at -1/0/normal/all for E/S/L/B/R/C/T plus A at nonnegative radii.
   CPU exact membership and declared distance tolerance; directly compare ordered
   float32 bits. All five pruning variants must agree per level (128 cases/radius).
3. memcheck/synccheck/initcheck/racecheck for E/S/R/T; memcheck/synccheck for B/C.
   Stress 4096 normal-radius completed queries after 64 warmups for E/S/R/T/B/C.
4. Four fresh-process primary rounds, 512 queries/process after 64 warmups.
   Orders ESRT, TRSE, RTES, SETR: every pair has two runs in each order.
   Public estimator median process-mean completed-query wall latency including
   transfers and host completion, excluding build/layout/setup/capture/hashing.
   Retain every sample, p10/p50/p90, process wins, order splits, exact 4^4 bootstrap
   of paired log ratios. Record loop CPU/wall, not sampled CPU attribution.
5. One forward and reverse normal-radius 4096-query sustained screen: ESRT/TRSE.
   No all-hit/zero long-duration matrix in this screen. A promising follow-up
   requires all gates, four primary wins, bootstrap lower >1.03 vs E AND S, and
   no >5% normal sustained regression. This is not production promotion or proof
   of all-radius performance; weak gains are inconclusive, not universal rejection.
6. Same-binary NSYS for E/S/R/T: 2x64 queries, 64 warmups, node trace. First-query
   NCU two stream pruning launches D/U/V/B/C, same eight sections and cache/clock
   control none. Preserve per-level counters. Replay durations are diagnostic only.

No required observation is dropped. Contamination stops the screen; no opportunistic
GPU change or automatic retuning. Publish portable code/curated evidence only;
raw datasets, profiler reports, process details and machine state remain private.

### Pre-timing control clarification

L/V is remeasured only through full-output correctness and first-query NCU, not
through a new clean completed-query timing arm. No historical L latency enters
a ratio in this screen. The four primary modes remain E/S/R/T.

### Pre-execution admission amendment

Before any GPU process or measurement in this campaign, GPU 0 became reserved
by another workflow audit under the same account. Two admission attempts
failed (lock busy, then compute process present); neither launched this binary.
Do not touch that job. The user has authorized other idle cards. A fresh idle and
nonblocking existing-lock probe admitted GPU 5 of the same model/driver/toolkit.
All observations now use GPU 5 only, with its existing advisory lock. This replaces
the physical GPU-0 admission above; no measurements select the device, no
cross-device ratio is allowed, and further interference stops this screen.
The setup/admission failure logs are retained separately from measured receipts.
