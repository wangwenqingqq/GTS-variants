# Complete Host-ready timing

Six fresh processes per mode, eight warmups plus the original32 measured queries. p10/p90 across process means are not confidence intervals. B0 is structural READ_ONLY, not a search algorithm. All576 measured ACK samples retained in JSON.

P1/B1 marginal median ratio **0.443375**; matched-round geometric ratio **0.443278**; 95% process bootstrap CI **[0.442961, 0.443627]**; wins **6/6**.

| Mode | Median ACK ms/query | Process p10 / p90 ms | Relative to B1 |
| --- | --- | --- | --- |
| B0 | 2.518568 | 2.517247 / 2.519529 | 0.978800 |
| B1 | 2.573117 | 2.570768 / 2.578705 | 1.000000 |
| P1 | 1.140855 | 1.139724 / 1.142674 | 0.443375 |
