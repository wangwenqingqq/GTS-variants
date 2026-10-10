# External static kNN

N1M/D960/B1/K8, FP32 inputs; radius bits `0x3f34a3d8`. Six fresh processes per method/snapshot, eight warmups and32 measured calls per supported task. Ratios are comparator/P; values below1 favor the comparator.

The matrix is4+44+24 valid observations. Both failed attempts remain excluded from estimates but retained in the budget (74 external attempts;92 including18 internal). The three registration batches and changed ownership observer are recorded; no incomplete batch is substituted for the frozen estimate.

Scope: continuous32-query Host-input-to-complete-Host-ID/FP32-field-ready pass on a prebuilt index. Preparation, build, warmup and native/index resource release are separate; serialization and retained-client-output destruction are excluded. This is not full-program or update-workflow time.

All72 admitted processes pass complete membership and frozen numeric-field checks; the two failed attempts are excluded from the admitted matrix. The isolation-invalid attempt retains its separate output-quality pass; correct answers do not repair failed isolation. CPU_FLAT below means CPU_FLAT_INCLUSIVE_ADAPT (native kNN; explicitly inclusive range adapter).

| Snapshot | Comparator | Comparator median ms | P median ms | Paired ratio |95% CI | P wins/6 | Comparator-first / P-first | Confirmed P gain |
|---|---|---:|---:|---:|---|---:|---|---|
| initial | GPU_FLAT_KNN | 138.169229 | 219.049129 | 0.630915 | [0.629782, 0.632010] | 0 | 0.631476 / 0.630356 | no |
| initial | CPU_BALL | 33971.951881 | 219.049129 | 155.726598 | [154.320804, 157.171700] | 6 | 155.594370 / 155.858939 | yes |
| initial | CPU_FLAT | 10374.151253 | 219.049129 | 47.147335 | [46.468700, 47.632447] | 6 | 46.946797 / 47.348729 | yes |
| initial | CPU_KD | 34950.262916 | 219.049129 | 160.452462 | [157.995180, 163.396248] | 6 | 159.628493 / 161.280684 | yes |
| first_rebuilt | GPU_FLAT_KNN | 138.280938 | 219.256465 | 0.630411 | [0.629987, 0.630852] | 0 | 0.630355 / 0.630467 | no |
| first_rebuilt | CPU_BALL | 33691.360854 | 219.256465 | 154.335577 | [152.649488, 156.468229] | 6 | 155.298513 / 153.378613 | yes |
| first_rebuilt | CPU_FLAT | 10153.143001 | 219.256465 | 46.371721 | [46.108341, 46.699476] | 6 | 46.575845 / 46.168492 | yes |
| first_rebuilt | CPU_KD | 34382.940665 | 219.256465 | 157.210412 | [156.192768, 158.379937] | 6 | 157.283526 / 157.137332 | yes |

## Absolute pass distribution and average query cost

Six observed pass times: p10 / median / p90, not a confidence interval. Average query cost is each pass divided by32; its median is shown below, not a latency percentile.

| Snapshot | Method |32-query pass p10 / median / p90 ms | Median average ms/query |
|---|---|---|---:|
| initial | CPU_BALL | 33720.875007 / 33971.951881 / 34632.510359 | 1061.623496 |
| initial | GPU_FLAT_KNN | 138.110760 / 138.169229 / 138.257258 | 4.317788 |
| initial | GTSPP_P | 218.448801 / 219.049129 / 219.544635 | 6.845285 |
| initial | CPU_FLAT | 10168.711276 / 10374.151253 / 10438.173002 | 324.192227 |
| initial | CPU_KD | 34546.204227 / 34950.262916 / 35951.377182 | 1092.195716 |
| first_rebuilt | CPU_BALL | 33406.828183 / 33691.360854 / 34440.220064 | 1052.855027 |
| first_rebuilt | GPU_FLAT_KNN | 138.052676 / 138.280938 / 138.371095 | 4.321279 |
| first_rebuilt | GTSPP_P | 218.885309 / 219.256465 / 219.691184 | 6.851765 |
| first_rebuilt | CPU_FLAT | 10095.320581 / 10153.143001 / 10257.302322 | 317.285719 |
| first_rebuilt | CPU_KD | 34172.641289 / 34382.940665 / 34866.812721 | 1074.466896 |

Complete phase distributions, all72 raw rows, process CPU/RSS and returned payload/guard hashes are in `evidence/EXTERNAL_STATIC_COMPLETE.json`. The estimator is byte-bound and reproduces the original paired calculation:20,000 bootstrap resamples, seed2026101002. Confirmation requires lower95% bound>1, at least5/6 wins and both order strata>1; an unconfirmed row is not automatically a tie.

Limits: observed diagnostic queries, shared host, native single-thread CPU latency (not full-machine throughput); CPU_FLAT is the explicitly inclusive adapter, KD/Ball leaf512. GPU-Tree is absent from these timings (range correctness is separate; kNN safety remains blocked), MVPT provenance/output remain open. No universal GPU-tree, coalescing-only, held-out, dynamic,100k/1B or leak-clean claim; the96B context-symbol limitation remains.
