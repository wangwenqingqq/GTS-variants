# Current-P Fixed3 results (2026-10-11)

**Accepted as a narrow PAR range dispatch prototype:** same complete logical
336-event workflow, exact outputs/work, six fresh balanced processes per mode.
This is an incremental engineering win, not a new thesis or external closure.

## Complete unprofiled workflow

| Variant | Geometric mean complete trace | Meaning |
|---|---:|---|
| P0 | 6.171187 s | current PAR_STRONG/FULL/TILED keeper, one range leaf /256 threads |
| P1 | 6.183837 s | one range leaf /32 threads |
| P2 | 5.268155 s | three canonical range entries /32 threads |

| Paired comparison | Geometric ratio | 95% paired bootstrap | Candidate wins | Decision |
|---|---:|---|---:|---|
| P0/P1 | 0.997954 | [0.994428, 1.001761] | 2/6 | shrink alone inconclusive |
| P1/P2 | 1.173815 | [1.169506, 1.177715] | 6/6 | packing incremental win |
| P0/P2 | 1.171413 | [1.166083, 1.175006] | 6/6 | current-P complete-workflow win |

The confidence interval describes process-to-process variation on this fixed
trace and GPU, not workload/GPU population generalization.

The denominator is summary.trace_ms: all 336 serialized events, full host-ready
ID/field delivery, uploads/allocations/synchronization, updates, two rebuilds,
refits, refreshes and final drain. Cold setup, separate real warmup, oracle,
counters/profiler and file writes are excluded identically. This is NOT the
original-GTS fixed256 static kNN denominator. All raw rounds, marginal ratios,
relative-order splits and component ACK distributions are retained in evidence.

## Component attribution (arithmetic mean per-process totals)

| ACK component | P0 | P1 | P2 |
|---|---:|---:|---:|
| Range (128 requests) | 2590.622 ms | 2593.851 ms | 1681.948 ms |
| FULL kNN (128 requests) | 860.303 ms | 861.006 ms | 860.729 ms |
| Insert (40, includes rebuilds) | 2636.001 ms | 2639.482 ms | 2639.840 ms |

These sums are formed INSIDE each process and then averaged, never a sum of
component medians. The observed gain localizes to range; FULL kNN and rebuild
cost remain. Mean CPU user time over the observer's trace-plus-drain rusage
window falls from 5.914 s to 5.011 s, but this does not establish less CPU
algorithmic work: CUDA synchronization/spin can contribute. No CPU-flamegraph
or “all GPU trees have CPU redundancy” claim follows from this experiment.

## Mechanism and invariants

Two reverse NSYS rounds show leaf-inclusive totals P0/P1/P2:
- forward: 1758.292 /1759.346 /811.339 ms;
- reverse: 1717.860 /1718.808 /808.726 ms.

Actual range leaf launches stay 128. Configured CTAs fall from 12,800,000 to
4,266,752. The lists are canonical ALL-leaf lists with inactive -1 entries,
not compacted visited leaves. Materialization/traversal stays unchanged.
Counter sidecars are byte-identical across all three modes: 10,060,090 node
tests; 1,006,009 pivot evaluations; 8,667,952 visited leaves; 86,679,420 leaf
distance objects; 83,212,243,200 distance dimensions in the measured 128 ranges.
The logical adapter uses nonindexed query rows, verified before interpreting
its non-self object counter as the full leaf distance count.

The measured target's canonical leaves all have size 10. Active-group histogram
(0/1/2/3 active leaves) is 1,316,547 / 50,680 / 81,303 / 2,818,222. Actual-object
slots divided by configured active-CTA lanes are source-derived 31.24996%
(P1) and 91.81504% (P2), NOT measured hardware occupancy/issue efficiency.
Packing also intrinsically loads one shared query per active group instead of
per leaf; this staging reduction was predeclared and priced. No DRAM/L2 byte
saving, instruction count or pure scheduling-only causal decomposition is
claimed. NCU was denied (ERR_NVGPUCTRPERM); no policy bypass was attempted.

## Validation and preserved failures

48 main wrapper processes completed plus one registered permission probe.
Nine real-kernel unit processes each cover 4800 cases: ALL leaf sizes 1..20,
D128/D960, tails, inactive groups, deleted objects, identity-distinct equal
vectors, exact radius boundaries and pointer churn. P1/P2 memcheck, racecheck
and synccheck passed both the actual kernel unit and bounded mixed workflow.
Bounded outputs use exhaustive CPU scores; all target processes compare complete
logical outputs/field bits to the pinned prior-qualified reference. Warmup and
measured states are checked separately. CPU-only UNIT_PAYLOAD_CLOSURE additionally
validates EVERY byte of all nine unit outputs; no additional GPU run.

The first build failed the user-shared gate because cuobjdump includes the
keeper's additional 1024-byte overhead; the amended bound preceded runtime.
After 21 qualifiers passed, the controller stopped because it accidentally
froze its own mutable run.log. Only this log drifted. A separate recorded
continuation requalified existing receipts offline and ran only the remaining
original budget, without rerunning/replacing any qualifier. Original failures,
recipes and all observations remain in the private raw archive. Closure checks
all external data/reference and all source/binary/resource/SASS/output pins.

## Boundary and next action

FULL kNN, TILED build, pruning, arithmetic and updates are unchanged. This
result does not establish Safe-C1 correctness, D96/K1/K32 coverage, N1M full
sanitizer admission, concurrency, Graph, production closure or superiority
over the external GPU baseline. The inherited whole-program leak is not fixed.
The prior strong external gap is not erased by an internal 1.171413 ratio.
Keep Fixed3 as the scoped range candidate; next remeasure the strong external
baseline under this exact complete-workflow contract before promoting a thesis.
