# Original GTS pivot-distance and candidate audit

This is the preregistration-time source audit. Later runtime evidence is in
`WORK_COUNTS.json`, `VALIDATION.json` and `RESULTS.md`; pending language below
describes the audit checkpoint, not the latest collection state.

## Identity and scope

Upstream: `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
All eight caller-supplied upstream source hashes were checked before changes.
The complete-ID adapter is the existing sibling
`native_knn_faiss_ivf_20261003/prepare_gts.py` and `gts_bench.cu`, not the later
FULL/BOUND range executor. G0 and G1 share MAX_H=6, fixed1GiB workspace,
complete sorted-ID extraction, and disabled timed console output.
No old timing is used as the new denominator.

## Findings from the pinned source

| Mechanism | State | Exact flow |
|---|---|---|
| Same sibling pivot shared during kNN | Already present | `tree.cuh:198` assigns siblings one object ID; `getDisPQ` (`search_v2.cuh:646-755`) computes once per sibling group; `nodeProcessKnn:170-214` reads the saved group distance. No fanout10 claim for this path. |
| Pivot distances retained for node bounds | Already present | `p_list_k[offset_p + ofst/3 + i]` is a **double**, containing the full Euclidean distance. The FP32 node-bound conversion is a separate consumer and must not become the cache value. |
| Encountered pivots used to tighten kNN upper bound | Already present | `searchIndexKnnV2:1087-1109` sorts encountered group pivot distances, then `updateDisK:759-782` takes kth and only decreases `disk[qid]`. Therefore G2 is not a missing-mechanism control and is removed; G3 collapses to G1. No cross-level union or alternative bound is introduced. |
| Leaf reuses the saved full pivot-object distance | Real gap | `dataProcessKnn:422-546` looks up `id_list[node.lid+did]` and calculates the full distance again, except for self-ID. It does not consult pivot distance tables. |
| Object identity shared between different layers | Real gap, small structural opportunity | Original query tables are keyed by layer/group, not a persistent query/object pair. CPU inspection of the pinned1M index finds one repeated object across evaluated pivot layers; actual active repetitions remain to be measured. |
| Partial leaf L2 early exit | Absent in this baseline | Each non-self valid leaf object computes all960 dimensions before testing `result > disk[qid]`. Do not call padding or already-pruned nodes a distance calculation. |
| Pivot/leaf arithmetic bridge | Source-equivalent; runtime gate pending | Both use a double accumulator, FP32 input subtraction, `pow(delta,2)` and `pow(sum,0.5)` in the same dimensional order. Cache stores double before the leaf's existing disk filter. A bitwise GPU bridge is required before promotion. |

The current-level pivot IDs are distinct in the pinned real index. This matters
because original kth-pivot bound code counts groups, not a general deduplicated
candidate heap. Do not silently generalize its legality to arbitrary externally
edited indexes containing alias groups. New G1 must retain the same bounds.

## Cheap falsification screen

The fixed index has111,111 allocated nodes and100,000 disjoint leaves. If every
evaluated group is live, levels3/4/5 compute100/1,000/10,000 pivot distances:
11,100 calls for11,099 distinct object IDs. Against a no-pruning full-leaf scan,
the maximum reusable share is11,100/(1,000,000+11,100) = **1.0978%** of complete
distance calls. This is a structural arithmetic opportunity, **not** a measured
latency upper bound: pruning changes the denominator and cached pivots may not
reach leaf verification. Measure the fixed32-query active work before expansion.

## Decision

Retain G0/G1 only. Do not weaken original pivot-bound use to manufacture G2.
Caching is a conventional mechanism, not a novelty claim. GPU correctness,
32-query active counts and complete confirmation cost remain pending.
