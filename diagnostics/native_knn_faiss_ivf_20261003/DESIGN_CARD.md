# Full-ID observation adapter (not a new search algorithm)

The target is a single SM120 RTX PRO 6000 with resident FP32 table/index data.
The external comparison asks whether native GPU IVF is competitive at the same
empirical ID Recall@K, not whether a new CUDA kernel beats original GTS.

The pinned original configuration already maps `short` to `float`. The binary
loader avoids text parsing without quantization. MAX_H=6 is a separate capacity
configuration; every constructed leaf must hold at most MAX_SIZE=20 rows and the
leaf union must cover the complete dataset. A fixed 1 GiB query workspace makes
scheduler capacity reproducible. Index construction, pivot bounds, pruning,
original distance arithmetic, packed query/distance keys, and sorting remain.

## Output ownership and readiness

| Role / phase | Owns | Ready dependency | Lifetime / overwrite |
|---|---|---|---|
| Original leaf CTA | leaf-position distances and encoded sort keys | merged leaf/query list | until the existing sort completes |
| Existing sort | sorted leaf-position indices | leaf distance kernel completion | until result extraction |
| Original result thread | one query's sorted K positions | sort in default stream | extraction completes before workspace free |
| Diagnostic extraction in the same thread | K original IDs and FP32 L2 fields | sorted position -> leaf ID -> index permutation | Host copy completes before output free |
| Host caller | Q×K IDs and fields | blocking copies and synchronization | inspected outside timed query pass |

For an existing sorted position `pos`, `pos / MAX_SIZE` identifies its leaf
entry, `pos % MAX_SIZE` identifies its row within that leaf, and the original ID
is `id_list[node.lid + row]`. No extra data search or sorting is performed.
The adapter guards padded positions and sentinel distances and leaves the
original kth-distance output intact. Its extra K ID loads, K field writes,
output allocation/free and complete Host delivery are charged to GTS.

No MMA/TMA/cluster geometry, swizzle, barrier ownership, warp schedule or
precision optimization is introduced. The result thread holds scalar rank,
position, node and field values; its per-query loop is bounded by K<=32.
The ready graph stays sort -> extract -> copy -> free in the default stream.

## Gates and boundaries

Separate source hashes and an exact adaptation patch preserve the original.
The synthetic screen uses N4097 (ragged), D96/960, 33 queries, K8/32, B1/32,
nonperiodic coordinates, duplicate-vector boundary ties and repeated calls.
The recorded memcheck and synccheck runs reuse already-built synthetic caches
and cover the GTS query path, not initial construction, Faiss or the oracle.
An additional offline cache audit verifies an exact disjoint leaf partition,
rather than only the summed leaf capacity checked by the timing driver.
Full-table independent RN FP64 reference results and CPU spot checks qualify ID
quality on real development/final data. Profile duration is diagnostic only.
CUDA Graphs and mixed insert/delete are explicitly uncovered.

This card records the implemented observation path. It is not represented as
an earlier-than-compilation preregistration; CONTRACT.json owns the pre-run
measurement contract and every amendment precedes production development.
