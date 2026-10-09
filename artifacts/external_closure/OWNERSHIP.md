# Author GPU-Tree ownership and scope

Pinned author source: `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`,
`Source Code/GPU-Tree`. The overlay consumes user-supplied source and emits a
private build; no full third-party source is redistributed. No license-named
file was found in the earlier complete upstream source audit. That disclosure
boundary does not itself prevent local runtime qualification.

| Owner | Lifetime / last use | Release |
|---|---|---|
| data, data_info, pid, radius, partition contents/counts | index and searches | index release |
| tree_num, tree_sum_prefix, node_sum_prefix | topology read on every search | moved from search to index release |
| node_num | construction metadata, preserved for native lifecycle | index release |
| isSatisfied | query scratch, capacity PNUM x B1; every pivot filter overwrites | retained reusable scratch, index release |
| dis_pivot, qid | query input/scratch, overwritten each B1 | index release |
| T pointer table | **mutable root aliases**, not an allocation registry | table itself only |
| original allocations referenced by T before construction | nodes owned by index; Insert changes root table entries | captured separate Host registry, each allocation once |
| tree_filter, tree_filter_prefix | query-local compaction scratch, last read by mergeTree | release after compaction synchronization |
| tree_counter, root_idx, pivot_flag and compacted arrays | query-local | native release |
| qnum_counter, qnum_counter_prefix | query metadata needed for full delivery | adapter release after delivery |
| result_counter, init_result, dis_knn, id_knn | query output owner | adapter release after complete Host copy |
| queues / priority queues | per-query search temporary state | native search release |

The native first-call wrapper uses identical kernel bodies and PNUM8 in the
comparison. It retains native single-query metadata frees; adapter mode only
moves those frees. Both wrappers need the allocation registry correction, so
`native` means native search/arithmetic, **not untouched original lifecycle**.
PNUM8 is fixed before measurement because the source's Kth partition-bound
access requires K<=PNUM. PNUM5/K8 is not a supported configuration.

Capacity: each native subtree contains at most DNUM500 objects; range outputs
allocate DNUM times retained subtrees, then deliver each full counted segment.
kNN retains the source's candidate queues/global distance sort and delivers K.
Out-of-capacity or invalid IDs fail the complete run, never truncate to a pass.
Small N<8 is currently explicitly unsupported by this native construction;
this is an admission gap, not a measured performance loss. Empty candidate
searches and degenerate partition behavior require explicit qualification.

No distance formula, partition, priority queue, pivot selection or pruning kernel
is changed. A detected pruning/race/precision failure is a blocker until a
separately named repair passes; ownership changes cannot be used to excuse it.
