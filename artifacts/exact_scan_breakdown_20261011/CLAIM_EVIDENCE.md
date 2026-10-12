# Claim–evidence ledger

| ID | Claim / evidence state | Scope and denominator | Evidence | Strongest allowed wording |
| --- | --- | --- | --- | --- |
| C1 |Memory-dominant static query (`inferred`) |Frozen GIST N1M/D960/B1 native range, 32 fixed queries |STATIC_STATS, STATIC_TIMELINE, METRICS, STATIC_DECISION; full quality and six process distributions |Passes MEMORY_BOUND, fails NEAR_ROOFLINE; not all scans/trees |
| C2 |High CPU occupancy (`measured`), independent CPU bottleneck rejected (`rejected`) |E trace + release rusage; static independent NSYS query scopes |DYNAMIC_STATS, static/dynamic API overlap unions |Approximately one CPU core is consumed, but API waits overlap GPU; CPU stack cause unknown |
| C3 |Native executed-work inflation (`measured`) |One selected first-measured main-kernel NCU launch per mode, 10 replay passes |Predicated-on FADD/FMUL/FFMA counters; reported function text hash identity |184.32G executed FP32 proxy versus 2.879G useful model; not 64x speedup |
| C4 |Padded query-tile cause (`inferred`) |Native B1 library path only |Counter ratio and runtime-function geometry; full JIT module unavailable |Plausible explanation requiring causal follow-up; not proved innovation |
| C5 |Sparse output not dominant (`inferred`) |Actual 200/206/1645 mean-hit range; six paired processes |FULL/COUNT contrast and high/low paired CI |No large bottleneck within attained sparse-output range; not dense results |
| C6 |Updates not dominant (`measured`) |Fixed 336 events, six E processes; continuous trace includes release |DYNAMIC_STATS and complete 128 range / 128 kNN / 40 insert / 40 delete state/output checks |0.063045% median update ACK share; not an update-heavy long trace |
| C7 |Ordered-FP64 reference qualified (`measured`) |One diagnostic process, 8 warm+32 measured |MATCHED, retained failed launch and registered recovery |All 40 members/fields exact; no native-FP32 paired speedup |
| C8 |Scaling (`partial`) |Deterministic D and N-prefix controls |SCALING_TABLE and raw QUERY_OPERATIONS |Descriptive scaling; lower-D selectivity not matched, logical GB/s not DRAM GB/s |
| C9 |New mechanism/system gain (`unknown`) |No optimization prototype, no new P/external comparison |No evidence in this campaign |No new end-to-end gain or novelty claim |
| C10 |L2 traffic split (`measured`) |One approved separate diagnostic launch |L2_SUPPLEMENT, retained two-bucket rejection |Read/write/Other request sectors; unknown Other subtype; no blending with main capture |

Measured, inferred and partial states are intentionally separate. Raw executed
contracts/source archives are immutable/private; public contracts parameterize
placement prose, with both raw and curated hashes in PROVENANCE. The public commit
identifies the delivered artifact, not the earlier build timestamp. Dataset and
binary/source/raw-report hashes bind the original measurements. Native membership
is exact on tested cases; field tolerance and bit-exact matched scope differ.

Prior art: [cuVS small-query tiling/resource issue](https://github.com/NVIDIA/cuvs/issues/277),
[NVIDIA profiler guide](https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html),
[server hardware peaks](https://www.nvidia.com/en-us/data-center/rtx-pro-6000-blackwell-server-edition/).
These support calibration/novelty boundaries, not a new kernel causality claim.
