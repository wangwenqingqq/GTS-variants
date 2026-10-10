# External dual-task static lifecycle

N1M/D960/B1/K8, FP32 inputs; radius bits `0x3f34a3d8`. Six fresh processes per method/snapshot, eight warmups and32 measured calls per supported task. Ratios are comparator/P; values below1 favor the comparator.

The matrix is4+44+24 valid observations. Both failed attempts remain excluded from estimates but retained in the budget (74 external attempts;92 including18 internal). The three registration batches and changed ownership observer are recorded; no incomplete batch is substituted for the frozen estimate.

Scope: preparation + build +32 kNN +32 range + native/index resource release. Warmup/context and process setup/serialization are separate; retained-client-output destruction is excluded. Only dual-task CPU portfolios are paired against dual-task P; single-task GPU Flat/range are not divided by this denominator. This is not full-program time or a dynamic update workflow.

All72 admitted processes pass complete membership and frozen numeric-field checks; the two failed attempts are excluded from the admitted matrix. The isolation-invalid attempt retains its separate output-quality pass; correct answers do not repair failed isolation. CPU_FLAT below means CPU_FLAT_INCLUSIVE_ADAPT (native kNN; explicitly inclusive range adapter).

| Snapshot | Comparator | Comparator median ms | P median ms | Paired ratio |95% CI | P wins/6 | Comparator-first / P-first | Confirmed P gain |
|---|---|---:|---:|---:|---|---:|---|---|
| initial | CPU_BALL | 176732.991790 | 2585.842037 | 69.282709 | [67.976009, 71.261490] | 6 | 68.589848 / 69.982570 | yes |
| initial | CPU_FLAT | 24259.399016 | 2585.842037 | 9.542851 | [9.254327, 10.033320] | 6 | 9.715152 / 9.373606 | yes |
| initial | CPU_KD | 226356.727081 | 2585.842037 | 87.305722 | [86.479473, 88.078551] | 6 | 87.386559 / 87.224960 | yes |
| first_rebuilt | CPU_BALL | 172222.618696 | 2489.332030 | 69.599451 | [68.903053, 70.558341] | 6 | 69.171000 / 70.030556 | yes |
| first_rebuilt | CPU_FLAT | 23474.612720 | 2489.332030 | 9.431373 | [9.350901, 9.517176] | 6 | 9.498526 / 9.364696 | yes |
| first_rebuilt | CPU_KD | 220243.898015 | 2489.332030 | 88.566541 | [88.053335, 89.181503] | 6 | 88.942064 / 88.192603 | yes |

## Phase medians (ms)

All methods are listed to retain setup costs; a dash is an unsupported task, never zero. Warmup is separate. Lifecycle medians are computed per complete process, not by summing phase medians. Single-task GPU lifecycle ratios remain inadmissible.

| Snapshot | Method | Preparation | Build | Warmup | kNN pass | Range pass | Native/index release | Dual-task lifecycle |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| initial | CPU_BALL | 2295.054041 | 106743.150814 | 17195.353603 | 33971.951881 | 33998.844906 | 55.357446 | 176732.991790 |
| initial | GPU_FLAT_KNN | 0.000000 | 769.109168 | 133.161786 | 138.169229 | — | 33.538947 | — |
| initial | GTSPP_P | 546.135303 | 1053.013812 | 239.029864 | 219.049129 | 694.854477 | 67.856303 | 2585.842037 |
| initial | GPU_RANGE_COMPLETE | 0.000000 | 544.915733 | 36.497473 | — | 110.486709 | 8.005519 | — |
| initial | CPU_FLAT | 1196.463427 | 2112.311164 | 5188.238380 | 10374.151253 | 10353.477900 | 160.609454 | 24259.399016 |
| initial | CPU_KD | 2530.284790 | 153550.480209 | 17812.991451 | 34950.262916 | 34555.826255 | 51.611935 | 226356.727081 |
| first_rebuilt | CPU_BALL | 1467.124764 | 103316.720681 | 16908.096653 | 33691.360854 | 33649.674910 | 23.342882 | 172222.618696 |
| first_rebuilt | GPU_FLAT_KNN | 0.000000 | 632.783518 | 133.543601 | 138.280938 | — | 33.069576 | — |
| first_rebuilt | GTSPP_P | 542.209433 | 1053.653211 | 196.410828 | 219.256465 | 603.352617 | 67.616402 | 2489.332030 |
| first_rebuilt | GPU_RANGE_COMPLETE | 0.000000 | 533.851079 | 36.508612 | — | 110.415453 | 8.229219 | — |
| first_rebuilt | CPU_FLAT | 856.907241 | 2092.594270 | 5081.061865 | 10153.143001 | 10186.713326 | 175.332758 | 23474.612720 |
| first_rebuilt | CPU_KD | 1475.836124 | 149939.610365 | 16695.491542 | 34382.940665 | 34091.417369 | 24.293947 | 220243.898015 |

Complete phase distributions, all72 raw rows, process CPU/RSS and returned payload/guard hashes are in `evidence/EXTERNAL_STATIC_COMPLETE.json`. The estimator is byte-bound and reproduces the original paired calculation:20,000 bootstrap resamples, seed2026101002. Confirmation requires lower95% bound>1, at least5/6 wins and both order strata>1; an unconfirmed row is not automatically a tie.

Limits: observed diagnostic queries, shared host, native single-thread CPU latency (not full-machine throughput); CPU_FLAT is the explicitly inclusive adapter, KD/Ball leaf512. GPU-Tree is absent from these timings (range correctness is separate; kNN safety remains blocked), MVPT provenance/output remain open. No universal GPU-tree, coalescing-only, held-out, dynamic,100k/1B or leak-clean claim; the96B context-symbol limitation remains.
