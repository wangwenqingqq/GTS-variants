# Exact checkpoint ownership and stage accounting

Every complete checkpoint ID for all40 target qualification invocations matched Gate1/original ordered-FP64. The table excludes eight warmups. Coordinate/owner/state columns are logical cost models, not NCU DRAM; scan/CUB times come from the separate event-enabled diagnostic. Tuple padding, flags, refinement and CUB scratch are additionally charged/reported, not folded into owner/state.

| Stage | Mean input | Mean output | Coordinate MB/query | Modeled owner/state MB | Scan event ms | CUB event ms |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 1000000.00000 | 654128.18750 | 512.000000 | 31.849538 | 0.402303 | 0.020461 |
| 2 | 654128.18750 | 149844.93750 | 334.913632 | 25.346754 | 0.294916 | 0.015992 |
| 3 | 149844.93750 | 8076.96875 | 153.441216 | 5.491341 | 0.126042 | 0.010047 |
| 4 | 8076.96875 | 205.93750 | 14.473928 | 0.293242 | 0.213077 | 0.006638 |
