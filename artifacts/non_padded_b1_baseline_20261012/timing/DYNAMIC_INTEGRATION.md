# Conditional short integration pair

336 events:40 insert,40 delete,128 range,128 kNN; initial1M/D960. One old→strengthened pair only. Inherited trace_ms includes final-state copy/release and host bookkeeping; context/setup/disk/serialization excluded. Operation sums are not the full trace. No CI or sustained benefit claim.

Observed trace reduction **7.7132%**, speedup **1.083579×**. Both measured256 and warmup8 complete queries passed with final-state checks. Original reference-ownership false failure remains; old output was rechecked offline, not rerun. Only the strengthened process was resumed after human approval.

| Mode | Trace ms | 128 range ACK sum ms | 128 kNN ACK sum ms | 40 insert ACK sum ms | 40 delete ACK sum ms | Release ms |
| --- | --- | --- | --- | --- | --- | --- |
| old | 1336.345387 | 431.204220 | 862.761123 | 0.554327 | 0.297631 | 41.510084 |
| strengthened | 1233.270291 | 329.552427 | 862.702277 | 0.548815 | 0.306475 | 40.143238 |
