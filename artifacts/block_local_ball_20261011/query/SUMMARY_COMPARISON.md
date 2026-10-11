# Fixed-block summary comparison

GIST N=1,000,000, D=960, FP32/L2; 4096 identical S1/P2 blocks and 32 fixed queries per snapshot. Arithmetic means; gap counts blocks, not objects. GLOBAL4 is the retained baseline and independently reconstructed; ORACLE is an unavailable-online lower bound, not a timed competitor.

| Snapshot | Summary | Mean surviving blocks (%) | Oracle (%) | Mean oracle gap (blocks) | False-pruned blocks |
| --- | --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 68.8995 | 0.3654 | 2807.15625 | 0 |
| initial | LOCAL_BALL | 92.2501 | 0.3654 | 3763.59375 | 0 |
| initial | ORACLE | 0.3654 | 0.3654 | 0.00000 | 0 |
| first_rebuilt | GLOBAL4 | 67.8749 | 0.3746 | 2764.81250 | 0 |
| first_rebuilt | LOCAL_BALL | 93.4250 | 0.3746 | 3811.34375 | 0 |
| first_rebuilt | ORACLE | 0.3746 | 0.3746 | 0.00000 | 0 |

LOCAL_BALL is worse on 63/64 queries; it is better on one initial query and ties none. Zero false prune is not evidence of selectivity or speed.
