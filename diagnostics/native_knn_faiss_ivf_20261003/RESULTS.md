# Native kNN / IVF comparison: final evidence

## Conclusion

Native GPU Faiss-IVF all-list1024/1024 satisfies **100% tie-aware ID Recall@K** on all eight registered shapes. Its later six-process median Host-ready256-query pass is **63.6–140.2× shorter** than the original GTS V2 full-ID/capacity/workspace adapter. This is a **non-paired supplemental comparison**, not a promoted optimization or a replacement for the frozen primary experiment.

The frozen development-selected 100% points **missed their final100% anchor on all eight shapes**. They remain failures of that anchor; no final-query tuning or query replacement was used. The primary six-round comparison admitted8/8 points at the99% minimum-quality target and4/8 at99.9% (all four Deep shapes), but0/8 at100%. Minimum-quality targets do not imply identical achieved recall.

The GIST diagnostic points to **GPU leaf-distance processing**, not uncovered CPU/IO gaps, as the principal cost. No causal coalescing control, NCU memory-sector counters, GTS++ production result or update workflow is established here.

## Equal achieved tie-aware quality: supplementary all-list control

All values below are **milliseconds per complete256-query Host-ready pass**; six original GTS processes and six later IVF processes. Training/build/setup/checks are excluded. The ratio is the marginal median GTS/IVF ratio. The CI is an **independent-process log-ratio bootstrap**, not a paired CI.

| Dataset | K | B | GTS median ms | Native IVF median ms | Median ratio | Independent geo-ratio95% CI |
|---|---:|---:|---:|---:|---:|---:|
| GIST | 8 | 1 | 90206.539 | 1119.098 | 80.61× | [80.43, 81.67] |
| GIST | 8 | 32 | 80210.614 | 652.313 | 122.96× | [122.93, 123.01] |
| GIST | 32 | 1 | 91091.811 | 1164.844 | 78.20× | [77.96, 78.23] |
| GIST | 32 | 32 | 81089.202 | 654.189 | 123.95× | [123.95, 124.03] |
| Deep | 8 | 1 | 10853.775 | 136.798 | 79.34× | [78.67, 79.49] |
| Deep | 8 | 32 | 8689.546 | 61.965 | 140.23× | [140.07, 140.32] |
| Deep | 32 | 1 | 10904.796 | 171.528 | 63.57× | [63.17, 63.62] |
| Deep | 32 | 32 | 8733.466 | 63.877 | 136.72× | [136.62, 136.81] |

**Deterministic tie-breaking caveat:** original GTS has100% deterministic-ID recall on these final sets. Native exhaustive IVF has100% on Deep, but99.804688% atK8 and99.938965% atK32 on GIST. All GIST disagreements in the exhaustive control are admissible exact-distance boundary ties. Thus this table is **not**100% deterministic `(distance,ID)` recall parity on GIST. Tie-aware recall was the registered anchor metric before development, not an after-the-fact metric change.

## Frozen primary configurations: quality misses retained

The table below shows every primary anchor/configuration, minimum final tie-aware recall across six rounds and median IVF pass time. GTS achieved100% tie-aware recall in every primary shape/round. Ratios are reported only for admitted targets; the complete paired estimates, order splits, wins, means, raw process values and p10/p90 are in [SUMMARY.json](evidence/SUMMARY.json).

| Dataset | K | B | Target% | nlist/nprobe | Final recall% | IVF median ms | Same minimum target admitted |
|---|---:|---:|---:|---:|---:|---:|---|
| GIST | 8 | 1 | 99 | 4096/256 | 99.511719 | 205.406 | yes |
| GIST | 8 | 1 | 99.9 | 4096/512 | 99.853516 | 278.483 | **no** |
| GIST | 8 | 1 | 100 | 4096/512 | 99.853516 | 278.483 | **no** |
| GIST | 8 | 32 | 99 | 4096/256 | 99.511719 | 69.728 | yes |
| GIST | 8 | 32 | 99.9 | 4096/512 | 99.853516 | 136.028 | **no** |
| GIST | 8 | 32 | 100 | 4096/512 | 99.853516 | 136.028 | **no** |
| GIST | 32 | 1 | 99 | 4096/512 | 99.780273 | 297.079 | yes |
| GIST | 32 | 1 | 99.9 | 4096/512 | 99.780273 | 297.079 | **no** |
| GIST | 32 | 1 | 100 | 4096/1024 | 99.987793 | 452.448 | **no** |
| GIST | 32 | 32 | 99 | 1024/128 | 99.328613 | 93.601 | yes |
| GIST | 32 | 32 | 99.9 | 4096/512 | 99.780273 | 136.845 | **no** |
| GIST | 32 | 32 | 100 | 4096/1024 | 99.987793 | 257.359 | **no** |
| Deep | 8 | 1 | 99 | 4096/128 | 99.267578 | 33.090 | yes |
| Deep | 8 | 1 | 99.9 | 4096/512 | 99.902344 | 45.022 | yes |
| Deep | 8 | 1 | 100 | 4096/512 | 99.902344 | 45.022 | **no** |
| Deep | 8 | 32 | 99 | 4096/128 | 99.267578 | 2.558 | yes |
| Deep | 8 | 32 | 99.9 | 1024/128 | 99.902344 | 5.850 | yes |
| Deep | 8 | 32 | 100 | 1024/128 | 99.902344 | 5.850 | **no** |
| Deep | 32 | 1 | 99 | 4096/256 | 99.609375 | 42.383 | yes |
| Deep | 32 | 1 | 99.9 | 4096/512 | 99.926758 | 56.340 | yes |
| Deep | 32 | 1 | 100 | 4096/1024 | 99.987793 | 83.025 | **no** |
| Deep | 32 | 32 | 99 | 1024/64 | 99.218750 | 3.962 | yes |
| Deep | 32 | 32 | 99.9 | 4096/512 | 99.926758 | 7.671 | yes |
| Deep | 32 | 32 | 100 | 4096/1024 | 99.987793 | 14.132 | **no** |

