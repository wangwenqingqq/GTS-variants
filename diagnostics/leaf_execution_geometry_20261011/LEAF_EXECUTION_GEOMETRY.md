# Leaf execution geometry: original GTS, fixed32

**The existing-information whole-leaf gate has no additional opportunity in this
workload; small-leaf execution packing merits a later test, not promotion.**
The diagnostic finds 2,929,074 visited query-leaf pairs, all with ten objects.
None has its recorded original lower bound above the entry disk upper bound.

## Contract and provenance

Original GTS kNN plus the pinned complete-ID adapter, GIST1M x960 FP32, K8/B1,
self-inclusive, fixed32 previously seen queries. Same index/pivots, 1GiB original
workspace, FP32 subtraction / ordered double accumulation, bounds and complete outputs.
The new code only observes sidecar records; six insertions strip byte-for-byte
back to the original search. GPU1/NUMA0 admission and serial locks apply. No
optimized kernel, current-GTSPP run, new profiler collection or formal timing
comparison was performed. Source, binary, query and raw identities are retained.

## Exact work counts (all 32 queries)

| Quantity | Count |
|---|---:|
| Potential query-leaf pairs | 3,200,000 |
| Leaves reaching the original leaf-bound test | 3,019,410 |
| Rejected by that original leaf-bound test | 90,336 |
| Visited / launched leaf CTAs | 2,929,074 |
| Valid objects | 29,290,740 |
| Objects executing the distance loop | 29,290,708 |
| Leaf distance dimensions | 28,119,079,680 |
| Pivot distance evaluations | 336,587 |
| All distance dimensions | 28,442,203,200 |
| Objects passing the existing disk filter | 27,388 |
| Original node-bound tests / passes | 3,365,870 / 3,262,461 |
| Original bound-free prefix labels | 3,520 |

Original pruning already removes 270,926 potential query-leaf pairs, including
180,590 excluded before reaching the leaf-bound test. The **zero** below is only
additional re-pruning opportunity, not a claim that GTS never prunes.
Visited leaves range from 23,470 to 97,818 per query, averaging 91,533.5625.
All distance/node/leaf totals agree with the preceding fixed32 baseline counts.

## Online information versus retrospective outcomes

| Classification over visited leaves | Count | Fraction |
|---|---:|---:|
| Existing lower bound > entry disk upper bound | 0 | 0% |
| Bound changed between node test and leaf entry | 0 | 0% |
| Missing original leaf-bound observation | 0 | 0% |
| No object passes the entry disk filter | 2,906,484 | 99.22877% |
| No returned final top-k object | 2,928,828 | 99.99160% |
| No member of the independent oracle's legal top-k set | 2,928,828 | 99.99160% |
| Existing lower bound > final kth field (retrospective) | 52,517 | 1.79296% |

`nodeProcessKnn` applies its existing FP32 lower-bound predicate before
`getQCountKnn -> scan -> mergeLNodeKnn -> dataProcessKnn`. The entry disk is a pivot-derived upper bound, not an exact online heap kth. It is
unchanged after this predicate. Rechecking it cannot remove an additional leaf
here. This is scoped to the observed original predicate, not a theorem excluding
new stronger bounds or another traversal regime.

No-disk-survivor and no-top-k labels use completed distances or final results.
They are **not** safe pre-execution certificates. Even the final-kth screen uses
future information and the original FP32 predicate; it is not an implemented gate
or a new mathematical safety proof. Leaf CTAs run in parallel, not a sequential
online top-k heap. A leaf's accepted-object mask means disk-filter survival, not
necessarily returned membership.

## Three different warp denominators

The source launches **512 threads =16 warps per leaf CTA**, not a literal
one-warp CTA. `did=threadIdx.x` assigns an object to each of the first ten lanes;
MAX_SIZE is20. The other warps do not execute object distance loops.

| Denominator | Recorded / derived result |
|---|---|
| Configured launched warp slots | 46,865,184 |
| Warps containing distance-loop participants | 2,929,074 |
| Launched warp slots with no distance participants | 43,936,110 (93.75%) |
| Object-active warp participation | ten lanes in 2,929,042 leaves; nine in32 self leaves |
| Distance lanes / object-active warp lane slots | 31.24997% |
| Distance lanes / all configured CTA lane slots | 1.95312% |
| Object-active warps with at most8 distance lanes | 0 |

These are GPU-recorded thread-participation masks plus the fixed launch mapping,
**not** SM occupancy, eligible-warps samples, dynamic SASS instruction counts or
percent-of-peak utilization. In particular, 93.75% zero-distance warp slots does
not mean 93.75% of executed distance instructions can be removed. The earlier
cache result did not dynamically prove unchanged warp instruction counts either.

## Whole-leaf packing simulation, no GPU implementation

The CPU simulator preserves the observed compacted leaf order and never splits
a leaf. It packs valid object slots, not a posteriori survivors. All original
distance work, object IDs and independent leaf predicates remain required.

| Structural mapping | Warp bins across32 queries | Distance-lane fill |
|---|---:|---:|
| One leaf per object-active warp | 2,929,074 | 31.24997% |
| At most two leaves/warp | 1,464,546 | 62.49955% |
| At most three leaves/warp | 976,369 | 93.74884% |
| Sequential whole-leaf capacity32 packing | 976,369 | 93.74884% |

Three-leaf packing reduces structural object-warp bins by66.66629%, with tail
bins included per query. This is **not a 3x speedup**, an actual CTA reduction,
or a measured reduction in warp-issued instructions. Packing can add address
selection, result-slot mapping and resource costs; the row-major vector accesses
may remain poorly coalesced. Fixed three and greedy capacity32 are identical on
this workload, so the more complex packer has no demonstrated structural benefit.
On a self-only synthetic leaf a structural bin may have zero distance participants;
the public key is therefore `packing_structural_warps`.

## Qualification, faults and limitations

The successful final collection includes21 processes: both modes on D96/960,
N4097, K1/8/32 with the fixed33 tie/self queries; both modes on the last allocated
nonempty leaf; three count-mode sanitizer processes; and G0/Gcount fixed32 GIST.
All legal membership/field checks pass; every paired full-result binary matches,
and GIST results match the preceding baseline. Memcheck, racecheck and synccheck
pass on the affected count path with the D96 synthetic fixture. This is not a
1M sanitizer coverage claim or a total GPU leaf visitation-order proof.

The first package omitted the oracle's imported helper and stopped after one
baseline process. The second collection passed runtime/output checks but its
closing manifest mistakenly included a mutable Python bytecode cache. Both
failures remain in raw evidence. One bounded complete recollection excluded only
derived bytecode, retained identical GPU binaries and queries, and passed the
full source/data identity gate. Its fixed32 raw sidecar hash, outputs and work
summary are identical to the second collection: no result selection occurred.

The parser's CPU regression verifies the binary format, the distinction between
online and retrospective classification, and corrupt-mask rejection. Run it with
Python>=3.11; the local default Python3.9 lacks `int.bit_count`, so the successful
local test used Python3.13. No N<K, B32, dynamic update or concurrency claim is made.
The instrumented driver's raw CSV times include instrumentation/file costs and
must not be used as a latency comparison.
