# Unpriced future system costs

This CPU gate prices only coordinate payload. No latency model or GPU kernel is
admitted, and the following are not assumed free:

| Cost | Ownership / admission requirement |
|---|---|
| Partial-sum state | A persistent register or exact-safe state per unresolved occurrence; if staged through memory, state reads and writes must be counted. FP64 analytical state is not automatically a performant GPU arithmetic choice. |
| Masks / branch decisions | Strict-safe rejection flags, reads/writes or predicate instructions; hits cannot disappear. |
| Object scheduling | Maintain the original occurrence ownership while continuing unresolved rows; price any permutation or restoration. |
| Warp divergence | Per-object first crossings do not imply a warp or a memory sector can stop at the same dimension. |
| Continuation metadata | Owner IDs, offsets and persistent/relaunch state; no uncharged compact-index stream. |
| Compaction / relaunch | Charge scan/select, metadata traffic and launch completion; compare against the non-padded baseline. |
| Result materialization | Complete stable membership, all declared fields, full D2H and Host completion remain charged; true hits need complete scores. |
| Update maintenance | Outside this round. Insert/delete/refresh/fallback costs must be frozen before a future dynamic claim. |

Only a GO result admits a design-only128/256/512/960 stage accounting. Such an
accounting must distinguish per-coordinate ideal payload from checkpoint-rounded
payload and optional global-state/continuation traffic. It cannot grant a
latency or novelty claim. Conditional/unclassified/NO-GO outcomes admit no GPU.
