# Current-P residual costs and selected branch

## Decision

**Select branch 2: do not expand the current P to a 10K matrix.** The qualified
short dynamic service still loses to E_ADAPT: paired E/P 0.202847, CI95
[0.201070, 0.204578], P wins 0/6. See [formal results](PE_RESULTS.md). This does
not erase the direct internal R/P 13.423096x result; it rejects the extrapolation
that the present combination supplies net value beyond a strong GPU scan on this
GIST N1M/D960/B1 workload. R is the common repaired reference, not untouched GTS.

The selected **next cost question** is range-leaf distance verification after a
candidate can already be rejected. Only a causal engineering probe is designed
below; no new variant, speedup, novelty claim or additional GPU campaign is
admitted. Do not run both this and a sustained-workload branch.

## A: evidence on the current P, not the historical slow baseline

Existing six P processes were reused without rerunning the 18 R/T/P jobs. The
median own-trace shares were query.tree 40.527%, rebuild.construct 20.574%,
rebuild.compaction 11.338%, and update safe-refit 10.765%. These are inclusive
Host intervals and independently taken medians, not additive removable budgets.
The new P/E results likewise show large range and rebuild-containing insert
ACKs, whereas kNN ACK sums are much closer. Update-tail latency matters: only
two rebuild-triggering insertions can dominate a short workflow's insert total.

One independent NSYS/counter process ran on the original P parent. Its warmup
and measured 336-event complete IDs/fields match the pinned keeper. An extra
atomic per active parent CTA and profiling perturb the timing. Only the measured
`native.trace` span is selected; its duration is 6438.100376 ms. These numbers
are **diagnostic GPU durations, not the formal end-to-end denominator**.

| GPU stage | Calls / launches | Total diagnostic ms | Interpretation |
|---|---:|---:|---|
| `rex::verify_materialized` | 128 | 1793.454460 | Range leaf verification; exact candidate/dimension counts not yet instrumented |
| `getPivotDisTiled` | 10 | 1199.096333 | Real rebuild distance work; tiling changes ownership, not distance count |
| FULL `verify_distances` | 128 | 844.274756 | kNN exact verification; different queries are not automatically reusable work |
| `rex::parent_groups` | 640 | 811.498884 | Traversal, pivot distances, radius normalization and probe atomic together |
| `target::refit` | 2 | 686.255065 | Post-rebuild safe bounds; changed pivots/membership invalidate old bounds |
| `getNewData` | 2 | 487.649854 | Rebuild vector compaction/copy, not an invariant-state cache opportunity |

### Radius normalization: a real repetition, not yet its isolated benefit

The probe counted **1,006,009 actual `radius_upper` invocations** for one distinct
radius/dimension pair. At D960, source semantics execute 963 directed multiplies
per invocation: **968,786,667 inferred multiply operations**. This is a
source-plus-call-count inference, not a dynamic SASS instruction counter.
Only one normalization value is mathematically required for the fixed pair.
Its isolated time remains unknown; the whole 811.499 ms parent stage includes
other work and cannot be called removable normalization time.

Valid reuse would execute the *same GPU function* once per radius/dimension
lifetime, then publish/read its result. A parameter change invalidates it; scalar
storage, launch/fence, argument/load and refresh costs must be charged. It is
ordinary invariant hoisting, not a new index. Do not prioritize it merely because
it is easy: the measured leaf stage is larger than the entire parent stage.

### CPU occupancy is mostly a dependency question, not a CPU-math result

The selected span contains 770 `cudaStreamSynchronize` calls taking 2621.415466
ms inclusive Host time, 726 `cudaDeviceSynchronize` calls taking 2558.732719 ms,
852 `cudaMemcpy` calls taking 891.974752 ms, and 1620 `cudaFree` calls taking
205.504939 ms. These calls can include GPU waits; they must not be added to GPU
durations or interpreted as pure CPU arithmetic. This capture does not resolve
busy polling versus sleeping, cache-line traffic or coalescing efficiency. NCU
coalescing measurements were not taken in this campaign.

