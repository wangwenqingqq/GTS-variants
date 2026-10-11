# Fully charged query work proxies

Each distance evaluation is full D=960. Coordinate payload uses FP32 and excludes query coordinates, caching, reuse and output writes. This is a logical payload model, **not measured CPU/GPU time, DRAM traffic or cache transactions**.

| Summary | Summary distance evals/query | Summary reads (bytes) | Coordinate payload (bytes/query) |
| --- | --- | --- | --- |
| GLOBAL4 | 4 | 262144 | 15360 |
| LOCAL_BALL | 4096 | 32768 | 15728640 |
| FULL_SCAN | 1,000,000 (all verification) | 0 | 3840000000 |

GLOBAL4 reads 8 FP64 endpoints/block; LOCAL_BALL reads one FP64 radius/block. Optional 64-bit center IDs add 32,768 bytes; optional four pivot IDs add 32 bytes, listed separately from summary reads. Center coordinates are 15.72864 decimal MB versus a full-scan 3.84 decimal GB. The ball summary requires 1024 times as many distances as GLOBAL4, although it is only 0.4096% of full-scan distance work.

## Remaining exact verification must still be paid

Model: summary distances + one full-D distance per surviving object; no reuse of center distances during verification. FULL_SCAN uses all objects once.

| Snapshot | Summary | Mean surviving objects | Mean total distance evals | Mean total coordinate bytes | Queries with total evals > full scan |
| --- | --- | --- | --- | --- | --- |
| initial | GLOBAL4 | 688981.15625 | 688985.15625 | 2645703000 | — |
| initial | LOCAL_BALL | 922502.56250 | 926598.56250 | 3558138480 | 8 |
| initial | FULL_SCAN | 1000000.00000 | 1000000.00000 | 3840000000 | — |
| first_rebuilt | GLOBAL4 | 678735.68750 | 678739.68750 | 2606360400 | — |
| first_rebuilt | LOCAL_BALL | 934252.43750 | 938348.43750 | 3603258000 | 5 |
| first_rebuilt | FULL_SCAN | 1000000.00000 | 1000000.00000 | 3840000000 | — |

The extra summary cost does not purchase a smaller candidate set here. These proxies cannot establish an actual end-to-end slowdown or speedup. Offline certificate construction also costs N center/member distances per snapshot, in addition to reused four-pivot signatures and deterministic C0 selection; no build timing was collected.
