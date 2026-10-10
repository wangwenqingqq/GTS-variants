# Design card — static certified-navigation diagnostic

## Boundary and hypothesis

Target: RTX PRO 6000 Blackwell, sm_120a. GIST 1M x 960 FP32,
K8/B1, immutable original GTS tree. No updates, external vectors, Graph or
kernel fusion are admitted. G0 is repaired true-tree V2, not an unchanged
upstream result and not a full scan.

Hypotheses: G1 saves repeated pivot/leaf coordinate work; G2 retains distinct
cross-layer real witnesses to lower the native traversal upper bound; G3 is
the factorial combination. Cache traffic, allocation, clearing, candidate
insertion, final duplicate removal, sorting, and synchronization are charged.
The CPU-only model predicts ~1.1% fewer full distances for memo and very small
additional leaf savings for candidates; that is not CUDA or latency evidence.

## Role / state / readiness ledger

| Phase | Owners | Live state | Ready / release edge |
|---|---|---|---|
| getDisPQ | Native thread per query/pivot family | FP64 score, row, optional memo slot | Default stream completion before threshold and node readers |
| nav_update | One thread, B1 only | G0/G1 native O(1) Kth read; G2/G3 persistent distinct K<=32 witnesses | Completed current-level distances -> conservative upper bound |
| nodeProcessKnn | Native thread per query/node | FP64 distance/bounds, parent flag | Current upper bound -> active child flags |
| leaf | Native CTA per region, object threads | FP64 score, optional memo slot | All previous pivot phases complete before memo read |
| output | Native flattened leaf slot + K witnesses | `(score,id)` keys; common score-by-row workspace | Exact full score -> lexicographic sort -> full Host result |

Tree sibling pivot owners are distinct within each level; object owners are
unique in leaves. Setup rejects duplicate same-level owners. A CPU ownership
audit checks exact sibling coverage, ID permutation and unique leaf ownership.
Query state never survives a query: fresh allocation and tags replace rollover.
Static storage epochs are represented by immutable pinned snapshots, not a
claim of dynamic invalidation support.

No shared memory, TMA, tensor cores, cluster barriers or new async handoffs.
Register peak is expected in the K-key single-thread candidate merge; it must
be treated as an added serial cost, not a free oracle. Native traversal,
Host stack, Thrust pivot sorts, and native synchronizations are preserved.

## Common repairs (not new-mechanism gains)

- RN FP64 ordered subtract/multiply/add on original FP32 input; FMA disabled.
- FP64 squared score and lexicographic static-instance ID selection.
- FP64 upper bounds; +infinity until K valid witnesses (legacy finite sentinel is not a candidate); widened native split intervals, full object coverage
  validation; failing interval disables only that bound.
- Complete K IDs and FP64 scores exported before query workspace release.
- Existing pinned adapter: tree height 6, fixed 1 GiB workspace, no timed prints.

Inputs are checked finite and within [0,2]. D<=960 and this range bound each
subtraction, square and sum far from FP64 overflow/underflow (including the
smallest FP32 inputs); a conservative gamma_(3D) accumulation estimate plus
RN sqrt is below 1e-10 absolute L2 error. The 1e-6 distance envelope is wider.
The 0.01 split widening is *not* assumed from samples: every original region's
objects are checked at setup against the interval with this error envelope.
Uncertified bounds keep the region. The proof is confined to the input envelope
and immutable validated tree, not universal metrics or arbitrary FP32 values.

## Reject / stop gates

Any full result, score-bit, cache value, witness legality or same-semantics trace
mismatch stops admission. Diagnostic timing is not a public ranking. All E2
small/boundary/invalidation/stress/sanitizer tests are required before E3.
No E3 or E4 expansion without evidence supporting the declared >=10% gate.

Nearest prior art already contains triangle bounds and current-level pivot
thresholds (original GTS, arXiv:2404.00966; M-tree, VLDB 1997). Generic memo,
candidate sets and triangle certificates are not novelty claims. This campaign
is a cheap same-contract mechanism falsification, not a paper thesis promotion.
