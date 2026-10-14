# One zone-order adapter, no new execution mechanism

Target: the live-verified RTX PRO6000 Blackwell server GPU, sm_120, existing
CUDA13.1. Keep the inherited eight-warps/CTA, one warp/original-row owner,
16-byte PrefixState, four stages128/256/512/960, and stable CUB selection.
Single raw FP32 row-major database, no physical replicas or per-query reorder.

| Phase | Owner/live state | Ready/release edge |
|---|---|---|
| Host order | global960-FP32 means,30 ranks/zone IDs,960-coordinate temporary order | recompute every request;submit query and two30-int arrays on existing stream |
| Scan | each warp owns one row;lane-local FP32 chunk,shuffle reduction;lane0 owns FP64 prefix/ID/replay | same-stream order upload before scan;no cross-warp state |
| Ambiguous bound | lane0 replays selected coordinates in original dimension order | completes before tuple store;all source rereads charged |
| Select | existing CUB stable selection of16-byte tuples | count D2H/stream synchronization precedes next stage |
| Full hit | lane0 recomputes original ordered960-FP64 authority | before final fields and complete Host output |
| Output | inherited IDs,FP32 Euclidean fields,FP32-square cast to FP64 observer | all copies complete before Host-ready timer stops |

Fast scan maps each logical32-coordinate zone to a physical contiguous zone;
lanes0..31 remain contiguous within a row. This preserves a coalesced stretch
but does not guarantee cache/sector reuse across nonmonotonic zones. Added
global state:30-int order and30-int inverse,240B total. Static means3840B on
Host, not a second database. No shared-memory handoff, async barrier, cluster,
Tensor Core, Graph, persistent kernel, or new warp shape.

The inherited FP32 nonnegative-term interval is order-insensitive under the
same abs<=16 envelope and gradual-underflow mode. Ambiguity cannot replay
original0..END: those may be different coordinates. Instead, replay exactly
the selected subset **in original order**. Its sequential nonnegative score is
monotone below the original full authority. This preserves safe membership
without pretending a permuted reduction is bit-identical to the original.
Every retained final hit is restored from all960 original coordinates.

No coordinate-retention optimization is added. Ambiguous and full-authority
rereads are included in scan traffic and Host-ready latency. The CPU source
model does not include them. Qualification alone exports internal full-score
state for bitwise comparison; it is diagnostic-only, not primary timing.
Inherited FP32 field semantics are unchanged and explicitly distinguished from
the diagnostic internal FP64 authority.

Expected useful coordinate-stage payload:711,680,776B/query versus
1,014,828,776B for the historical keeper. Expected savings can be lost to zone
address loads, worse sectors/cache, changed active-set locality, ordering
submission, compaction, or authority rereads. Only fresh same-campaign all-kernel
NCU traffic and complete Host-ready timers decide realization. No performance
claim follows from this design or a successful build.

Qualification retains pointer/stream churn100iterations, inclusive boundaries,
duplicates, subnormals, every stage and ragged/empty/all-hit cases. Synthetic and
N4096 memcheck/racecheck/synccheck precede target-N timing. Inspect selected
kernel SASS/resources and retain spill costs rather than hiding them. Graph is
forbidden, so no Graph-compatibility claim. Sustained scope is six complete
32-query passes, not a production service or a dynamic workflow.
