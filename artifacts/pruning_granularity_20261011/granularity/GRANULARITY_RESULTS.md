# Fixed GLOBAL4 granularity curve

GIST N1M/D960 FP32 L2 B1, original32 queries per snapshot, fixed radius0x3f34a3d8. Arithmetic means are deterministic structural counts, not process timings or confidence intervals. Each target independently restarts the identical S1/P2 recursive rule; all smaller member sets are nested.

| Snapshot | Target size | Tiles | Mean surviving tiles (%) | Mean surviving objects (%) | Mean oracle tiles (%) |
| --- | --- | --- | --- | --- | --- |
| initial | 512 | 2048 | 69.9448 | 69.9439 | 0.4623 |
| initial | 256 | 4096 | 68.8995 | 68.8981 | 0.3654 |
| initial | 128 | 8192 | 68.0550 | 68.0529 | 0.2842 |
| initial | 64 | 16384 | 67.3655 | 67.3628 | 0.2207 |
| initial | 32 | 32768 | 66.7257 | 66.7223 | 0.1703 |
| first_rebuilt | 512 | 2048 | 69.0582 | 69.0576 | 0.4593 |
| first_rebuilt | 256 | 4096 | 67.8749 | 67.8736 | 0.3746 |
| first_rebuilt | 128 | 8192 | 66.9193 | 66.9173 | 0.3025 |
| first_rebuilt | 64 | 16384 | 66.1736 | 66.1709 | 0.2445 |
| first_rebuilt | 32 | 32768 | 65.5041 | 65.5008 | 0.1989 |

## Actual occupancy

Target size is a maximum, not an exact leaf size; recursive boundaries are not flattened/rechunked. Static slots below are a target-capacity model, not a GPU allocation.

| Snapshot | Target size | Tiles | Min objects/tile | Max | Modeled occupancy (%) |
| --- | --- | --- | --- | --- | --- |
| initial | 512 | 2048 | 488 | 489 | 95.3674 |
| initial | 256 | 4096 | 244 | 245 | 95.3674 |
| initial | 128 | 8192 | 122 | 123 | 95.3674 |
| initial | 64 | 16384 | 61 | 62 | 95.3674 |
| initial | 32 | 32768 | 30 | 31 | 95.3674 |
| first_rebuilt | 512 | 2048 | 488 | 489 | 95.3674 |
| first_rebuilt | 256 | 4096 | 244 | 245 | 95.3674 |
| first_rebuilt | 128 | 8192 | 122 | 123 | 95.3674 |
| first_rebuilt | 64 | 16384 | 61 | 62 | 95.3674 |
| first_rebuilt | 32 | 32768 | 30 | 31 | 95.3674 |

## Fixed-query robustness

Linear-interpolated quantiles across32 queries, not repeated runs.

| Snapshot | Target size | Min objects (%) | p10 | Median | p90 | Max |
| --- | --- | --- | --- | --- | --- | --- |
| initial | 512 | 3.3697 | 55.2600 | 74.6557 | 89.8041 | 90.7198 |
| initial | 256 | 3.2718 | 54.0272 | 73.8512 | 88.9346 | 89.3049 |
| initial | 128 | 3.1373 | 53.0117 | 73.3255 | 87.7673 | 88.5971 |
| initial | 64 | 2.9416 | 52.2822 | 72.9193 | 86.7287 | 88.1819 |
| initial | 32 | 2.6630 | 51.5273 | 72.4082 | 85.9019 | 87.7431 |
| first_rebuilt | 512 | 2.1498 | 40.5419 | 76.1945 | 89.2230 | 92.0407 |
| first_rebuilt | 256 | 1.9302 | 38.9590 | 75.3391 | 88.3511 | 90.9905 |
| first_rebuilt | 128 | 1.6982 | 37.6320 | 74.6051 | 87.7210 | 90.3065 |
| first_rebuilt | 64 | 1.5579 | 36.2509 | 74.1345 | 87.3214 | 89.8239 |
| first_rebuilt | 32 | 1.3790 | 35.1222 | 73.6341 | 86.7952 | 89.3512 |

## Object-work wins against256

| Snapshot | Target size | Better queries | Worse | Equal |
| --- | --- | --- | --- | --- |
| initial | 512 | 0 | 32 | 0 |
| initial | 256 | 0 | 0 | 32 |
| initial | 128 | 32 | 0 | 0 |
| initial | 64 | 32 | 0 | 0 |
| initial | 32 | 32 | 0 | 0 |
| first_rebuilt | 512 | 0 | 32 | 0 |
| first_rebuilt | 256 | 0 | 0 | 32 |
| first_rebuilt | 128 | 32 | 0 | 0 |
| first_rebuilt | 64 | 32 | 0 | 0 |
| first_rebuilt | 32 | 32 | 0 | 0 |

The256 permutations, leaf boundaries and complete64 anchor rows reproduce exactly. Object counts, not tile percentages, drive admission.