## C2: one causal question, with novelty and cost ceilings

**Question:** how much of the 1.793 s leaf-verification stage is avoidable suffix
arithmetic after ordered partial squared distance already exceeds the exact
range cutoff? The reject-prefix distribution and removable fraction are unknown.
The stage budget is evidence to test this question, not evidence it will win.

Five-part chain, stated as a hypothesis rather than a result:

> X: continuing coordinates of an already rejectable query/object pair is
> avoidable work (not a proven duplicate vector comparison). Y: for finite FP32
> inputs, the existing ordered FP64 sum of nonnegative squares cannot decrease.
> Z/M: a gated partial-distance check in the existing range leaf verifier may
> skip the remaining suffix after strict `partial > radius_squared`. U: query,
> radius or object changes invalidate the proof; no cross-query/update cache is
> proposed. W: measure skipped coordinates/loads and eligible lanes. C: charge
> predicate/divergence, control, register/live-mask and any extra synchronization
> cost. Net benefit remains unmeasured under the same complete workflow boundary.

Reuse the existing `verify_distances<Early>` principle in
`unified_search_update/kernels/knn_verify.cuh` before introducing a new abstraction.
The initial causal design is one on/off gate at the existing 32-coordinate check
interval, with candidate enumeration, storage layout and traversal held fixed.
Maintain the exact ordered RN subtract/multiply/add sequence; no reordering or
approximate cutoff. Equality continues, and accepted fields keep the original
sqrt/FP32 conversion bits. Nonfinite/generalized-metric support is not inferred.
Buffer verification remains unchanged in this first isolation test.

### Gate 0 kills a novelty claim, not the usefulness of a small diagnostic

Partial-distance elimination is established prior art, explicitly reviewed by
Ramasubramanian and Paliwal, *Fast nearest-neighbor search algorithms based on
approximation-elimination search*, Pattern Recognition 33(9), 2000,
[doi:10.1016/S0031-3203(99)00134-X](https://doi.org/10.1016/S0031-3203(99)00134-X).
The repository already contains analogous kNN early termination. Merely moving
it into range verification is therefore **not a new research direction or
contribution**; stop that novelty claim. No expensive campaign or manuscript
expansion should be justified by renaming it. A substantive, non-incremental
index/system thesis and decisive external advantage remain open requirements.

### Cheapest falsification and reopen conditions (not launched)

1. Separately register one bounded diagnostic of the frozen candidate stream,
   collecting first-reject coordinate distribution, total/eligible lanes and
   accepted-result count. Keep observation overhead out of performance timing.
   If most candidates reach the final coordinates, reject before an A/B campaign.
2. If supported, add only the on/off gate. Validate complete range members and
   field bits, threshold equality, duplicate vectors, empty results, update-buffer
   visibility, real rebuild boundaries and bounded sanitizer behavior against P.
   P's candidate stream and all non-target modules must remain identical.
3. Only after those gates, separately freeze same-campaign P-off/P-on/E timing
   and a finite process budget. Include every added cost and preserve rejects;
   kernel improvement alone does not admit end-to-end or sustained promotion.

Even deleting the whole diagnostic leaf stage would save only about 1.79 s,
less than the roughly 5.09 s observed formal P/E median gap. These are different
measurement scopes, so this is a rough impossibility check, **not a predicted
new latency**. A small engineering win cannot by itself rescue external
superiority or paper novelty. Negative/inconclusive results stay closed unless
a new mechanism or measured reject distribution supplies a concrete reason.

## Reproducibility and unchanged boundaries

The first bounded P checker failure, offline admission and all ten authorized
remaining qualifiers are retained. The first sample was not rerun. All 12 formal
records were rebound and rechecked offline. The diagnostic is separately bound
to its registration, build, sources, binary, trace and keeper output. Raw payloads,
NsYS files, recipes and runtime receipts remain private; sanitized hashes and
observations are published. No old static/RTP matrix, 10K sustained workload,
private paper, Overleaf project or foreign process was modified.
