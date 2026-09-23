# GTS fusion plan: ownership and readiness before implementation

Status: **source-derived design only**. No CUDA implementation, GPU run, compiled
resource claim, or measured speedup. The eight author CUDA files still match
commit `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Baseline observations come from
[the accepted original-flow campaign](README.md) and [the async audit](ASYNC_AUDIT.md).

## Decision

Fuse around a shared intermediate and its ownership domain, not around adjacent
launches. The strongest opportunities are **candidate selection** and **result
selection**: both separately count, prefix-scan, and scatter the same predicates.
A prefix scan can supply positions and the aggregate count together.

Preserve the many-CTA leaf-distance phase. Do not turn the entire query into one
CTA, introduce a hand-written grid barrier, or add an atomic append that silently
changes result ordering. For the bounded measured path, the eventual design is
three query kernels, or four if traversal and candidate selection are better
kept separate. This is a hypothesis, not an implementation or a speedup estimate.

This uses established block-scan, compaction and fusion techniques. It is an
engineering attribution/control, **not a novelty claim for GTS++**. A paper thesis
would require a separate nearest-prior-art gate and same-contract evidence.

## Frozen first design scope

- Original query-only update entry: qnum=1, Words N=2,000, inclusive r=4,
  MAX_H=3, TREE_ORDER=10, MAX_SIZE=20, original distance evaluation and pruning.
- `tree.cuh:339` bounds node slots at `(10^3-1)/(10-1)=111`. Candidate slots are
  bounded by 111, and per-candidate result slots by 20: at most 2,220 slots.
  Keep any original selected non-leaf slots with zero hits unless equivalence
  of removing them is separately proved; do not silently redefine the frontier.
- Maintain counts, IDs, distances, stable candidate order and stable result
  order, deletion filtering and the original ID-remapping rule. Do not reduce
  the task to count-only just because the existing executable prints counts.
- The prior campaign checked counts/kth distances, **not full IDs/distances**.
  Full materialized-output validation is a new required gate before any fusion
  performance result can be accepted.
- No insertion-buffer query, mixed update visibility, batched kNN, tree building,
  larger-height tree or full-dataset claim is admitted by this first design.
  A larger shape needs a separate dispatch/resource decision and fallback.

## Five strongly coupled groups

Locations below are in `GTS/include/` at the pinned author revision.

| Group | Original operations | Shared data / owner | Fusion decision and required boundary |
|---|---|---|---|
| F1: traversal | `initQnode`; repeated `findNextRnn` then `updatePnodeFlag` | One query owns its node flags; both traversal kernels already use one CTA/query | Fuse initialization and level loop within that CTA. Barrier after initialization, after every level's child decisions, and after parent clearing before the next level. Preserve pruning and empty-child conditions exactly. |
| F2: candidate selection | Host `reduce(query_node_list)`; `getQnodeCount`; singleton count scan; flag scan; `mergeLeafNode` | Same query-node flag vector determines count, rank and selected node IDs | One cooperative block scan/select produces ordered candidate IDs and count. qnum=1 makes the two counts identical and the count-prefix zero. F2 may join F1 only after its resource and final-flag readiness gates pass. |
| F3: leaf evaluation | `initRes`; `leafProcessRnnUpdate`; optionally leaf-local hit counting/packing | One leaf CTA owns a disjoint MAX_SIZE slot segment | Each slot owner writes zero or one exactly once after evaluating its predicate. Fuse initialization into this producer, including deleted, non-leaf and unused tail slots. Optional local compaction remains within the same leaf CTA. |
| F4: result selection | Host `reduce(qresult_idx)`; `getQresultCount`; singleton query-count scan; hit scan; `mergeResultRnn` | Same hit flags determine count and output offsets | After all leaf CTAs finish, one bounded query CTA performs a stable scan/scatter and publishes the count. Alternatively scan per-leaf counts if F3 emits locally packed hits. This is a cooperative algorithm rewrite, not nested calls to the old Thrust routines. |
| F5: final projection | `mergeResultRnn` output followed by `mergeTotalResult` ID remap and distance copy | Each emitted result owns one destination; ID map is read-only for the query snapshot | Apply the map when F4 emits the result and write directly to final output. The deletion prefix must already be ready. Insertion-buffer append needs its separately completed input; it is not covered by the three-kernel query-only target. |

### F1: the parent-flag write-after-read hazard

`search.cuh:38-141` tests the parent's flag to decide which children to visit.
`search.cuh:178-193` later clears that parent flag, conditional on the original
first-child/empty-node rule. Naively doing both in each thread lets one thread
clear a flag before its sibling threads have read it.

A legal schedule is:

```text
initialize this query's flags
block barrier
for each tree level, uniformly across the CTA:
    all child threads read parent flags and compute child flags
    block barrier                 # all parent reads have completed
    the original designated threads clear parent flags
    block barrier                 # next-level state is ready
