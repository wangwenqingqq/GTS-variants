# Summary-family comparison

GIST N1M/D960 FP32 L2, B1; 4096 identical frozen S1/P2 blocks of 244/245 objects; 32 original queries/snapshot. GLOBAL4 and LOCAL_BALL are hash-bound retained results, previously independently verified; this round newly evaluates PROJECTED_BOX and independently reconstructs its complete rows. ORACLE is an unavailable-online lower bound.

| Snapshot | Summary | Mean surviving blocks (%) | p90 (%) | Mean oracle gap (blocks) | False-pruned blocks |
| --- | --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 68.8995 | 88.9355 | 2807.15625 | 0 |
| initial | LOCAL_BALL | 92.2501 | 99.8486 | 3763.59375 | 0 |
| initial | PROJECTED_BOX | 74.4102 | 93.0078 | 3032.87500 | 0 |
| initial | ORACLE | 0.3654 | 0.0244 | 0.00000 | 0 |
| first_rebuilt | GLOBAL4 | 67.8749 | 88.3521 | 2764.81250 | 0 |
| first_rebuilt | LOCAL_BALL | 93.4250 | 99.6973 | 3811.34375 | 0 |
| first_rebuilt | PROJECTED_BOX | 75.1266 | 92.6782 | 3061.84375 | 0 |
| first_rebuilt | ORACLE | 0.3746 | 0.0952 | 0.00000 | 0 |

## Per-query wins against GLOBAL4

| Snapshot | PROJECTED_BOX better | Worse | Equal |
| --- | --- | --- | --- |
| initial | 6 | 26 | 0 |
| first_rebuilt | 4 | 28 | 0 |

PROJECTED_BOX is not uniformly worse: ten queries improve, while 54 regress. Aggregate survival and tail gates nevertheless fail. No measured query speed follows from these counts.
