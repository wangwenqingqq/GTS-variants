# Per-query robustness

Descriptive quantiles over each fixed 32-query set; NumPy linear interpolation. No repeated timing runs, confidence intervals or claim of distribution-wide generalization.

| Snapshot | Summary | Min (%) | p10 (%) | Median (%) | p90 (%) | Max (%) |
| --- | --- | --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 3.2715 | 54.0259 | 73.8525 | 88.9355 | 89.3066 |
| initial | LOCAL_BALL | 13.2568 | 91.2134 | 98.6572 | 99.8486 | 100.0000 |
| initial | ORACLE | 0.0244 | 0.0244 | 0.0244 | 0.0244 | 5.5908 |
| first_rebuilt | GLOBAL4 | 1.9287 | 38.9600 | 75.3418 | 88.3521 | 90.9912 |
| first_rebuilt | LOCAL_BALL | 29.1992 | 91.2500 | 98.4985 | 99.6973 | 99.9512 |
| first_rebuilt | ORACLE | 0.0244 | 0.0244 | 0.0244 | 0.0952 | 7.8369 |

The local-ball tail is near a full scan, not just a few hard outliers around a good median.
