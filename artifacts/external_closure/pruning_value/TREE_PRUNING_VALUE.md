# Tree pruning value: measured diagnosis, not a new system speedup

**Decision: prioritize insufficient GPU-block-level selectivity of the current
partition/summary interface.** Inefficient native leaf execution compounds the
problem; maintenance also amplifies costs, but cannot explain away a query path
that already loses without updates. This is a scoped research decision inferred
from the tables, not a proved universal cause for GPU trees.

The next interface must make a **cheap, safe rejection correspond to complete
physical verification blocks**, rather than merely generating scattered object
candidates. No such new index has been implemented or admitted here. The earlier
leaf early-exit/invariant-hoisting proposal is paused, not falsified.

## Frozen task and gates

GIST: **1,000,000 live FP32 vector occurrences, D960, B1**, original radius
`0x3f34a3d8`. Initial and first-rebuilt snapshots each use their original 32
queries; the two query sets differ, so their times are not before/after speedups.
P remains PAR_STRONG/FULL/TILED, arity10, leaf20, threshold10. Range walks the
actual tree; current FULL kNN scans the complete live set and is not pruning kNN.
All results below use dimension-ordered FP64 sub/mul/add, squared-radius
membership, complete occurrence IDs and bit-exact FP32 sqrt fields.

Eleven registered GPU processes completed: bounded capture, bounded four-mode
check, four sanitizer tools, two target captures, two target four-mode checks,
and one missing-second-rebuild **build-only** supplement. All **3,904** delivered
query answers (including warmups/sanitizers/repetitions) passed full membership
and field checks. Target oracle distances were reused, not regenerated or fed
into online candidates. Actual rebuilt nodes/order/safe bounds exactly match
prior qualified dumps at the first two snapshots. All **113 original GPU
functions / 76,152 normalized instructions** are unchanged in the timing binary;
only one score-to-range-output adapter is added. No new distance kernel.

Hardware: one RTX PRO 6000 Blackwell Server Edition, sm_120, nominal96GB,
CUDA13.1.115 / driver590.48.01. The preferred GPU became occupied before admission; **zero**
experiment children launched there. Under standing idle-card authorization the
entire campaign used one idle same-model GPU with verified NUMA locality.
Two-sided ownership guards passed. No foreign
process was stopped; clocks/power were not changed. GPU isolation is not exclusive
Host isolation. The old external matrix used a different same-model card.

## Table 1: decisions, pruning and reference-only explanation

Values are **means per query** over32, separately by snapshot/layer. A layer only
subtracts newly rejected nodes that were actually tested; ancestor rejections
are never counted again. Early leaves stay in the unresolved frontier. Root
seeding is not a bound test. Pivot calls and unique query/pivot identities are
measured separately; they coincide per layer here, not by assumption.

| Snapshot | Layer | Tested nodes | Pivot calls | Newly excluded occurrences | Unresolved occurrences | Kept nodes with a true hit | Kept nodes without any hit | Observer traversal interval ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| initial | 1 | 10.000 | 1.000 | 87,500.000 | 912,500.000 | 1.344 | 7.781 | 0.502 |
| initial | 2 | 91.250 | 9.125 | 67,187.500 | 845,312.500 | 2.688 | 81.844 | 0.490 |
| initial | 3 | 845.312 | 84.531 | 59,593.750 | 785,718.750 | 6.469 | 779.250 | 0.491 |
| initial | 4 | 7,857.188 | 785.719 | 44,209.375 | 741,509.375 | 22.000 | 7,393.094 | 0.621 |
| initial | 5 | 74,150.938 | 7,415.094 | 31,577.500 | 709,931.875 | 83.781 | 70,909.406 | 4.265 |
| first_rebuilt | 1 | 10.000 | 1.000 | 275,000.000 | 725,000.000 | 1.219 | 6.031 | 0.501 |
| first_rebuilt | 2 | 72.500 | 7.250 | 35,312.500 | 689,687.500 | 1.781 | 67.188 | 0.489 |
| first_rebuilt | 3 | 689.688 | 68.969 | 40,531.250 | 649,156.250 | 5.344 | 643.812 | 0.491 |
| first_rebuilt | 4 | 6,491.562 | 649.156 | 25,168.750 | 623,987.500 | 23.375 | 6,216.500 | 0.550 |
| first_rebuilt | 5 | 62,398.750 | 6,239.875 | 21,642.500 | 602,345.000 | 106.531 | 60,127.969 | 3.638 |

