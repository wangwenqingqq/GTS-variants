# Operation attribution

The primary metric is each process's actual events + release, then its median. The figure instead stacks **means of per-process component totals**, so the components exactly sum to mean primary latency; it never stacks component medians. Raw operation, complete count/field-quality and ownership witnesses are preserved per process in `raw/A`.

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

Mean of D0 per-process kNN/event shares: 72.307134%. kNN is byte-identical and its paired interval includes 1; do not claim a kNN optimization. The first measured lazy native kNN setup remains inside its ACK. CPU usage and result transfer/waits are included in event ACKs, not separated into a new CPU-wait benchmark.

Insert/delete pixels are tiny because the query-dominated trace has only 40+40 updates; use the table, not their plotted height, to assess regression. Formal samples contain no extra fixed32 probes. B attribution is unavailable.

## Descriptive individual-event distribution

| Mode | Operation | Pooled events | p10 ACK (ms) | Median ACK (ms) | p90 ACK (ms) |
| --- | --- | ---: | ---: | ---: | ---: |
| D0 | Insert | 240 | 0.013068800 | 0.014059000 | 0.015489900 |
| D0 | Delete | 240 | 0.000855800 | 0.006580000 | 0.014710500 |
| D0 | Range | 768 | 2.569225900 | 2.572542000 | 2.577202200 |
| D0 | kNN | 768 | 6.023856400 | 6.029970000 | 6.036808600 |
| D1 | Insert | 240 | 0.012758700 | 0.013944000 | 0.015664200 |
| D1 | Delete | 240 | 0.000844800 | 0.006308000 | 0.014804200 |
| D1 | Range | 768 | 0.709177900 | 1.136937000 | 1.478348600 |
| D1 | kNN | 768 | 6.010678100 | 6.019081500 | 6.030675200 |

Events are pooled across six processes for descriptive distributions only. They are not additional independent process observations or the estimator for update-regression gates. Lazy native kNN initialization remains charged in the first measured ACK, even when a pooled quantile does not display that rare tail. All events are retained in raw CSVs.
