# Rebuild localization: shallow pivot-distance work dominates

**Both new independent diagnostic captures identify the shallow `getPivotDis`
launches, not sorting, as the main remaining construction cost.** The root has
one 512-thread block processing 1M objects. The first two layers account for
about 22.49 s of the ~23.0 s pivot-kernel sum. This supports a same-semantics
node-object tiling intervention; it is not a measured tiling speedup or novelty.

## Frozen scope and admission

The parent is `a8cc8031bd75768a400c4bb9393098c6d574c96a`, original FP32 GIST
N1M/D960/B1/K8, radius bits `0x3f34a3d8`, occupancy 10. A is the common-repaired
staged range path + integrated FULL kNN, not untouched original GTS. B is
PAR+FULL. Each fresh process runs the same cloned 19-event warmup, releases it,
restores the original state, then runs the first 51 events of the frozen
336-event trace. This contains 31 queries, ten inserts, ten deletes, one real
rebuild at zero-based event 48, and post-rebuild kNN/range at 49/50.

The capture starts before submission of event 48 and stops after its existing
ACK fence. Host NVTX marks do not add device synchronization or change launches.
All 112 normalized GPU functions are identical to the phase-B target:
`7d0ff1767e79a2dbc1f8ea18e52d29015d3d5a99ce4491dab8836d75b5f40948`.
The diagnostic binary SHA is
`ddf30c52360dc4ceb01f54608bf3b0bb967e62535a1fa7107291ca6835c12cc9`.
Both original guards passed with no foreign GPU activity and empty pre/post
compute-process lists. Complete prefix and warmup IDs/FP32 fields match the
admitted parent byte-for-byte; state/ACK rows match. The independent exhaustive
quality scope is bound to the parent's retained full CPU proof, not called a
new independent exhaustive replay in this phase.

## Actual layer ledger

Times below are milliseconds from two single NSYS captures, **diagnostic-only**.
GPU launches are attributed by CUDA correlation ID and issuing Host NVTX range,
not by blindly requiring an asynchronous kernel to end within a Host range.

| Layer / grid blocks (512 threads each) | A Host inclusive | A GPU pivot | B Host inclusive | B GPU pivot |
|---|---:|---:|---:|---:|
| 0 / 1 | 20442.475 | 20442.436 | 20443.261 | 20443.223 |
| 1 / 10 | 2046.177 | 2046.155 | 2046.543 | 2046.509 |
| 2 / 100 | 205.942 | 205.927 | 206.371 | 206.351 |
| 3 / 1000 | 125.892 | 125.879 | 125.891 | 125.875 |
| 4 / 10000 | 142.794 | 142.781 | 143.099 | 143.085 |
| All five pivot launches | — | 22963.179 | — | 22965.042 |

Each target layer partitions the same 1M positions into 1/10/100/1000/10000
nodes. The source performs an L2 distance loop over 960 coordinates for each
split member. These are source/shape-derived work quantities, not dynamic NCU
instruction or sector counters. The internal topology/key identity gate remains
mandatory before admitting a different mapping.

| Additional boundary | A | B | Unit / interpretation |
|---|---:|---:|---|
| Captured event 48 Host interval | 23790.103 | 23745.626 | ms, rebuild insertion through ACK |
| Five sort Host ranges, total | 3.582 | 4.006 | ms, includes sorting call overhead |
| All `cudaDeviceSynchronize` calls | 23706.606 | 23643.495 | ms inclusive Host; overlaps GPU execution |
| Synchronization API calls | 16 | 18 | calls in captured maintenance window |

Allocation/init, compaction, nodeSplit/reduce, common refit, PAR refresh,
mirror repack, release and publication are all retained in the per-stage JSON,
with kernel grids, resources, API counts and observable copy/fault events.
**Do not add Host + GPU + migration times.** Nested ranges and asynchronous
fault events overlap. NSYS instrumentation, CPU stack sampling and UM fault
collection also perturb this diagnostic; none is a primary timing denominator.

## CPU attribution and IO boundary

Own-process CPU sampling was collected without modifying shared device/kernel
settings. A has 12,398 leaf samples: 10,472 in `libcuda.so.590.48.01` and 1,867 in
`[vdso]`; B has 12,376, including 10,533 driver and 1,779 `[vdso]` samples. Most
sampled driver symbols are unresolved PCs. Together with ~23.6–23.7 s inside
synchronization APIs and actual ~23 s GPU pivot work, this supports host
synchronization/driver waiting as the main explanation of the captured CPU
occupancy, not CPU distance arithmetic. The precise polling/wait implementation
and effective CPU instruction mix remain **unknown**. A leaf-module sample
fraction is not a CPU-time fraction or effective-computation count.

Explicit copies and observed UM migrations/faults are retained, including their
byte counts when exported. They are not silently treated as complete traffic,
exclusive IO costs, avoidable redundancy or proof that all GPU trees share the
same bottleneck. No NCU replay was needed to choose this bounded next test;
occupancy, sectors and memory-instruction mechanisms are not claimed measured.

## Decision and five-link boundary

| Avoidable cost | Mechanism hypothesis | Module | Effect gate | Workflow gate |
|---|---|---|---|---|
| Shallow large nodes use only 1/10 blocks | Multiple object tiles per node; 512 positions initially | planned build_distance_tiles | Same complete keys/pids/sort/topology; larger grid; actual module cost | fresh B0/B1 six paired 336-event processes, not yet run |
| Repeated full maintenance after few updates | Later policy study, not implemented here | maintenance_policy | Canonical occurrence trace, residual-state/drain accounting | Not admitted by this diagnostic |

The mapping inefficiency is not duplicate distance computation. Tiling is an
engineering/strong-baseline intervention, not automatically a main research
contribution. Sorting, build arithmetic, pivots, threshold, query kernels and
output semantics must stay unchanged in the next single-mechanism candidate.
The 96B context-symbol leak diagnostic remains unresolved; no leak-clean,
production, long-workflow or global-default status follows.

## Sources

- [Pinned original build source](https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GTS/include/tree.cuh).
- [NSYS attribution guide](https://docs.nvidia.com/nsight-systems/AnalysisGuide/index.html).
- [Phase-B complete workflow and counterevidence](../unified_target_workflow/phase_b/RESULTS.md).
