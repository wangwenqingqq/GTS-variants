# A: fixed 336-event integration trace

**UNCLASSIFIED.** The primary ratio of process-total medians is 0.855934141; the required <=0.85 is not reached. No sample replacement or threshold change was made.

| Metric | D0 median (ms) | D1 median (ms) | Median ratio D1/D0 | Paired geometric ratio | Paired 95% CI | Wins |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Service events + release | 1234.190701 | 1056.385958 | 0.855934141 | 0.856538914 | [0.855399524, 0.857722127] | 6/6 |
| Events | 1193.030078 | 1015.956915 | 0.851576950 | 0.852275791 | [0.850556075, 0.854775903] | 6/6 |
| Native/device release | 40.307336 | 39.695788 | 0.984827861 | 0.979834665 | [0.927726753, 1.035303586] | 5/6 |
| All ACKs | 1193.008346 | 1015.935582 | 0.851574580 | 0.852275013 | [0.850556900, 0.854772736] | 6/6 |
| Range ACKs | 329.677093 | 153.797929 | 0.466510814 | 0.466537500 | [0.465902726, 0.467184070] | 6/6 |
| kNN ACKs | 862.245428 | 861.117389 | 0.998691742 | 0.999463613 | [0.997023847, 1.002714010] | 5/6 |
| Insert ACKs | 0.556818 | 0.576951 | 1.036157236 | 1.001012268 | [0.950347710, 1.047065912] | 3/6 |
| Delete ACKs | 0.303727 | 0.291951 | 0.961226694 | 0.979070648 | [0.941900476, 1.026523692] | 5/6 |

All values aggregate inside each fresh process before statistics. The primary estimator is the ratio of medians, not the paired geometric ratio. The interval bootstraps six matched log ratios, 20,000 replicates, seed 2026101303. Events are not independent performance samples. [Timer boundary](../TIMING_BOUNDARY.md) limits the denominator to events + native/device/live-map release; retained Host-container destruction is unmeasured.

| Pair | Order | D0 service (ms) | D1 service (ms) | Paired D1/D0 |
| --- | --- | ---: | ---: | ---: |
| 1 | D0/D1 | 1230.461913 | 1052.916069 | 0.855707973 |
| 2 | D1/D0 | 1235.871379 | 1056.534454 | 0.854890300 |
| 3 | D0/D1 | 1235.296839 | 1056.237462 | 0.855047490 |
| 4 | D1/D0 | 1231.036600 | 1054.770952 | 0.856815266 |
| 5 | D0/D1 | 1247.480074 | 1071.396315 | 0.858848440 |
| 6 | D1/D0 | 1233.084563 | 1057.902200 | 0.857931590 |

Primary p10/median/p90 (ms): D0 1230.749256/1234.190701/1241.675727; D1 1053.843510/1056.385958/1064.649257.

Primary order strata: forward geometric ratio 0.856533030, 3/3 wins; reverse 0.856544797, 3/3 wins. No order stratum is discarded.
