# B0: frozen keeper

B0 reads coordinates for scoring, then reads them again after tree construction for numeric refit. Its per-pair interval is **register-local**, not a global endpoint sidecar. Refit uses 256 threads/node, 4,096 shared bytes/block, one initial barrier and eight reduction rounds. Host validation and publication remain separate costs.

## Dependency and ready graph

```text
LEVEL_INPUT + DATA -> NATIVE SCORE -> KEY -> NATIVE SORT -> SPLIT
                                                   |            |
                                      native boundary read      TREE -> VALIDATE
                                                                 |
DATA -> SECOND COORDINATE READ -> FULL SAFE ARITHMETIC -> REGISTER ENDPOINT
                                                        |
                                               NODE MIN/MAX -> BOUNDS -> PUBLISH -> QUERY
```

Execution mapping: native score/sort/split for five levels; one post-build numeric refit kernel (NN blocks of 256 threads); existing host validation and epoch update.

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
| TREE | REFIT_READ | final node pivot and member interval/order | TN + int32 | post-build refit | device global -> registers | tree finalized and host validation complete | final node |
| VALIDATE | REFIT_READ | validated physical structure | structural status | post-build refit | host control -> kernel launch | refresh validation and allocation before refit | tree epoch |
| DATA | REFIT_READ | coordinates loaded again for (row,node.pid) | FP32 x,y | refit coordinate iteration | device global -> registers | refit launch after construction | physical pair (r,p), final node |
| REFIT_READ | SAFE | promoted coordinate operands | FP64 x,y; ordered RD/RU loop | coordinate iteration / pair | registers | program order | physical pair (r,p), final node |
| SAFE | REDUCE | pair endpoints folded immediately into thread partials | two FP64 | pair -> node block reduction | registers -> shared low[256],high[256] | initial block barrier + eight reduction rounds | final node; no global per-pair endpoints |
| REDUCE | BOUNDS | min(lo),max(hi); root [0,+inf] | two FP64 per node | persistent | device global lo[NN],hi[NN] | post-refit device synchronization | final node |
| BOUNDS | PUBLISH | completed numeric bounds | two FP64 per node | persistent | device global | refit completion plus validated structure | tree epoch |
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
| per-pair endpoint sidecar | none | none | 0 | 0 | none: pair endpoint dies after thread fold | none |
| refit shared lower+upper | thread partials | node block reduce | 512 | 4096 | one node block | shared memory per resident block |
| refit registers | ordered interval/thread fold | node reduce | per active thread | unknown | coordinate/pair/node loop | registers; compiler lowering unmeasured |

## Arithmetic graph

Native scoring: FP32 coordinate subtraction -> original `pow(...,2)` -> **nominal double accumulator** -> original `pow(sum,0.5)` -> FP64 encoded key. Native split boundary remains a separate **float accumulator** and FP32 TN.min_dis; it cannot silently be replaced by the scoring value. Safe arithmetic: FP32 operands promoted to FP64 -> ordered lower/upper directed subtract -> absolute extrema -> directed square -> ordered directed add -> directed roots -> child min/max. Final root is explicitly `[0,+inf]`.

See [cost accounting](COST_MODEL.md), [source hashes](evidence/KEEPER_SOURCES.json), [exact source locators](evidence/SOURCE_LOCATIONS.json) and [machine-readable graph](evidence/GRAPHS.json).