stable-select surviving flags
```

All block threads participate even when a node is empty, pruned or out of range.
Keep the flag storage (111 int entries = 444 bytes before scan scratch) separate
from the distance DP state. Do not claim fusion fixes traversal's one-CTA/query
parallelism; it removes handoffs without shrinking an already matching owner.

### F2 and F4: count is already part of selection

For binary predicates `b[i]`, define `p[i] = sum(b[j], j<i)` and
`count = sum(b[i])`. A stable selection is exactly:

```text
if b[i]: output[p[i]] = input[i]
```

The same scan produces `p` and its aggregate. Separate reductions are not needed
to recover the same count. Current node-count duplication is visible at
`update.cuh:384-406` and `search.cuh:559-570`. Current result-count duplication
is at `update.cuh:421-430` and `search.cuh:574-585`.

Current result merging uses an inclusive prefix and adjacent-prefix comparison
(`search.cuh:607-630`). Exclusive positions plus the original hit predicate give
the same stable output, including hits crossing a scan tile boundary. Keep the
original IDs/distances for those hits; never read uninitialized miss payloads.

For at most 2,220 hit slots, one query CTA can process multiple ordered tiles
with a carry between tiles. A block scan does not require the entire array to
fit in one warp or to hold every payload in shared memory. Use the installed
block primitives rather than writing a new scan framework. The tiling cost and
single-CTA tail still need measurement; larger shapes retain hierarchical scans.

An alternative F3/F4 interface is `(leaf_count, leaf-local packed hits)`. F4
scans at most 111 leaf counts and adds each local rank to its leaf offset. Local
ranks and leaf offsets must preserve the original leaf-major/item-major order.
This changes both interfaces and must be declared as a coupled variant; do not
attribute its result to launch removal alone.

### F3: initialization belongs with the writer, not with a global reset

`initRes` currently zeros every potential hit slot, and
`leafProcessRnnUpdate` only changes hits to one. In the fused producer, the owner
of each of the MAX_SIZE slots computes a final predicate and writes it once.
Deleted records, unused tail slots, non-leaf candidate slots, no-hit and
self-match cases all require explicit behavior. Preserve the original distance
path and inclusive comparison; do not combine distance-arithmetic changes with
this fusion experiment. A per-leaf count uses a block/warp collective with a
valid participation mask, not an unsynchronized read of other lanes' flags.

### F5: push the projection into the final store

`update.cuh:97-115` does not recompute distances. For a tree result it writes
`id - is_delete_prefix[id]` and copies its distance. F4 can perform that same
mapping at its final store, avoiding the intermediate compacted result array
and the second read/write pass. The output offset and prefix epoch must be known.

The scan of `is_delete` at `update.cuh:601` is different: it depends on the tree's
delete state, not on query hit flags. Move it to state maintenance only when its
invalidation rules are correct. In the measured no-update path the flags stay
zero, making the tree-ID map the identity. For mixed updates, rebuilding or
maintaining this prefix and its cost are part of the contract, not free work.

## Proposed ready graph, and why it is not one mega-kernel

```text
query / tree snapshot + reusable bounded workspace
    K1: traverse + stable candidate selection
        -> candidate list + device candidate count
    [same-stream kernel boundary: all K1 writes ready]
    K2: multiple leaf CTAs, distance + final hit flags
        -> disjoint hit segments + payloads (optional local packed hits/counts)
    [same-stream kernel boundary: all leaf CTAs complete]
    K3: stable result selection + count + final ID projection/store
        -> final count + materialized IDs/distances
    completion before host consumption / reuse of this query's workspace
