# Memory and maintenance accounting

A reserves capacity 1,000,040; all byte values are decimal bytes, not GiB. Persistent device vectors are one allocation in both variants. Forward/reverse logical maps live on the CPU.

| Owned storage | D0 (B) | D1 (B) |
| --- | ---: | ---: |
| Raw FP32 device vectors | 3,840,153,600 | 3,840,153,600 |
| Native kNN device norms | 4,000,160 | 4,000,160 |
| CPU forward-map capacity | 4,000,160 | 4,000,160 |
| CPU reverse-map capacity | 4,000,160 | 4,000,160 |
| Retained CPU input vectors | 3,840,153,600 | 3,840,153,600 |
| Reusable query workspace, total | 25,006,891 | 57,038,379 |
| PrefixState ping-pong, part of above | 0 | 32,001,280 |
| CUB reserved scratch, part of above | 2,047 | 32,255 |

D1 adds 32,031,488 query-workspace bytes. Common D0 buffers retained by D1 remain charged. Workspace reservation occurs before service ready; use and native/device release follow the service boundary. Query-only state is persistent across requests as reusable capacity, but it is not a maintained index or a precomputed O(ND) representation.

CUDA mem-info after events reports 6,165,364,736/6,198,919,168 bytes (D0/D1), including context/library reservations. Device memory after service release is 614,203,392 bytes in both; remaining context/library globals are not claimed free. Private 200ms device-wide samples give 5880/5912 MiB high-water marks, **not exact peak or ownership proof**. CPU RSS peak was not measured. Offline final validation transiently creates another CPU replay copy outside primary timing. Retained client/audit Host-container destruction is unmeasured.

No tree/rebuild, D1-specific duplicated database or representation maintenance is introduced. Monotonic logical IDs and fixed capacity were qualified only for these 40 inserts/40 deletes; eventual capacity exhaustion/growth/rollover remains outside scope.
