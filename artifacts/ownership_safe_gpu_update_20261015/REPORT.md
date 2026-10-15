# Ownership-safe update transformation — complete bounded study

**Decision: strong engineering signal;scientific novelty is not admitted.** FINAL's W2 events+release median is 627.995267 ms versus 1737.449777 ms for the unchanged same-card CURRENT Frozen-PDX control:time reduction 63.86%,speedup 2.767x. The paired geometric ratio is 0.3578,95% interval [0.3404,0.3699],with 6/6 process wins.

## Data,scope and correctness

- GIST1M:1,000,000 x960 FP32 coordinates,3.84GB raw vectors;one SM120 RTX PRO6000 Blackwell GPU,CUDA13.1. B1 exact inclusive range queries,not ANN/kNN.
- W2:500,000 replacement pairs,1,000,000 point updates,977 delete+977 insert ACKs,160 formal queries and8 excluded warmups. Build and full-state export are excluded;release is included. Incoming vectors are the inherited rotated-coordinate payload.
- 341 attempts preserve one invalid foreign-activity interruption;340 admitted targets include42 qualification,6 screen,192 primary,54 synthetic shape,36 calibration and10 profiler targets. No passed target was rerun. The initial callback false alarm was corrected offline without rerunning its GPU target.
- All complete query members/fields,independently replayed occurrence maps and final vectors pass. All262 new GIST processes additionally bind full allocated-capacity bytes(including retired rows) and exact per-ACK physical execution to mutation witnesses. Qualifying diagnostic runs check every changed row after ACK. Synthetic bit tests do not admit NaNs to search.
- CPU proof:125,664 exhaustive sequences,576 randomized cases and15 invalid cases;C++ reverses permitted within-wave orders. Memcheck/racecheck/synccheck,high-entropy full-capacity cases and two sequential stream slots pass. Graph,simultaneous readers and production are not admitted.

## Full same-campaign service

All numbers are medians of6 process values,not sums of independent medians. See TIMING.json for p10/p90,all process values,paired ratios and order strata.

| Variant | events+release ms | query ms | update ms | release ms | known owned bytes |
|---|---:|---:|---:|---:|---:|
| S1 | 1759.527428 | 171.389747 | 1565.582604 | 11.231654 | 3889036099 |
| CURRENT | 1737.449777 | 135.566768 | 1582.372559 | 9.508118 | 3889036339 |
| NATIVE | 1713.146549 | 135.677214 | 1557.765616 | 10.331039 | 3889036339 |
| WAVES | 1707.158565 | 135.551499 | 1552.205751 | 10.218674 | 3889036339 |
| FINAL | 627.995267 | 135.575035 | 464.512459 | 10.275330 | 3889040435 |

| Comparison | Candidate/base service ratio;paired interval |
|---|---|
| NATIVE/CURRENT | 0.9860;paired95%[0.9428,1.0351] |
| WAVES/CURRENT | 0.9826;paired95%[0.9331,1.0211] |
| FINAL/CURRENT | 0.3614;paired95%[0.3404,0.3699] |
| FINAL/S1 | 0.3569;paired95%[0.3288,0.3574] |
| FINAL/WAVES | 0.3679;paired95%[0.3559,0.3739] |
| FINAL/NATIVE(audited) | 0.3666;paired95%[0.3542,0.3656] |

S1 is the inherited Progressive internal control;CURRENT is the unchanged Frozen-PDX native-update control. This is not an external Faiss/CAGRA or original-GTS-tree comparison.

## Whole Host-return operator ACK

Each entry is the median of6 within-process means. Replacement includes both operations;its outer ACK is not added to its sub-ACKs. Finite p50/p95 and throughput are retained in TIMING.json.

| Operator | B | NATIVE ms | WAVES ms | FINAL ms | FINAL/NATIVE;paired interval |
|---|---:|---:|---:|---:|---|
| I | 1 | 0.006460 | 0.006451 | 0.006531 | 1.0109;paired95%[1.0061,1.0400] |
| I | 32 | 0.025500 | 0.026171 | 0.025602 | 1.0040;paired95%[0.9884,1.0413] |
| I | 512 | 0.289461 | 0.292479 | 0.291622 | 1.0075;paired95%[1.0000,1.0632] |
| D | 1 | 0.008220 | 0.008238 | 0.008251 | 1.0038;paired95%[0.9979,1.0397] |
| D | 32 | 0.088254 | 0.085234 | 0.020374 | 0.2309;paired95%[0.2145,0.2534] |
| D | 512 | 1.340000 | 1.303596 | 0.172527 | 0.1288;paired95%[0.1281,0.1465] |
| R | 1 | 0.014145 | 0.014108 | 0.014033 | 0.9921;paired95%[0.9536,0.9990] |
| R | 32 | 0.115902 | 0.111566 | 0.046224 | 0.3988;paired95%[0.3719,0.4221] |
| R | 512 | 1.634041 | 1.619583 | 0.495277 | 0.3031;paired95%[0.2796,0.3053] |

## Query tails,CPU consumption and memory

| Variant | finite query p95 ms | events CPU user+system s | process max RSS KiB |
|---|---:|---:|---:|
| CURRENT | 1.526983 | 1.728067 | 6047930 |
| NATIVE | 1.527831 | 1.703040 | 6047448 |
| WAVES | 1.542706 | 1.696616 | 6048052 |
| FINAL | 1.555049 | 0.617459 | 6048034 |

FINAL/CURRENT formal query-total ratio:1.0001;paired95%[0.9969,1.0016]. CPU consumption is not pure CPU computation or isolated waiting. Known owned allocations are not an instrumented absolute GPU peak;cudaMemGetInfo values are point observations. FINAL adds4096 device bytes. The shared Host audit ledger is present in new NATIVE/WAVES/FINAL;CURRENT directly measures the unchanged comparator.

