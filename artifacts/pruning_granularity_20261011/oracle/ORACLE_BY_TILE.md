# Oracle changes with granularity

A tile is required iff at least one complete ordered-FP64 reference hit belongs to it. Oracle is diagnostic only, never a partition/filter input. Required-tile objects include false positives sharing a required tile; they are not the true-hit count.

| Snapshot | Target size | Mean required tiles | Mean empty surviving tiles | Mean objects in required tiles | Mean true hits | False-pruned tiles |
| --- | --- | --- | --- | --- | --- | --- |
| initial | 512 | 9.46875 | 1423.00000 | 4623.59375 | 205.93750 | 0 |
| initial | 256 | 14.96875 | 2807.15625 | 3654.56250 | 205.93750 | 0 |
| initial | 128 | 23.28125 | 5551.78125 | 2842.09375 | 205.93750 | 0 |
| initial | 64 | 36.15625 | 11001.00000 | 2206.90625 | 205.93750 | 0 |
| initial | 32 | 55.81250 | 21808.87500 | 1703.81250 | 205.93750 | 0 |
| first_rebuilt | 512 | 9.40625 | 1404.90625 | 4593.34375 | 388.40625 | 0 |
| first_rebuilt | 256 | 15.34375 | 2764.81250 | 3746.53125 | 388.40625 | 0 |
| first_rebuilt | 128 | 24.78125 | 5457.25000 | 3025.28125 | 388.40625 | 0 |
| first_rebuilt | 64 | 40.06250 | 10801.81250 | 2445.25000 | 388.40625 | 0 |
| first_rebuilt | 32 | 65.18750 | 21399.18750 | 1989.62500 | 388.40625 | 0 |

All320 rows have zero false prune; independent stable-sort/direct-endpoint/owner-array verification reconstructs all rows. This does not qualify a CUDA kernel or establish end-to-end benefit.