The last column is an **instrumented observer stream interval**, not a performance
sample or pure kernel-active time. Do not add it to Table2 or add CPU waits again.
No-hit membership comes from bottom-up minima of existing exhaustive reference
scores over actual node members. A kept no-hit node is an opportunity the current
summary failed to certify, not evidence that an inexpensive stronger bound exists.
Nested no-hit object counts must not be summed across layers. Per-query, layer,
subtree-size, and unique-pivot records are retained in the CSVs.

| Snapshot | Mean candidate occurrences | Candidate fraction | Mean true hits | Mean reached32-row blocks | Fraction of32-row blocks | Mean reached256-row blocks | Fraction of256-row blocks |
|---|---:|---:|---:|---:|---:|---:|---:|
| initial | 709,931.875 | 70.993% | 205.938 | 29,587.438 | 94.680% | 3,886.031 | 99.463% |
| first_rebuilt | 602,345.000 | 60.234% | 388.406 | 29,617.469 | 94.776% | 3,889.750 | 99.558% |

Blocks are `floor(physical_row/32)` and `floor(physical_row/256)` in the original
row order used by the packed mirror, not tree-order intervals, cache lines,
measured DRAM transactions or bytes. Duplicate vectors remain separate candidates.
The original1M rows contain **982,694 distinct bitwise FP32 vectors** (17,306
repeated rows): every repeated SHA256 digest was checked against full coordinates.
Lineage IDs alone therefore were **not** used as vector-content identity.

Candidate counts vary substantially: initial12,340–872,520; first-rebuilt
9,650–843,660. This is not a claim that every query visits almost everything.
Nevertheless even the sparsest observed candidate set touches most256-row
blocks (initial minimum3562/3907, rebuilt3422/3907).

## Table 2: identical arithmetic, actual candidates, complete output

Each entry is the median of four **sums of32 individual Host-ready query
intervals**, in one process per snapshot. Frozen orders are T,N,B,S / S,B,N,T,
repeated twice, after8 warmup queries per mode. This is not a continuous pass,
a six-process significance estimate, or a sustained-workload result. The Host
interval includes query-vector H2D, complete result D2H and native temporary
output release. Retained client answer vectors, cache loading, layout setup,
service teardown and disk persistence are outside; their costs are recorded.

| Mode | Initial ms /32queries | First-rebuilt ms /32queries | Interpretation |
|---|---:|---:|---|
| TREE_NOW | 687.061808 | 594.672145 | Actual tree frontend + original leaf verifier + full output |
| REPLAY_NATIVE | 479.644050 | 409.940743 | Diagnostic only: actual precomputed leaf list; no frontend |
| REPLAY_BLOCK | 207.485444 | 207.352380 | Diagnostic only: identical candidate mask + existing packed FULL verifier |
| SCAN_MATCHED | 216.583486 | 216.539718 | Existing packed FULL verifier, all live objects + same full-range output adapter |

**REPLAY rows are not end-to-end algorithms or system speedups.** Original
leaf replay remains slower than matched full scan. Reusing the existing packed
core greatly reduces native candidate-execution cost, but replay-block saves
only about4.2% of matched full-scan query time before paying for candidates.
Its remaining headroom is about9ms per32queries; current TREE_NOW frontend
stream intervals total203.772/181.458ms. This is an execution-screen observation,
not a bound on a future redesigned tree.

The non-observer TREE_NOW verification intervals are462.257/392.904ms;
REPLAY_NATIVE462.479/393.008ms; REPLAY_BLOCK196.583/196.791ms;
SCAN_MATCHED206.003/205.990ms. Event0 is after H2D; event intervals include
stream/dispatch gaps and must not be called pure GPU-active time or added to
Host time. All individual samples/order and phase times remain in CSV.

