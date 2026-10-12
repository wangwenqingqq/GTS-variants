# B1 Z: retained comparator, rejected

After evaluating X/Y/Z, retain only Z as the clearest complete comparator for the graph kill test. Its split-local gather/min-max is already permitted in strongest C2. Its normalized graph, storage, ownership and consume-before-overwrite edges are identical. The execution label changes; no necessary C2 dependency is removed. This retained design is rejected, not promoted or implemented.

## Dependency and ready graph

```text
LEVEL_INPUT + DATA -> ONE COORDINATE READ
                            |             |
                        NOMINAL       FULL SAFE ARITHMETIC
                            |             |
                           KEY       GLOBAL lo[r],hi[r] (16 MB, one level)
                            |             | retained across native sort
                        NATIVE SORT       |
                            |             |
                        NATIVE SPLIT -> GATHER BY id_list[s] -> CHILD MIN/MAX
                            |                                  |
                     native boundary                      FINAL BOUNDS
                            |                                  |
                           TREE -> VALIDATE ----------------> PUBLISH -> QUERY

Consume all level endpoints -> completion -> allow next-level overwrite
```

Execution mapping: Z: call direct split-segment aggregation ownership-aware propagation; execution naming/placement only relative to the strong C2 above.

Every edge below is a value/control dependency, not a claim about measured CUDA instructions. `physical row` is a unique occurrence index in the compact base, not a logical user ID.

| Producer | Consumer | Value | Type | Lifetime | Storage | Synchronization/readiness | Owner |
|---|---|---|---|---|---|---|---|
| LEVEL_INPUT | NATIVE_READ | pre-sort physical order, parent interval, flags and pivot selection | int32 metadata/order | current scoring level | device global -> registers/shared pivot | previous split/init ready; same-block pivot barrier | scoring parent and physical rows |
| LEVEL_INPUT | SPLIT | unchanged parent interval and split flag | TN + int32 | current split task | device global -> registers | previous split/init ready and current native sort complete | scoring parent |
| DATA | NATIVE_READ | object and parent-pivot coordinates | FP32 x,y | coordinate iteration | device global to registers | before scoring; existing stream | physical row r / parent pivot p |
| NATIVE_READ | NOMINAL | unchanged nominal operands | FP32 subtraction; nominal double accumulator | coordinate loop / scoring task | registers | program order | parent |
| NOMINAL | KEY | encoded nominal sort key | FP64 | score through native sort; allocation reused per level | device global dis_list[N] | scoring completion / existing device synchronization | slot s within parent |
| KEY | SORT | keys and paired physical-row values | FP64 key + int32 row | native sort invocation | device global arrays; sort scratch unknown | native Thrust sort completion | slot -> permuted slot, physical row preserved |
| SORT | SPLIT | sorted physical-row order | int32 order[N] | split through later build/query | device global id_list[N] | native sort completion before split | parent interval -> child subinterval |
| DATA | BOUNDARY_READ | child first-row and parent-pivot coordinates | FP32 x,y | boundary coordinate iteration | device global to registers | sorted order ready | child |
| SPLIT | BOUNDARY_READ | child lid and inherited pivot | int32 lid,pid | child boundary computation | registers / node metadata | native sort completion | child |
| BOUNDARY_READ | BOUNDARY_NOMINAL | unchanged boundary operands | FP32 subtraction and float accumulation | boundary task | registers | program order | child |
| BOUNDARY_NOMINAL | TREE | TN.min_dis and native flags | FP32 scalar + int32 metadata | persistent tree | device global nodes/flags | existing split completion / device synchronization | child |
| SPLIT | TREE | child lid,size,pid,is_leaf | TN metadata | persistent tree | device global node_list | existing split completion / device synchronization | child |
| TREE | VALIDATE | final nodes, empty flags, physical permutation | TN + int32 | host refresh scope | D2H to host vectors | existing refresh synchronization and copies | final tree |
| VALIDATE | PUBLISH | valid physical permutation and node/leaf coverage | structural status | refresh -> epoch publication | host status / managed Bounds metadata | host validation succeeds before publication | tree epoch |
| PUBLISH | QUERY | bounds base/nodes/n/d/epoch identity | pointer/int/uint64 metadata | persistent until refresh/release | managed metadata | all bound producers complete before publication | tree epoch |
| NATIVE_READ | SAFE | same loaded coordinate operands, explicitly promoted | FP64 x,y; ordered RD/RU loop | coordinate iteration / pair | registers | program order; native nominal path preserved | physical pair (r,p), scoring parent |
| SAFE | SIDECAR | pair lower and upper endpoints | two FP64 | score to child reduction in same level | lo[r],hi[r] device global, keyed by physical row | score completion before native sort/split consumer | physical row r in this level; parent pivot p |
| SIDECAR | GATHER | endpoints by sorted physical row | two FP64 | post-sort child interval traversal | global -> registers | score ready and native sort complete | row r -> child owner |
| SORT | GATHER | r = id_list[s] | int32 | one gather iteration | existing global order -> register | native sort completion | sorted slot s -> physical row r |
| SPLIT | GATHER | [child.lid,child.lid+child.size) and inherited pivot | int32 segment descriptor | child reduction | existing metadata / split-local registers | child descriptor ready; same-block barrier if cooperative | parent -> child, no materialized N-owner map |
| GATHER | REDUCE | finite nonnegative pair endpoints | two FP64 | thread partials through block/segment completion | registers/shared; implementation scratch unknown | reduction barriers required by chosen mapping | child member set |
| REDUCE | BOUNDS | min(lo), max(hi); root special [0,+inf] | two FP64 per node | persistent to query/refresh | global final lo[NN],hi[NN] | reduction completion; consume-before-sidecar-overwrite | child/node |
| REDUCE | NEXT_LEVEL | level endpoints fully consumed | completion event/control | end level -> next producer | stream/control, not an N-array | done before overwriting lo[r],hi[r] | this level -> next level |
| BOUNDS | PUBLISH | final node endpoints | two FP64 per node | persistent | device global | all level reductions done; validation retained | tree epoch |
| BOUNDS | QUERY | published lower and upper bounds | two FP64 per node | persistent | device global | epoch guard after completion | query node |

