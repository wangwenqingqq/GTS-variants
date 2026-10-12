# Rebuild change amplification results

**Decision: NO_GO_LOCAL_MAINTENANCE.** Sparse mutation triggers dense work, but
almost all canonical tree organization really changes. This is not evidence that
most tree/refit work merely regenerates identical state. KNN packing is a separate
semantic redundancy opportunity, conditional on physical-layout handling.

One exact GIST N1M D960 replay, two actual rebuilds at zero-based events 48 and
216. No timing conclusion, external rerun, maintenance prototype or optional GPU
repeat. Full ordered measured/warmup IDs and FP32 fields, event/query semantics,
final occurrences and rebuild decisions match frozen P2. Four complete snapshots
are compared on CPU. See summary/RESULT.json and POSTPROCESS_CLARIFICATION.md.

## Main tables

“Changed” is canonical POST state absent/different in PRE, unless marked raw.
Each row has its own units; do not pool these denominators. All-live positions
include pending-to-base moves. Numeric canonical changes include changed ownership,
not a claim that every floating-point value differs. Plan work is regenerated
final-payload cardinality, not executed scalar-store instructions.

### R1

| State | Total | Actually changed | Reprocessed | Amplification |
|---|---:|---:|---:|---:|
| Logical occurrences (mutation-window unique touched IDs) | 1,000,000 | 20 | N/A | N/A |
| All-live physical positions | 1,000,000 | 977,408 moved | 1,000,000 rows compacted | 48,870.4 moves / touched ID |
| Leaf memberships | 100,000 | 99,982 | 100,000 | 1.000180 |
| Pivot ownership references | 111,110 | 111,110 | 111,110 | 1.000000 |
| Node topology | 111,111 | 111,111 | 111,111 constructed/refitted | 1.000000 |
| Numeric refit scalar state (ownership-aware) | 222,222 | 222,222 | 222,222 | 1.000000 |
| KNN pack coordinates (occurrence-aligned POST) | 960,000,000 | 9,600 new | 960,000,000 | 100,000.0 |
| PAR plan scalar content (canonical) | 2,283,344 | 2,283,117 | 2,283,344 | 1.000099 |

### R2

| State | Total | Actually changed | Reprocessed | Amplification |
|---|---:|---:|---:|---:|
| Logical occurrences (mutation-window unique touched IDs) | 1,000,000 | 30 | N/A | N/A |
| All-live physical positions | 1,000,000 | 966,203 moved | 1,000,000 rows compacted | 32,206.767 moves / touched ID |
| Leaf memberships | 100,000 | 99,985 | 100,000 | 1.000150 |
| Pivot ownership references | 111,110 | 111,110 | 111,110 | 1.000000 |
| Node topology | 111,111 | 111,111 | 111,111 constructed/refitted | 1.000000 |
| Numeric refit scalar state (ownership-aware) | 222,222 | 222,222 | 222,222 | 1.000000 |
| KNN pack coordinates (occurrence-aligned POST) | 960,000,000 | 9,600 new | 960,000,000 | 100,000.0 |
| PAR plan scalar content (canonical) | 2,283,344 | 2,283,153 | 2,283,344 | 1.000084 |

Physical “amplification” above divides moves by unique logical mutations, not
compaction by moves. Compaction/moves is 1.023114 / 1.034979 (R1/R2). Comparing
logical updates with work alone cannot establish redundant execution.

## Q1. What logical mutations precede each rebuild?

| Window | Inserts | Deletes | Events | Unique touched | Net live-set change | Live before / after |
|---|---:|---:|---:|---:|---:|---:|
| Initial publication -> PRE_R1 | 10 | 10 | 20 | 20 (0.002%) | 20 (0.002%) | 1,000,000 / 1,000,000 |
| POST_R1 -> PRE_R2 | 20 | 20 | 40 | 30 (0.003%) | 20 (0.002%) | 1,000,000 / 1,000,000 |

R2 includes ten inserted occurrences deleted again before publication. Their
IDs are counted once in unique touched, and disappear from net live-set delta.
All insertion/deletion IDs are retained in RESULT.json and snapshot metadata.
Across PRE -> POST itself the logical set is identical: rebuild creates/deletes
zero logical occurrences. PRE includes ten pending rows and ten base tombstones.

## Q2. What occurrences move or change leaf membership?

R1/R2 each has 999,990 common live **base** occurrences. Of these, 977,398 /
966,193 move, while 22,592 / 33,797 keep their row. Ten pending occurrences also
move from request scratch rows into base, giving all-live move rates 97.7408% /
96.6203%. Ten tombstone rows disappear; ten pending occurrences are admitted to
base. These admissions are not new logical occurrences at the rebuild.

Among common live base occurrences, 999,810 / 999,840 change exact canonical leaf
membership (99.9819998% / 99.98499985%). Only 180 / 150 stay in identical leaf
membership. Tombstone-filtered PRE membership gives the same primary rates.
No pointer, numeric node ID or leaf ID is used as identity.

## Q3. How many leaves, pivots and nodes really change?

Only 18 / 15 of 100,000 leaves have identical sorted occurrence membership:
**99.982% / 99.985% change**. All 111,111 nodes have changed ownership/pivot/child
structure; fully unchanged and numeric-only changed nodes are both zero.
Even the 18 / 15 matched leaves use different pivots.

The exact-first, overlap-greedy descriptive inventory is:

