# Fixed-query descriptive robustness

Linear-interpolated quantiles across each frozen 32-query set, not repeated process timings or confidence intervals. No cross-snapshot averaging for admission.

| Snapshot | Summary | Min (%) | p10 (%) | Median (%) | p90 (%) | Max (%) |
| --- | --- | --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 3.2715 | 54.0259 | 73.8525 | 88.9355 | 89.3066 |
| initial | LOCAL_BALL | 13.2568 | 91.2134 | 98.6572 | 99.8486 | 100.0000 |
| initial | PROJECTED_BOX | 11.0352 | 33.7720 | 83.5571 | 93.0078 | 93.8477 |
| initial | ORACLE | 0.0244 | 0.0244 | 0.0244 | 0.0244 | 5.5908 |
| first_rebuilt | GLOBAL4 | 1.9287 | 38.9600 | 75.3418 | 88.3521 | 90.9912 |
| first_rebuilt | LOCAL_BALL | 29.1992 | 91.2500 | 98.4985 | 99.6973 | 99.9512 |
| first_rebuilt | PROJECTED_BOX | 2.8320 | 44.4238 | 84.2285 | 92.6782 | 93.5059 |
| first_rebuilt | ORACLE | 0.0244 | 0.0244 | 0.0244 | 0.0952 | 7.8369 |

PROJECTED_BOX p90 remains above 92%, failing the 70% target on each snapshot.
