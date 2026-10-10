# External static range

N1M/D960/B1/K8, FP32 inputs; radius bits `0x3f34a3d8`. Six fresh processes per method/snapshot, eight warmups and32 measured calls per supported task. Ratios are comparator/P; values below1 favor the comparator.

The matrix is4+44+24 valid observations. Both failed attempts remain excluded from estimates but retained in the budget (74 external attempts;92 including18 internal). The three registration batches and changed ownership observer are recorded; no incomplete batch is substituted for the frozen estimate.

Scope: continuous32-query Host-input-to-complete-Host-ID/FP32-field-ready pass on a prebuilt index. Preparation, build, warmup and native/index resource release are separate; serialization and retained-client-output destruction are excluded. This is not full-program or update-workflow time.

All72 admitted processes pass complete membership and frozen numeric-field checks; the two failed attempts are excluded from the admitted matrix. The isolation-invalid attempt retains its separate output-quality pass; correct answers do not repair failed isolation. CPU_FLAT below means CPU_FLAT_INCLUSIVE_ADAPT (native kNN; explicitly inclusive range adapter).

| Snapshot | Comparator | Comparator median ms | P median ms | Paired ratio |95% CI | P wins/6 | Comparator-first / P-first | Confirmed P gain |
|---|---|---:|---:|---:|---|---:|---|---|
| initial | GPU_RANGE_COMPLETE | 110.486709 | 694.854477 | 0.157903 | [0.156274, 0.159296] | 0 | 0.157912 / 0.157893 | no |
| initial | CPU_BALL | 33998.844906 | 694.854477 | 49.019652 | [48.182908, 49.943078] | 6 | 49.067850 / 48.971502 | yes |
| initial | CPU_FLAT | 10353.477900 | 694.854477 | 15.524602 | [14.616703, 17.212313] | 6 | 16.224178 / 14.855192 | yes |
| initial | CPU_KD | 34555.826255 | 694.854477 | 50.213811 | [49.247553, 51.615243] | 6 | 49.680686 / 50.752657 | yes |
| first_rebuilt | GPU_RANGE_COMPLETE | 110.415453 | 603.352617 | 0.181860 | [0.180227, 0.183367] | 0 | 0.183462 / 0.180271 | no |
| first_rebuilt | CPU_BALL | 33649.674910 | 603.352617 | 55.837688 | [55.484450, 56.182404] | 6 | 55.536315 / 56.140696 | yes |
| first_rebuilt | CPU_FLAT | 10186.713326 | 603.352617 | 16.889300 | [16.775023, 17.019946] | 6 | 16.961878 / 16.817034 | yes |
| first_rebuilt | CPU_KD | 34091.417369 | 603.352617 | 56.625922 | [56.301590, 56.972607] | 6 | 56.527350 / 56.724666 | yes |

## Absolute pass distribution and average query cost

Six observed pass times: p10 / median / p90, not a confidence interval. Average query cost is each pass divided by32; its median is shown below, not a latency percentile.

| Snapshot | Method |32-query pass p10 / median / p90 ms | Median average ms/query |
|---|---|---|---:|
| initial | CPU_BALL | 33328.609134 / 33998.844906 / 34894.771142 | 1062.463903 |
| initial | GTSPP_P | 693.266893 / 694.854477 / 696.740843 | 21.714202 |
| initial | GPU_RANGE_COMPLETE | 107.977393 / 110.486709 / 110.762328 | 3.452710 |
| initial | CPU_FLAT | 10093.545111 / 10353.477900 / 12134.514714 | 323.546184 |
| initial | CPU_KD | 34156.948057 / 34555.826255 / 36021.874281 | 1079.869570 |
| first_rebuilt | CPU_BALL | 33392.767227 / 33649.674910 / 33991.167758 | 1051.552341 |
| first_rebuilt | GTSPP_P | 600.739204 / 603.352617 / 605.282250 | 18.854769 |
| first_rebuilt | GPU_RANGE_COMPLETE | 108.165025 / 110.415453 / 110.487596 | 3.450483 |
| first_rebuilt | CPU_FLAT | 10096.073502 / 10186.713326 / 10277.121713 | 318.334791 |
| first_rebuilt | CPU_KD | 33874.012835 / 34091.417369 / 34495.035108 | 1065.356793 |

Complete phase distributions, all72 raw rows, process CPU/RSS and returned payload/guard hashes are in `evidence/EXTERNAL_STATIC_COMPLETE.json`. The estimator is byte-bound and reproduces the original paired calculation:20,000 bootstrap resamples, seed2026101002. Confirmation requires lower95% bound>1, at least5/6 wins and both order strata>1; an unconfirmed row is not automatically a tie.

Limits: observed diagnostic queries, shared host, native single-thread CPU latency (not full-machine throughput); CPU_FLAT is the explicitly inclusive adapter, KD/Ball leaf512. GPU-Tree is absent from these timings (range correctness is separate; kNN safety remains blocked), MVPT provenance/output remain open. No universal GPU-tree, coalescing-only, held-out, dynamic,100k/1B or leak-clean claim; the96B context-symbol limitation remains.
