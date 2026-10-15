# Operator readiness and attribution design

No update compute kernel or storage algorithm is added. `generate.py` takes
the immutable Store source and inserts compile-time optional NVTX scopes plus
a renamed legacy entry point. The diagnostic legacy capture changes from
repeated profiler start/stop to one formal-window capture;the unmodified parent
binaries remain the primary whole-service controls. A generated exact diff,
full binary identities and selected-function SASS hashes are retained.

| Object | Owner | Ready / overwrite / release |
|---|---|---|
| Raw FP32 database | One1M-capacity device allocation | same-stream copy completion and ACK before next request |
| Occurrence/position maps | Single Host thread | each swap updates moved owner before next delete |
| Incoming payloads/IDs | Immutable client vectors | request ready before timer;remain alive through stream wait |
| Delete tail source row | Current last live owner | stream orders dependent swap copies;not batch-independent |
| Native mutation witnesses | Service Host vector | appended within native ACK;retained for independent replay |
| PDX mean/order | Frozen mean,normal query order buffers | no update maintenance;search code identical to parent |
| NVTX scopes | Same Host thread | no per-row markers;PLAIN removes calls at compile time |
| Calibration buffers | Independent disjoint allocations | one copy + stream wait;full byte check outside measurement |

The ready graph is request → validation → per-row lookup/swap-enqueue/owner
update (delete) orone contiguous H2D+owner appends (insert) → stream wait → ACK.
Replacement preserves both individual waits and completes after insertion.
No cross-stream overlap,MVCC,Graph,persistent kernel or hidden Host database
lookup is introduced. Existing query kernels retain their native warp/CTA
shape,register/shared/stack ownership and ordered-FP64 authority.

Expected counts are hypotheses to verify from CUDA tracing:insertone copy and
one explicit wait/batch;deleteone copy/moved row andone wait/batch;replacement
both. Thus larger batch amortizes explicit ACK waits but does not inherently
reduce delete copy-submission count. Host checks and witness appends are real
charged work of this artifact,not asserted fundamental semantic lower bounds.
A tiny-copy stream can be CPU-fed or copy-engine-latency-bound despite low SM
activity;sampled DRAM/engine activity and the bulk reference test that alternative.

Unprofiled whole ACKs are the public denominator. Timeline partitions only the
marked function interval;wrapper timer/recording gaps are separately visible.
API Host time,device DMA and waits overlap. Never subtract independent NSYS
kernel/copy durations from plain ACKs to produce a fictitious CPU remainder.