### Costs deliberately outside replay, not allowed to disappear

| Snapshot | Packed mirror + workspace setup ms | Packed owned bytes | Cache load/upload ms | Cache device bytes | Offline CPU candidate expansion/check ms |
|---|---:|---:|---:|---:|---:|
| initial | 14.201259 | 3,858,000,264 | 25.291143 | 44,800,000 | 10788.435480 |
| first_rebuilt | 14.153786 | 3,858,000,264 | 25.148128 | 44,800,000 | 8800.775602 |

Per snapshot, cache storage is32MB of physical candidate masks plus12.8MB of
native leaf lists, with another Host copy during upload. The observer copied
339,911,040 bytes of node/pivot/object/active/leaf records, excluding tree dumps
and normal answers. Offline Python expansion includes validation and is **not**
an optimized online task-builder estimate. A deployable path must charge actual
online construction/publication, masks and any layout maintenance.

Packed storage is AoSoA32, with no candidate compaction. REPLAY_BLOCK launches
all3907 CTAs, each with256 lanes, even when a whole block is masked out. Inactive
lanes do not request object coordinates; no additional *logical noncandidate*
distances are computed. It still publishes N scores, reads the N-byte mask,
and loads query data per CTA; sector/cache overfetch is **not measured**. Physical
block reach is not a DRAM-byte reduction claim. The all-live scan uses exactly
the same original184-instruction verifier, not an intentionally weak new scan.

All modes share the resident frozen tree and packed mirror within a process.
Tree diagnostic setup (including dump I/O) is3615.650/3579.819ms; combined
service/cache release77.316/76.878ms. These are harness costs, not a claimed
standalone scanner build time. A future dynamic layout must pay real updates.

### Strong native external evidence is retained

The existing native-FP32 cuVS complete-range matrix reports110.486709/
110.415453ms per32-query continuous pass; the new ordered-FP64 matched scan is
about216.6ms under a different diagnostic harness/card. This cross-campaign
contrast makes arithmetic/backend choice a plausible part of the external gap,
**not** a same-round estimate of a pure FP64 penalty. It does not assign the
whole tree deficit to arithmetic. The existing formal dynamic P/E medians remain
6.386079/1.297195s, E/P0.202847, P wins0/6. Faiss/cuVS controls are not discarded.
See [external range](../EXTERNAL_RANGE_RESULTS.md) and [dynamic P/E](../PE_RESULTS.md).

## Maintenance: why unchanged data do not imply reusable derived state

The original336-event trace/state records were replayed on CPU using immutable
occurrence IDs and byte-verified vector-content IDs. Original two snapshot
lineages match exactly; only the missing second-rebuild tree was supplemented,
with **zero queries**. No threshold search or workflow rerun.

| Existing rebuild step | Actual insert/delete requests since prior rebuild | Net entering-buffer / removed-base occurrences | Surviving rows whose physical address changes | Full vector copy | Build distance pairs | Safe-refit pairs | Exact stable region+pivot reusable at any old node |
|---:|---|---|---:|---:|---:|---:|---:|
| 48 | 10 /10 | 10 /10 | 977,398 /999,990 | 1,000,000 vectors /3.84GB payload | 5,000,000 | 5,000,000 | 9 /111,111 |
| 216 | 20 /20 | 10 /10 | 966,193 /999,990 | 1,000,000 vectors /3.84GB payload | 5,000,000 | 5,000,000 | 12 /111,111 |

The second interval contains20 inserts/20 deletes, including buffered occurrences
deleted before rebuilding; its net entering/deleted-base set is still10/10.
The remaining trace tail has10 inserts/10 deletes and no further rebuild.
Each rebuild also republishes1M vectors into the packed mirror (another3.84GB
payload; read+write traffic is not measured here). At corresponding heap slots,
all111,111 member sets change; all111,110 nonroot pivot coordinate contents
change. There are no merely address-changed, otherwise identical regions at
those slots. Across **all** old node addresses,9/12 exact member-and-pivot regions
remain possible reuse opportunities, not zero. Content-identical previously
computed build pairs account for571/447 of the new5M evaluations (384/186 when
requiring identical occurrences). These work counts are not cache speedups.