## Query-only GIST attribution (diagnostic, not latency substitution)

First32 final queries, K8, B1/32; original measured GTS binary versus native IVF1024/1024. Capture contains one complete `formal.query_pass` NVTX interval and no index construction. CUDA runtime return codes are zero. GPU temporal coverage is not SM utilization. API intervals overlap kernels and cannot be added to GPU time.

| Path | B | NVTX interval ms | Recorded GPU coverage% | Leaf/scan kernel ms | Device-sync calls | Device-sync inclusive ms | Kernel calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| GTS | 1 | 11451.304 | 96.865 | 10190.061 | 576 | 11049.666 | 1792 |
| GTS | 32 | 10198.521 | 99.866 | 10105.371 | 22 | 10172.536 | 93 |
| IVF | 1 | 141.673 | 97.370 | 133.920 | 0 | 0.000 | 192 |
| IVF | 32 | 82.117 | 98.876 | 81.048 | 0 | 0.000 | 7 |

For GTS/B32, `dataProcessKnn` accounts for **99.087%** of the profiled interval; only **13.624ms** has no recorded GPU work. Removing only those uncovered gaps while keeping the observed GPU schedule unchanged cannot explain the large external gap. This is **not** an upper bound on a combined layout/arithmetic/rescheduling change.

GTS/B1 performs672 query-range `cudaMalloc` calls and736 `cudaFree` calls; their inclusive totals are86.086ms and32.291ms, versus an11.451s range. Repeated allocation/control traffic exists, but these API durations do not dominate this high-dimensional workload. GTS/B32 records only0.009792ms of ordinary Device-to-Host copy activity and0.060405ms of unified-memory copy activity. Host-visible synchronization waits for much longer GPU execution. Missing page-fault/CPU instruction counters remain unknown, not zero.

Native IVF also spends most inclusive runtime API time inside `cudaMemcpyAsync` while queued kernels execute: actual recorded copy activity is tiny by comparison. A long API interval therefore must not be labeled physical-transfer time or CPU arithmetic. Detailed kernel/API/copy-kind inventories and raw trace hashes are in [TRACE_SUMMARY.json](evidence/TRACE_SUMMARY.json).

## Excluded setup costs (separate denominator)

| Dataset | GTS initial construction/cache validation ms (one development process) | GTS data load ms (same process) | IVF1024 train median ms (six control processes) | IVF1024 add median ms |
|---|---:|---:|---:|---:|
| GIST | 22810.900 | 1105.710 | 1495.549 | 1382.729 |
| Deep | 2422.170 | 160.094 | 282.514 | 349.370 |

The GTS initial number includes construction and cache writing/validation, is one observation, and is not a six-process build comparison. Formal GTS processes load that cache; every IVF process builds afresh outside its timed pass. Data setup, training-sample generation, reference construction and validation have their own scopes and must not be summed into the warm-query table.

## Gates and bounds

- Exact pinned original-source hashes; original search/pruning/math retained. MAX_H6,1GiB workspace, binary FP32 input and full-ID observation are documented adaptations, not an unmodified published GTS latency.
- Real final oracle: full-table FP64 explicit RN distance scan plus CPU bitwise spot checks. All formal distance-field gates pass; every quality miss is retained.
- Synthetic N4097 D96/960, duplicate ties, ragged33/B32 tail, eight repeated GTS and two IVF passes; GTS reused-cache query memcheck/synccheck pass. Initial-build/Faiss/oracle sanitizer and Graph support are uncovered.
- All retained GTS bins pass supplemental nonnegative/nondecreasing field checks; all four caches pass exact permutation/disjoint-leaf-partition checks. Separate frozen native validation replays retain full result hashes and add signed/sorted/pure-relative/zero-distance diagnostics; they do not replace original timing outputs.
- Driver590.48.01, CUDA13.1.115, native Faiss1.15.1 (`use_cuvs=False`), CuPy14.1.0, selected idle GPU7/NUMA3. Per-process locks, before/after admission, foreign-process checks and200ms GPU telemetry are retained. Clocks/power unchanged; whole-host CPU isolation and locked clocks are not claimed.
- Source, measured binary, data and cache hashes were rechecked after collection; selected GPU clear and the pre-existing GPU0 service still alive.
- Public portable runner repairs cleanup/new-lock edge cases and removes private aliases. Its hash differs from the frozen collection runner. Rebuilt adapter compiles on the intended host/GPU and passes the ragged synthetic full-ID smoke; rebuilt binary hashes differ and are not substituted into the main timings.

## Decision and next experiment

**External baseline decision:** retain native IVF as a strong required kNN comparator. The frozen approximate100% selections failed; the fixed exhaustive control establishes equal achieved tie-aware quality, with its non-paired limitation. No current GTS++ implementation is measured by this experiment.

**Mechanism decision:** on this GIST subset, prioritize the dominant leaf-distance kernel and compare the current GTS++ keeper under the same contract. To attribute a gain to coalescing, preserve the declared arithmetic/quality gate and run a layout-only control with memory-sector/request counters plus Host-ready timing. CPU waiting may shrink when GPU execution shrinks, but that is not evidence of eliminated CPU computation or eliminated transfer bytes.

No claim applies to insert/delete, mixed update workloads, external queries, all GPU trees, Tensor Core suitability or a complete application including construction.
