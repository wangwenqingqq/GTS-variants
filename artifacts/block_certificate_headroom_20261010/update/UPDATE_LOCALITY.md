| Snapshot | Actual update interval | Changed blocks (%) range | Moved existing occurrences range | Splits range | Global repartitions |
| --- | --- | --- | --- | --- | --- |
| initial | 10I10D | 0.3359–0.7679 | 0–1288 | 0–10 | 0 |
| first_rebuilt | 20I20D | 0.4703–1.2798 | 0–2579 | 0–20 | 0 |

Across all layouts, strategies and P, both slack settings (240/224 active capacity in 256 slots) moved **zero** existing objects and needed zero splits. These are independent interval initializations, not one organization maintained through both intervals. Duplicate coordinates remain separate immutable occurrences. Inserts still scan every block summary to choose a destination. Local writes do not establish local total CPU work or an update speedup. Payload bytes are a copy model, not measured traffic.