## Memory-lifetime graph

Bytes are decimal payloads. Unknown is not zero. Persistent coordinate/order/tree/bound payloads are common costs, not all new allocation.

| State | Producer | Consumer | Cardinality | Bytes | Lifetime | Storage |
|---|---|---|---:|---:|---|---|
| coordinate payload | input | scoring/boundary/refit or certificate | 960000000 | 3840000000 | whole index epoch | device-accessible global |
| native nominal keys | scoring | native sort | 1000000 | 8000000 | allocation across build; values one level | device global |
| physical order | native init/sort | split/gather/query/validation | 1000000 | 4000000 | persistent tree | device global |
| TN nodes | split | validation/refit/query | 111111 | 2222220 | persistent tree | device global |
| empty flags | init/split | validation/refit | 111111 | 444444 | persistent tree | device global |
| split flags | init/split | host-observable reduce | 111111 | 444444 | construction; freed at return | device global |
| parent pivot list | scoring | native split | 111111 | 444444 | construction; values current level | device global |
| final lower+upper | numeric reduction | query | 222222 | 1777776 | persistent until refresh/release | device global |
| native sort scratch | native sort | native sort | implementation-dependent | unknown | sort invocation | device allocator-dependent |
| host validation vectors | refresh D2H / host init | structure checks | nodes NN + empty NN + order/seen/cover 3N | 14666664 | refresh host scope | host heap payload; allocator overhead unknown |
| level lower sidecar | safe scoring | child gather/reduction | 1000000 | 8000000 | one level; no overwrite before consume done | device global, physical-row indexed |
| level upper sidecar | safe scoring | child gather/reduction | 1000000 | 8000000 | one level; no overwrite before consume done | device global, physical-row indexed |
| additional N-entry owner map | none | none | 0 | 0 | none; segment owner computed from existing TN | none |
| additional endpoint permutation payload | none | none | 0 | 0 | none; existing id_list carries physical identity | none |
| certificate/reduction registers and shared scratch | score/gather | safe loop/segment reduce | implementation-dependent | unknown | producer or reduction block | registers/shared; compiler footprint unknown |
| alignment padding/allocator metadata | allocator | allocator | implementation-dependent | unknown | sidecar allocation | unknown beyond two 8-byte-aligned arrays |

## Arithmetic graph

Native scoring: FP32 coordinate subtraction -> original `pow(...,2)` -> **nominal double accumulator** -> original `pow(sum,0.5)` -> FP64 encoded key. Native split boundary remains a separate **float accumulator** and FP32 TN.min_dis; it cannot silently be replaced by the scoring value. Safe arithmetic: FP32 operands promoted to FP64 -> ordered lower/upper directed subtract -> absolute extrema -> directed square -> ordered directed add -> directed roots -> child min/max. Final root is explicitly `[0,+inf]`.

See [cost accounting](COST_MODEL.md), [source hashes](evidence/KEEPER_SOURCES.json), [exact source locators](evidence/SOURCE_LOCATIONS.json) and [machine-readable graph](evidence/GRAPHS.json).

## Required differentiation sentence

**Compared with strongest C2, B1 Z removes no necessary dependency while preserving the same proposed native sort/topology and final-bound contract.**

Deleting an N-entry owner map or a standalone reduction kernel would beat a weaker invented C2, not this control. Logical gather, child membership, extrema and readiness remain even inside the split kernel. No universal claim that all fusion is useless follows; launch reduction may be useful engineering under a separate same-contract campaign, but is not this independent mechanism.