## What is redundant?

The immutable W2 witness inventory has977 delete batches,500,000 native moves and500,000 distinct final destination assignments,with0 RAW/WAW/WAR edges. Thus **W2 eliminates no vector-row movement**. Its causal opportunity is execution/control granularity,not a proven reduction in necessary vector payload. Counts refer to provenance assignments,not data-dependent identical-value elimination.

| Variant | delete copy APIs | kernel launches | D2D memcpy payload bytes | kernel copy payload bytes | plan H2D bytes | delete syncs |
|---|---:|---:|---:|---:|---:|---:|
| NATIVE | 500000 | 0 | 1920000000 | 0 | 0 | 977 |
| WAVES | 977 | 0 | 1920000000 | 0 | 0 | 977 |
| FINAL | 977 | 977 | 0 | 1920000000 | 4000000 | 977 |

WAVES retains every native row move in safe stream-ordered CUDA batch levels. FINAL composes tail provenance,proves source/destination nonaliasing,and materializes final row assignments with coalesced GPU loads/stores. At B1 it dispatches native;one final row uses memcpy. Both keep the same logical map and query layout. All planning,validation,bookkeeping,submission,destruction and wait costs are inside primary ACK.

## Dependent synthetic shapes — narrower timing scope

The frozen ACK_ms column is actually submission+wait **before local set/BatchPlan destruction**,not the main complete Host-return ACK. N4096/B512,2 warmups+32 intervals per dimension/process,6 processes;setup/reset/readback excluded. Do not promote these ratios to GIST service or compare their absolute denominator with the main table.

| Shape | D | NATIVE interval ms | WAVES interval ms | FINAL interval ms | FINAL/NATIVE;paired interval | FINAL compiled rows |
|---|---:|---:|---:|---:|---|---:|
| random | 128 | 1.561794 | 1.396248 | 0.177075 | 0.1134;paired95%[0.1002,0.1233] | 479 |
| random | 960 | 1.495308 | 1.408447 | 0.188560 | 0.1261;paired95%[0.1108,0.1315] | 479 |
| localized | 128 | 1.545251 | 1.307358 | 0.085094 | 0.0551;paired95%[0.0545,0.0658] | 512 |
| localized | 960 | 1.544091 | 1.309686 | 0.090898 | 0.0589;paired95%[0.0587,0.0701] | 512 |
| chain | 128 | 1.269358 | 1.673548 | 0.046070 | 0.0363;paired95%[0.0324,0.0403] | 1 |
| chain | 960 | 1.269187 | 1.607162 | 0.050069 | 0.0394;paired95%[0.0351,0.0423] | 1 |

The adversarial chain reduces512 native moves/512 safe levels to1 final row assignment under strict capacity compatibility. This is structural/correctness evidence plus a narrow synthetic timing interval,not a dependency-rich mixed-query service result.

## Diagnostic attribution and limits

TIMELINES.json and the six normalized CSVs preserve all NSYS ranges,API partitions,DMA/kernel overlays,sampled GPU activity and completeness warnings. Each update is bound chronologically to the physical ledger. Profiled ACKs never replace the native table;DMA and kernel time are not added to overlapping API/sync spans.

NCU.json retains every exported value/unit and explicit unavailability. FINAL update-kernel counts exclude metadata copies and CPU work;no corresponding native copy-engine counter denominator exists. Therefore total update DRAM savings are **unknown**,not zero and not established by requested payload counts. Query counters cover only the actually launched nonempty progressive stages/fields;launch counts are independently bound to validated stage inputs and answer counts. Calibration ratios retain all MARKED/PLAIN matched observations with the later-phase caveat in METHODS.md.

| NCU capture | selected launches | denominator | L2 read sectors | L2 write sectors | unavailable metrics |
|---|---:|---|---:|---:|---|
| ncu_query_NATIVE | 707 | per query | 22507997.47 | 2847452.91 | dram__bytes_read.sum,dram__bytes_write.sum |
| ncu_query_WAVES | 707 | per query | 22508155.40 | 2847577.48 | dram__bytes_read.sum,dram__bytes_write.sum |
| ncu_query_FINAL | 707 | per query | 22508110.47 | 2848050.27 | dram__bytes_read.sum,dram__bytes_write.sum |
| ncu_update_FINAL | 16 | per delete ACK | 62177.81 | 61457.69 | dram__bytes_read.sum,dram__bytes_write.sum |

An exported n/a is null/unknown,never zero. The predeclared uncontrolled-cache/unmodified-clock warnings remain disclosed. These are profiler observations,not native latency or a complete device-traffic denominator.

## Five research answers and next decision

1. Native swap order fixes occurrence/row semantics,but not every intermediate vector copy. Full-capacity provenance composition removes overwritten intermediate assignments when such dependencies exist.
2. Strict physical compatibility holds on all declared tests without query indirection,tombstones or weakened ACK visibility. Unsupported B>512 and invalid IDs remain rejected.
3. W2 measures a control/executor change,not vector-payload elimination. The physical ledger and profiler must distinguish Host call counts,internal transfer activities,kernel payload and hardware traffic.
4. B1/32/512 operator results,W2 and all synthetic regressions are retained separately. Missing concurrency,Graph,other datasets/GPUs and inclusive cold-start costs limit promotion.
5. Known gather/scatter/compaction already explains much of this execution design. W2 alone cannot validate new ownership-mechanism novelty. Preserve the engineering result;before a paper claim,compare a generic GPU gather/scatter implementation and a repeated-live-occurrence GIST mixed-query trace under the same complete ACK/service contract. No such extra campaign was silently launched.
