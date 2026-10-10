| Snapshot | P | Best diagnostic layout | Strategy | Mean surviving256 (%) | Mean oracle gap (blocks) | Scalar reads/query |
| --- | --- | --- | --- | --- | --- | --- |
| initial | 1 | L1 | S0 | 90.7546 | 3532.81 | 7814 |
| initial | 2 | L1 | S0 | 89.5548 | 3485.94 | 15628 |
| initial | 4 | L3 | S2 | 87.7384 | 3415.00 | 31256 |
| initial | 8 | L3 | S2 | 78.3442 | 3047.97 | 62512 |
| first_rebuilt | 1 | L1 | S0 | 72.3405 | 2813.84 | 7814 |
| first_rebuilt | 2 | L1 | S0 | 72.2933 | 2812.00 | 15628 |
| first_rebuilt | 4 | L1 | S0 | 71.6047 | 2785.09 | 31256 |
| first_rebuilt | 8 | L1 | S0 | 69.2227 | 2692.03 | 62512 |

Each row is the best of 12 layout/strategy configurations at this P on that snapshot, **not one shared algorithm across snapshots**. All rejected/weaker rows, 32/512 sensitivity and per-query tails are retained in JSON. Query distance cost is exactly P, no early exit. Metadata is 16*P*3907 bytes for block256. False prune is zero for every configuration/query/block-size.