| Rebuild | Unchanged | Modified correspondence | New unmatched | Removed unmatched |
|---|---:|---:|---:|---:|
| R1 | 18 | 94,498 | 5,484 | 5,484 |
| R2 | 15 | 94,437 | 5,548 | 5,548 |

The modified correspondence is not persistent identity or optimal matching.
Primary exact-match rates and the decision do not depend on this heuristic.

The root split pivot occurrence changes **499999 -> 500006 -> 500012**.
Only 142 of 11,110 prior distinct pivot occurrences survive in R1's pivot
inventory; R2 retains 126 of 11,109. Source selects the middle occurrence of the
reset/sorted physical order, not an update-stable immutable pivot. This supports
an organization-instability diagnosis, but does not causally isolate pivot
selection from subsequent sorting/tie behavior. No counterfactual kernel was run.

## Q4. What numeric, packed and plan state changes?

Each rebuild writes 222,222 FP64 refit scalar entries. Raw positional comparison
finds 211,109 changed bit patterns and 11,113 identical ones. Because every
canonical topology changes, **none** of those raw equalities is admitted as
same-dependency numeric redundancy. There are zero same-topology numeric-only
comparisons; all scalar state is classified under changed ownership.

Pack32 physically changes 937,510,467 / 926,759,931 coordinate slots (97.6573403% /
96.5374928%). But after occurrence alignment, **all surviving coordinates are
bit-identical**: 959,990,400 entries (99.999%) are regenerated unchanged; 9,600
new entries are admitted and 9,600 old entries removed. The POST-change denominator
is 9,600; symmetric insert+delete coordinates would yield amplification 50,000,
not 100,000. This semantic redundancy does not prove in-place reuse under the
current dense row-compaction contract is correct or faster.

PAR canonical content changes 2,283,117 / 2,283,153 scalar entries (99.9900584% /
99.9916351%). Raw integer slots change only 999,998 / 999,999: many ordinal/count
slots retain the same number while referring to a different canonical subtree.
No vector-container or device pointer is compared. Per-vector denominators and
raw/canonical deltas are retained in RESULT.json.

## Q5. How much maintenance work is actually regenerated?

The two rebuilds each execute the following source-derived task inventory from
captured runtime split flags, sizes, actual node predicates and exact loop bounds:

| Work | Per rebuild | Evidence type |
|---|---:|---|
| getNewData candidates | 1,000,010 | Exact candidate loop cardinality |
| Compacted output rows / coordinates | 1,000,000 / 960,000,000 | Exact live-row and D loop count |
| Temporary full D2D bytes | 3,840,042,240 | Actual copy extent |
| Construction pivot-scoring distance tasks | 5,000,000 | Five captured active level dispatches |
| nodeSplit boundary-distance tasks | 111,110 | Ten children per 11,111 active parents |
| Total construction distance tasks | 5,111,110 | Previous two distinct task families |
| Full sort API input slots | 5,000,000 | Five full-N calls; radix internals unknown |
| Constructed nodes / leaves | 111,111 / 100,000 | Root initialization + active split children |
| Refit node outputs / distance tasks | 111,111 / 5,000,000 | Actual valid node/pivot predicates and member sizes |
| KNN packed regenerated coordinates | 960,000,000 | Exact pack32 per-row dimension loop |
| PAR regenerated final-payload scalars | 2,283,344 | make_plan assigns/pushes all final payloads |

Construction processes one million unique objects: 50,000 / 33,333.333 objects
per unique touched mutation. Pivot scoring alone is 250,000 / 166,666.667 tasks
per mutation. These logical-denominator ratios are large, but construction per
changed-membership common object is only 1.000190 / 1.000160. Neither API input
counts nor payload cardinalities are profiler instruction counts.

## Q6. How much is recomputed but identical?

| State, canonical denominator | R1 identical | R2 identical |
|---|---:|---:|
| Leaf membership | 18 / 100,000 | 15 / 100,000 |
| Complete node topology + numeric state | 0 / 111,111 | 0 / 111,111 |
| Refit scalar state under identical topology | 0 / 222,222 | 0 / 222,222 |
| KNN surviving coordinate content | 959,990,400 / 960,000,000 | 959,990,400 / 960,000,000 |
| PAR scalar content | 227 / 2,283,344 | 191 / 2,283,344 |

For node attribution, A (observed direct mutation dependency) is 49 / 48, B
(changed matched node with no direct dependency) is 18 / 15, U (changed unmatched
node, old dependencies unknown) is 111,044 / 111,048, and C is zero. Deleted old
dependencies cannot be inferred for unmatched nodes. U is not proof that its
change is transitively required. Pack and Plan C measure content equality, not
causal necessity or a correct skipping algorithm.

## Q7. Does this support selective/incremental maintenance?

**No under the frozen local-maintenance gate.** Both rebuilds exceed the 70%
NO_GO threshold for leaf and node changes, and fail the <=20% GO threshold and
>=70% same canonical structural-state criterion. GO/STRONG_GO are rejected for
this trace; do not average the huge coordinate denominator with tiny structural
units to manufacture a pass.

The next falsifiable question is why the current organization is so update-
unstable, and whether stable organization/layout can preserve useful state under
this same trace. That question needs prior-art screening before mechanism design.
KNN delta packing is a separately scoped candidate requiring a row-identity and
correctness contract; no prototype was implemented here. These results neither
cover all GPU trees nor prove incremental maintenance is universally impossible.
