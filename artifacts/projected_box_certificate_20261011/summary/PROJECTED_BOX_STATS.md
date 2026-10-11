# Conservative box statistics

Each of the unchanged 8192 snapshot-block pairs retains four lower and four upper FP64 endpoints. Bounds are built without query/radius/oracle information. The full scalar JSON records membership size, endpoints and widths per direction/block; no per-object projections or raw coordinates are published.

| Snapshot | Direction (0-based) | Mean width | Median | p10 | p90 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| initial | 0 | 0.889948769 | 0.834117506 | 0.580161140 | 1.209211170 | 0.128602761 | 4.239769258 |
| initial | 1 | 1.309367703 | 1.151005219 | 0.787614590 | 1.995932808 | 0.228258606 | 6.510924771 |
| initial | 2 | 1.548275879 | 1.432624228 | 1.045529484 | 2.181243050 | 0.305224441 | 6.455098817 |
| initial | 3 | 1.315688253 | 1.263946030 | 0.932135297 | 1.772107508 | 0.277493336 | 3.822991954 |
| first_rebuilt | 0 | 0.889989289 | 0.834012097 | 0.580161140 | 1.209211170 | 0.128602761 | 4.239769258 |
| first_rebuilt | 1 | 1.309388673 | 1.151005219 | 0.787614590 | 1.995932808 | 0.228258606 | 6.510924771 |
| first_rebuilt | 2 | 1.548250574 | 1.432624228 | 1.045529484 | 2.181243050 | 0.305224441 | 6.455098817 |
| first_rebuilt | 3 | 1.315690582 | 1.263946030 | 0.932041988 | 1.772107508 | 0.277493336 | 3.822991954 |

These are widths in the represented linear projection coordinates; Gram repair makes them safe even when stored directions are not mathematically exact orthonormal vectors.
