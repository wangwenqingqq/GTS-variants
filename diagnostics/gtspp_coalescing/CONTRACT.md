# GTSPP operator/coalescing campaign — 2026-09-23

Baseline is archive/GTS_incremental, source pins from diagnostics/cpu_io, not
original upstream GTS. Its node/leaf L2 already uses multiplication and sqrtf.
Parent delivery 4dedd85. Correct the prior recommendation: repeating the pow
change is not new GTSPP work. Generic warp-cooperative reductions are prior art;
this is engineering attribution, not a new contribution/novelty claim.

## Phase 1, frozen before measurement
Use the original archived GTSPP headers with native height computation, padding,
MAX_SIZE=20, native kernels and synchronizations. Only bound range workspace to
256 MiB and mute two query prints identically. Reuse the independent integer
oracle and disjoint host-stage clocks from query_breakdown. Data: SIFT N65,536,
128D float storage of integers [0,255]; Q32/128, r300/500; smoke N2,000/Q32/r300.
Exact counts include self; no learned kNN path, update, IDs or general-float claim.
Full query dispatch to CPU count delivery includes allocation, initialization,
all operators, waits and cleanup; excludes loading, oracle, build and warmup.
Keep CUDA default waiting unchanged; record actual schedule bits.

Admission: PRO 6000 Blackwell GPU0 only, UUID verified live under the shared
/tmp/gtspp_gpu0.lock. CUDA13.1, driver590.48.01. Preserve originals and foreign
processes. All execution has task-only timeout, pre/post idle checks. sudo is
only for authorized NCU with clock-control none; no driver settings changes.
Record source/fixture/binary/tool hashes and raw order; retain failed attempts.
First check smoke and Q128/r500, run sanitizer, then baseline timing/NSYS to
choose an operator. A stage profile is diagnostic, not an optimization result.

## Predeclared leaf control, conditional on material leaf cost
If leaf stage is at least 20% of baseline query wall, test B against baseline A:
change only numeric L2 leaf ownership from one-thread-per-point to one-warp-per-
point. Same blocks, 512 threads/block, candidates, output flag layout, buffers,
other kernels and CPU waits. Consecutive lanes read consecutive coordinates
from the existing AoS vectors; warp shuffle reduction replaces serial summation.
No data repack, TC, changed metric or root-removal. Other metrics retain the
original branch and are outside the experiment. This is a coupled ownership /
coalescing / reduction change, not a pure memory-transaction intervention.

Roles/live state: warp owns one leaf point at a time; each lane has a float
partial and coordinate addresses; lane0 writes exactly one result flag. Sixteen
warps/block stride through MAX_SIZE slots, writing zero for absent points. All
32 lanes of each participating warp execute each shuffle with a full mask.
No shared-memory object, cross-warp handoff, new launch or host/GPU wait.
Ready graph: point loads -> lane partial -> five shuffles -> lane0 sqrtf/store
-> existing kernel completion -> unchanged result aggregation. Added work:
shuffles, metadata duplication, more useful lanes. Expected benefit: fewer
uncoalesced sectors/byte and shorter serial distance dependencies. Resource
and register changes are measured, not assumed absent.

For integer SIFT, squared differences and all partial sums are nonnegative
integers <=128*255^2=8,323,200 <2^24, so FP32 regrouping is exact. Keep sqrtf and
native <=radius comparison. Reject on any full-table count mismatch.

## Conditional A/B acceptance
Before timing B: source invariants, all five shape correctness, memcheck and
synccheck for both variants on smoke and primary Q128/r500; B smoke racecheck
and initcheck. Diagnostic-only if any required gate fails. Stress 64 repeated
queries per process on both variants/two endpoint shapes, validate every output.
For all four main shapes: six fresh-process pairs, AB/BA alternating, one
correct query +3 warmups +8 retained queries/process. Primary estimator:
paired geometric process-median A/B wall ratio with seed0 10k bootstrap 95% CI;
win only if lower bound >1.02 and B wins >=5/6 pairs. Retain p10/median/p90,
marginal ratio, order split, main-thread and process CPU, per-stage fractions.
Sustained scope: 64-query batches on two endpoint shapes, three pairs with
alternating order, aggregate timer plus every-query correctness outside batch.
No promotion across a sustained regression; no production/Graph/concurrency claim.

Same-round NCU A/B leaf + NSYS full query on Q128/r500 after correctness gates.
Record sectors/requests/bytes and caches, warp participation, scheduler/stalls,
resources and exact runtime functions. Profiler replay duration is never the
speedup denominator. Attribute CPU API waiting from NSYS separately from CPU
compute; do not add overlapping API waits to kernel duration. No CPU wait-policy
change is credited as acceleration. If leaf is not material, append a new
operator contract before changing a different stage; do not optimize blindly.

## Phase 2 amendment — frozen before candidate implementation

Phase-1 Q128/r500 baseline measured about 28.5 ms total, 4.4 ms leaf (about 15.5%)
and 22.2 ms aggregation (about 78%). The predeclared >=20% leaf trigger failed;
no leaf-warp candidate was implemented. The conditional candidate B and all
subsequent A/B acceptance gates now target ONLY mergeResRnn aggregation.

B maps one block to each query rather than one thread to each query. Preserve
512 threads/block, exact result segments/IDs, all flags, buffers, distance math,
tree, other kernels, launch count and native CPU synchronization. Change only
mergeResRnn body and its grid from ceil(Q/512) to Q blocks. Each thread sums
stride-512 entries of its contiguous query segment; warp shuffles reduce each
partial; 16 warp leaders store 16 ints in shared memory; one block barrier;
warp0 loads those 16 partials and reduces; lane0 alone publishes the result.
Every thread reaches the barrier; every lane of each executing warp reaches
all shuffles. Integer flags and sums remain exact under the bounded count
contract. Sums are bounded by the unchanged candidate-slot allocation (<2^31).

This is a coupled query ownership / parallel reduction / coalesced-read control,
not a pure coalescing experiment. Expected: adjacent lane addresses reduce
sectors per requested byte; distributing queries across SMs reduces serial
latency. Added costs: 64 shared bytes/block, one CTA barrier, two warp reductions,
more resident CTAs/metadata reads. Live state is one integer partial and segment
bounds per thread; shared warp sums live only across the one barrier. No
asynchronous object, cross-block handoff, extra allocations or extra CPU waits.

Readiness: flag producers finish under the original synchronization -> parallel
loads/sums -> warp partial publication -> CTA barrier -> warp0 reduction ->
result store -> original kernel synchronization and CPU delivery. NCU A/B
selection changes to mergeResRnn (first measured launch); NSYS covers the full
query. All original correctness, sanitizer, stress, timing and sustained gates
apply, including both endpoint shapes. Build both final binaries with the same
new stress/sustained driver before final collection. Preflight binaries/runs are
retained separately and are not a comparator for final speedup estimates.
