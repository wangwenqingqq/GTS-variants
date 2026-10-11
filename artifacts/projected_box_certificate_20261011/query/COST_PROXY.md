# Query cost class and remaining verification

All reductions span D960. A dot, maximum and ordered squared distance are different operations; counts are work-class proxies, **not identical instructions or latency**. The safe projection computes four dots and one max-absolute-coordinate reduction, fused into one query-input pass. The max reduction is not free.

| Summary | Query full-D reductions | Endpoints/block | Metadata bytes | Direction/pivot bytes |
| --- | --- | --- | --- | --- |
| GLOBAL4 | 4 distances | 8 | 262144 | 15360 |
| LOCAL_BALL | 4096 distances | 1 radius | 32768 | 15728640 |
| PROJECTED_BOX | 4 dots + 1 numeric max | 8 | 262144 | 30720 |
| FULL_SCAN | 1,000,000 distances | 0 | 0 | 0 |

PROJECTED_BOX directions are FP64, GLOBAL4 pivots are FP32. LOCAL_BALL optional center IDs add 32,768 bytes; GLOBAL4 optional pivot IDs add 32 bytes. Those ID payloads are separate. Endpoint reads are 32,768 FP64 values/query for GLOBAL4 and PROJECTED_BOX, not measured memory transactions.

## Fully charged work and logical coordinate payload

Model: summary full-D reductions plus one exact distance per surviving object. Projected work is shown both as `4+survivors` and fully charged `5+survivors` in JSON. The table uses the latter. Coordinate payload includes one shared 3840-byte query, all direction/pivot coordinates and surviving FP32 objects; metadata is separate. No cache reuse, actual DRAM traffic or output cost is claimed. This convention explicitly differs from old coordinate proxies that excluded query coordinates. The core model assumes four direction maximum-absolute coefficients and A2 are cached as static build state (40 more FP64 bytes/index), derived from frozen U/Gram. The offline envelope helper recomputes direction maxima once per batch and its C entry validates all direction coefficients per call; it is not a deployed online operator. If direction maxima were recomputed per online query, charge four additional full-D maxima (nine reductions instead of five). No whole-Python execution-cost equivalence is claimed.

| Snapshot | Summary | Mean surviving objects | Mean full-D reductions incl verification | Mean logical coordinate bytes |
| --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 688981.15625 | 688985.15625 | 2645706840 |
| initial | LOCAL_BALL | 922502.56250 | 926598.56250 | 3558142320 |
| initial | PROJECTED_BOX | 744113.03125 | 744118.03125 | 2857428600 |
| first_rebuilt | GLOBAL4 | 678735.68750 | 678739.68750 | 2606364240 |
| first_rebuilt | LOCAL_BALL | 934252.43750 | 938348.43750 | 3603261840 |
| first_rebuilt | PROJECTED_BOX | 751273.68750 | 751278.68750 | 2884925520 |

FULL_SCAN has 1,000,000 distances and 3,840,003,840 logical coordinate bytes including the query. These counts do not predict an actual end-to-end ratio. PCA/training and block construction also have costs; see the separate resource account below.