The current pointer/epoch contract retires all old bounds. Failing a stable-ID
sufficient reuse test does not prove every old numeric interval unsafe; subset
or approximate region matches are not exhaustively searched. No old bound was
reused online. The measured instability comes from changed partition/pivots after
global rebuilding, not just renumbering; a generic cache cannot simply retain
all old state. Threshold10 is an unchanged mechanism control, not a tuned
maintenance baseline or grounds for inflating a future maintenance claim.

## One next design boundary, with no novelty promotion

**Primary category: summary/partition selectivity at the physical-block boundary.**
The current tree saves29–40% of object checks on average, yet nearly all256-row
blocks remain involved. Most surviving leaf regions have no reference hit, but
an affordable safe way to prove this remains unknown. Execution organization is
a demonstrated secondary penalty; maintenance is a further constraint, not the
reason to skip resolving query value first.

The next single design must couple (1) a bounded-cost conservative certificate
with (2) stable, explicitly owned physical verification blocks. The interface
that changes is the relation among `target::Bounds`, region membership,
`leaf_slot/slot_pid`, and block-task publication, not just another fused launch.
Keep separate occurrence IDs, content IDs and physical addresses; invalidate a
certificate on relevant membership/pivot/layout changes and preserve the exact
full-output contract. Never inject oracle minima into the online certificate.

Before implementation, identify the nearest block-aware metric-tree prior art
and run a cheap novelty kill test. Multi-pivot bounds, packing, caching and cost
models alone are not new: [GTS](https://arxiv.org/abs/2404.00966) already supplies
pivot-tree/table execution and a cost model. The present work is an experiment
that rejects an overly broad gain expectation, not proof of a novel mechanism.
If no distinct cheap certificate/ownership invariant survives that gate, stop;
do not rename ordinary engineering or launch a larger matrix to rescue it.

A future candidate must beat P and strong native scan under one same-task short
workflow, charging layout, task generation, copies, updates and output. Before
that: prove safety, bound construction/update cost, and test held-out queries.
No new default,10K/100K, six-round matrix or private paper change is authorized
by this diagnostic result. Existing R/P13.423096x and T/P6.448319x remain scoped
internal evidence; R is the jointly repaired reference, not untouched GTS.

## Evidence and calibration

`CONTRACT.json`, `evidence/FINAL_PROOF.json`, `evidence/RAW_MANIFEST.json`, per-query
CSV, four raw observations per mode and maintenance provenance bind this result.
The final checker was hardened after independent read-only review: partial
payload bytes, invalid time values and incorrect capture order are rejected;
actual replay masks are reconstructed from the observed leaf/object membership.
Original executed drivers are retained privately and hash-bound. Original runner
admission lacked individual pre/post cache hash receipts; final reconciliation
checks launch commands, binaries, parent source, retained hashes and timestamps.
The improved future runner adds those receipts. This is not a claim that stricter
receipts were collected retroactively, and **no GPU sample was rerun**.

| Claim | State | Allowed scope / material counterevidence |
|---|---|---|
| Large candidate set and almost complete256-row block reach | measured | These64 range queries at two N1M/D960 snapshots; not all GPU trees |
| Native candidate execution has a substantial mapping/granularity penalty | partial | Same-candidate diagnostic replay; generation/setup excluded |
| Current summary/partition interface is the primary next research target | inferred | Chosen from query evidence; cheap improved certificate still unknown |
| Rebuilds with10 entering/10 removed base occurrences reconstruct all derived state | measured | Two existing threshold10 rebuilds; not a tuned-policy superiority claim |
| A redesigned certificate/block owner beats native scan end-to-end | unknown | No implementation or same-task measurement; no new speedup claim |
