# Causal interpretation:Host API batching is not coarse GPU execution

## Measured trace counts — not native latency

All three W2 traces use the same strict native row assignments and1.92GB delete copy payload. Each chronological update range is bound to the independently replayed physical ledger.

| W2 delete executor | Host copy APIs | CUPTI memcpy activities | application kernels | explicit waits |
|---|---:|---:|---:|---:|
| NATIVE | 500000 | 500000 | 0 | 977 |
| WAVES | 977 | 500000 | 0 | 977 |
| FINAL | 977 | 977 | 977 | 977 |

**The ordinary CUDA batch API reduces500,000 Host submissions to977 calls,but still exposes500,000 row-copy activities.** FINAL instead uses977 metadata transfers(total4MB)+977 coalesced materialization kernels. Its vector-copy payload remains1.92GB. Thus the evidence distinguishes call-count reduction from execution/transfer granularity;it does not establish vector-byte elimination on W2.

## Native performance and resource scope

The unchanged CURRENT control takes1737.449777ms events+release versus627.995267ms for FINAL(63.86% reduction,6/6 wins). These are unprofiled process-median results;the trace table above is a separate diagnostic observation.

| Variant | events CPU user+system seconds | median CPU seconds/events wall seconds |
|---|---:|---:|
| CURRENT | 1.728067 | 1.0003 |
| FINAL | 0.617459 | 1.0002 |

CPU consumption during events falls substantially,but both variants still consume roughly one CPU core while active. This is **not proof of lower instantaneous CPU utilization**,nor a decomposition into pure CPU computation and GPU waiting. Build,export and release CPU time are outside this CPU-seconds field.

## Remaining costs and counterevidence

In the profiled FINAL W2 delete scopes,materialization kernels total4.468203ms(overlaid device activity),while outer delete scopes total189.526668ms. The gap includes Host ownership/planning,allocation,API/metadata work and waits. It must not be labelled all CPU computation or subtracted from unprofiled wall time. It motivates a future Host-planning diagnosis,not a new claim already measured here.

Pure insert is not accelerated:the main B1 andB512 FINAL/NATIVE median ratios are1.0109 and1.0075;all confidence intervals and finite query tails remain in REPORT.md. Query-total ratio is1.0001 with paired95% interval[0.9969,1.0016]. The service gain comes from deletion,not a universal operator win.

NCU DRAM metrics are unavailable in every capture and remain null;L2 sectors are available. No total native-versus-FINAL DRAM-byte saving is claimed. W2 has zero within-batch dependencies;the synthetic chain proves a narrower state-composition opportunity,but its timing excludes local plan/set destruction.

## Inference and next falsification

The combined same-contract observations support moving deletion from fine-grained copy-engine/runtime execution to coarse,coalesced GPU execution. Generic indexed GPU copying is known;this result does not admit new algorithmic novelty. A strong generic GPU gather/scatter comparator and repeated-live dependent mixed-query trace are the next falsifiers before a paper-level mechanism claim.