```

Keep K1 and K2 separate to change from one query owner to many leaf owners.
Keep K2 and K3 separate because the result spans independently scheduled leaf
CTAs. `__syncthreads()` cannot make all those blocks finish. A custom spin-based
grid barrier is not an acceptable substitute. Grid-cooperative/persistent designs
have residency and scheduling costs and are unnecessary for the first control.
See NVIDIA's [block and cross-block synchronization rules](https://docs.nvidia.com/cuda/cuda-programming-guide/02-basics/intro-to-cuda-cpp.html).

**Device count must not force a hidden host round trip.** K2 cannot keep the old
host-sized `<<<search_num[0], ...>>>` launch if K1 leaves that count on the device.
The bounded version launches 111 candidate-slot CTAs, each checking the device
count and returning when inactive. Allocate capacity before the query loop;
K3 also uses fixed launch geometry and publishes its final logical length.
This adds inactive blocks and capacity slack: both are charged to the variant.
If that overhead dominates selective queries, keep a host-sized-launch control
or a separate dispatch rather than claiming the fixed grid is always superior.

**Inactive capacity is not initialized data.** K2's inactive CTAs return without
clearing prior-query flags or counts. K3 reads only the first
`device_count * MAX_SIZE` slots (or the first `device_count` leaf counts in the
packed interface). If it scans padded capacity, inactive predicates are zero
without reading old payloads. K1 publishes the candidate count every query;
K3 explicitly publishes `final_count=0` for zero candidates or zero hits. Output
tail capacity is never part of the logical result and need not be cleared.

For one query, conservative existing-layout payload capacity is
`111 * 20 * (sizeof(int) + sizeof(float)) = 17,760 bytes` per ID/distance pair of
arrays; flags, candidate IDs, counts and any separate final output are additional.
Reject overflow before access and route larger trees elsewhere. Reuse memory only
after its last consumer, and give concurrent queries distinct in-flight state.

## Launch ledger: architecture target, not performance evidence

The existing fixed 24-kernel query pattern partitions as follows:

| Original group | Kernel positions in ASYNC_EVIDENCE.json | Count |
|---|---|---:|
| F1 traversal | 1-5 | 5 |
| F2 candidate count/select | 6, 8-13 | 7 |
| F3 initialization + leaf distances | 7, 14 | 2 |
| F4 result count/select | 15-21 | 7 |
| Deletion-prefix maintenance | 22-23 | 2 |
| F5 final projection | 24 | 1 |

Combining F1+F2, F3, and F4+F5 yields the **three-kernel design target** only if
capacity reuse, device counts/fixed dispatch and valid prefix maintenance are all
provided. It is not achievable by merely pasting kernel bodies together. Keeping
F1/F2 separate gives a four-kernel alternative with a shorter compiler live set.
Any prefix maintenance, query-input transfer, output transfer, insertion-buffer
processing, logging and exceptional fallback still count in end-to-end timing.

## Resource/lifetime card and reject conditions

| Phase / owner | Live objects and release boundary | Main added cost / reject signal |
|---|---|---|
| K1 query CTA | Node flags, level state; per-thread distance DP only during traversal; scan scratch after final traversal barrier; candidate list/count live through K2 | Fused distance+scan increases REG/STACK or loses residency; deeper/wider control loop serializes too much work |
| K2 leaf CTA | Read-only candidate mapping; leaf metadata; per-thread distance state; hit predicate/payload; optional collective scratch after distance evaluation | Added local compaction extends DP/payload lifetimes; inactive fixed-grid CTAs outweigh saved host feedback |
| K3 query CTA | Hit predicates/leaf counts, tile carry and scan scratch; stream payloads from global storage only when valid; output live until consumed | One-CTA packing becomes a tail bottleneck; output ordering/remapping drift or insufficient capacity |

There is no Tensor Core precision change, TMA, cluster, special swizzle, global
spin barrier or new dependency in this first design. Keep the original 512-thread
shape as an initial control, not an assumed optimum; choose a new shape only
after ownership and resource measurement. The baseline already reports 47,528
stack bytes per thread in distance kernels: compare generated REG/STACK/LOCAL
rather than assuming shared flags alone determine occupancy.

## Recommended implementation order and required gates

1. Freeze materialized-output oracle and baseline first. Include zero hits,
   all hits, deleted/tail/non-leaf slots, partial leaves, scan-tile boundaries,
   capacities 0/1/max, and varied query order; compare independent expected counts,
   ID membership and distances, plus baseline ordering. Resolve baseline faults
   separately rather than validating a candidate solely by matching them.
   Reuse the same workspace across large/many-hit, small/few-hit and zero-candidate
   queries in both directions to expose stale flags, counts and payload reads.
2. Build the smallest producer fusion, F3 (`initRes` into leaf predicate writes),
   and the local F1 level pair as separate controls. They establish ownership and
   synchronization without changing distance semantics or global result ordering.
3. Test F2 and F4 cooperative selection, with workspace reuse as a separately
   measured baseline. For the three-kernel goal, predeclare the coupled
   fusion + fixed-device-count dispatch change and retain its unfused/reuse
   control; count-dependent allocation otherwise makes isolated pieces misleading.
4. Add F5 store projection after prefix readiness and full-ID correctness pass.
   Compare three versus four kernels instead of assuming the fewest wins.
5. Compile/resource inspection, full-output oracle, memcheck/synccheck/racecheck,
   repeated workspace reuse, and direction-balanced same-GPU clean timing are
   separate gates. Keep original executable/source intact and retain failures.
   NSYS proves removed launches/round trips; only same-contract clean end-to-end
   measurements can establish a speedup. Report first-query, sustained query,
   setup/maintenance and output costs instead of moving overhead off the clock.

No step above has been implemented or promoted by this design note.
