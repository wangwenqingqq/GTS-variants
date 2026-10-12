# BASELINE_FIXED_MEMORY_LIMIT

## Q1 — Same-contract non-padded baseline?

**Yes, on the frozen tested scope.** GIST N1M/D960, FP32 row-major,
L2Unexpanded differences, B1, radius bits0x3f34a3d8, initial snapshot and original
fixed32 queries. All40 qualification/measurement queries per process have exact
complete membership/order against ordered FP64, with0 FN/FP. Inclusive flags,
CUB compaction, all declared fields, charged observer and full D2H are unchanged.
Native three-payload bit identity is enforced. N1 reduction order differs: its
maximum ordered-FP64 field-scale error is9.6225663e-8 and native-scale difference
2.0785190e-6, both below5e-5. N1 is **not native-bit-identical** and this is not
an all-input FP64 exactness proof.

Gate0 selected PathC only after no matching callable complete-output unexpanded
route was found in the inspected current/release sources. Direct B1 reduction
is ordinary baseline engineering, not a new search contribution.

## Q2 — Work inflation≤1.5?

**Yes:1.045154568×**, versus native64.022229941×. Predicated-on dynamic
FADD+FMUL+2×FFMA divided by2.879G useful scalar operations/query. This excludes
integer/control work and counts no READ_ONLY search inflation. Each result is
one independent first-measured-query NCU capture, not a sampled work CI.

## Q3 — Latency near READ_ONLY?

**Yes:2.569716 vs2.517427 ms/query, ratio1.020770690.** Native was3.345378ms.
Recovery93.68455954%, matched-round95% CI[93.27975795%,94.11596634%]. Residual
0.052288703ms is2.03480472% of N1. The process-paired N1/N0 geometric ratio
is0.767829562,95% CI[0.759850374,0.775864497],6/6 wins. Forward/reverse ratios
0.766167821/0.769494908 agree in direction.

Primary timing is Host request ready→complete Host output ready, including
query H2D, distance, threshold, full materialization/fields/D2H and completion.
Context, disk, one-time build and profiler overhead are excluded. Ratios of
medians and paired geometric ratios are different estimators, both disclosed.
Native identity/counters reproduce; its timing is not claimed identical to the
historical3.26–3.32ms range.

## Q4 — Remaining gap: memory or compute?

**The tested scan is close to the reachable streaming frontier.** N1 main-kernel
DRAM1530.511GB/s approaches READ_ONLY1532.455GB/s; native1160.115GB/s.
N1 SM throughput11.97%, active-warps85.35%,37 registers, no selected-function
spill/shared/barrier. These diagnostics and the small ACK gap support the
memory-frontier interpretation, **not a proof that every residual microsecond
is memory,3.84GB is mathematically unavoidable, or every GPU tree is bounded
this way**. READ_ONLY performs a checksum/reduction/scalar transfer and is not
a universal lower bound. Bandwidth recovery99.47802703% has no sampling CI.

## Q5 — Frozen decision

**BASELINE_FIXED_MEMORY_LIMIT**:

- inflation1.045155≤1.5;
- recovery93.6846%≥70%;
- N1/R0=1.020771≤1.15.

Original point thresholds are unchanged. Human clarified uncovered outcomes
remain `UNCLASSIFIED`, with no forced classification or follow-on direction.
The old padding campaign remains `PARTIAL_PADDING`: a stronger replacement
changes ownership/reduction/memory scheduling together and does not retroactively
pass that campaign's failed traffic-separation gate.

## Dynamic integration, failure and recovery

Static gates admitted one336-event old/strengthened E_ADAPT pair. The device
kernel stayed unchanged; only the host N ceiling was extended1,000,000→1,000,040
for capacity, with actual maximum live1,000,009 (warmup included). kNN, norms,
updates, ID bookkeeping, outputs and timers were unchanged.

The first old output triggered a postrun kNN check failure at event9. Offline
diagnosis found P reference IDs already represent stable logical occurrences,
while the inherited supplied-reference checker assumes live ranks. A bijective
CPU ID conversion preserved all fields and members; original old output also
matched historical E output bytes. All256 measured+8 warmup queries and final
state then passed. The failure and original registration were retained; after
explicit human approval only the remaining strengthened process was launched.

Trace1336.345387→1233.270291ms, reduction7.71320775%, speedup1.083578674×.
Range ACK sum431.204220→329.552427ms; kNN862.761123→862.702277ms. This is one
forward pair without CI, not sustained evidence or a GTSPP system gain.
The original trace denominator includes release/bookkeeping, and excludes
setup/context/disk/output-file serialization. No long workflow was started.

## Implementation / mechanism / thesis decisions

- **Implementation:** qualified artifact-local B1 baseline. No production
  dispatch installation, all-shape guarantee or Graph qualification.
- **Mechanism:** low inflation and measured same-contract ACK advantage.
  No padding-only causal attribution or64× latency claim.
- **Thesis:** B1 specialization is not novelty. Admit only representation
  Gate1 falsification; no compression/TC/pruning/hierarchy implementation now.

Reopen if a matching upstream primitive becomes callable, any required member
fails at a new query/update boundary, a required sustained shape regresses, or
safe representation work demonstrably reduces charged total bytes without a
same-contract end-to-end advantage. Do not rescue a subsumed thesis by packaging
this baseline repair as innovation.
