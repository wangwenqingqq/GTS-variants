# Privileged NCU: generic FP64 `pow`, not bulk memory bandwidth

**The profiled original GTS SIFT leaf path is dominated by general-purpose
FP64 power-function work.** This narrows the previous unknown bottleneck:
`__internal_accurate_pow` accounts for 89.29% of executed warp instructions and
about 91.6% of sampled stalls; the FP64 pipeline is utilized at about 86%, while
DRAM throughput is about 0.02% in the primary case. This is a same-binary
hardware-counter diagnosis, **not a measured optimization or speedup**.

## 1. Counter evidence

All rows below are NCU diagnostics, not clean query timings. Two large-leaf
rows are independent fresh processes; the smaller leaf is a boundary check.

| Native operation / workload | NCU duration ms | FP64 pipe utilization % | DRAM throughput % | Achieved occupancy % |
|---|---:|---:|---:|---:|
| Leaf Q128/r500, repeat 0 | 610.500 | 86.07 | 0.02 | 16.82 |
| Leaf Q128/r500, repeat 1 | 584.347 | 86.06 | 0.02 | 16.83 |
| Leaf Q32/r300 | 128.942 | 85.82 | 0.00* | 16.75 |
| Internal Q128/r500, level 0 | 1.456 | 1.14 | 0.00* | 29.94 |
| Internal Q128/r500, level 1 | 1.466 | 11.39 | 0* | 33.28 |
| Internal Q128/r500, level 2 | 2.950 | 56.76 | 0.00* | 42.83 |
| Internal Q128/r500, level 3 | 20.397 | 81.86 | 0.00* | 64.00 |
| Aggregation Q128/r500 | 10.438 | 0 | 0.00* | 8.33 |

\* NCU's exported precision; zero/0.00 does not prove that no bytes moved.
For example, the smaller leaf records 2,269,184 DRAM read bytes and 4,097,792
write bytes. The two large leaves record 53,191,168/53,908,992 read bytes and
123,497,984/123,590,400 write bytes under replay. These are device-memory
transactions, not CPU-GPU link bytes, and must not be reinterpreted as PCIe IO.

The exact metric names are
`sm__pipe_fp64_cycles_active.avg.pct_of_peak_sustained_elapsed`,
`gpu__dram_throughput.avg.pct_of_peak_sustained_elapsed`,
`sm__warps_active.avg.pct_of_peak_sustained_active`, and
`gpu__time_duration.sum`. All exported non-address performance metrics and
units are in [metrics.csv](metrics.csv). No missing metric is replaced by zero.

Clock control was explicitly disabled. The 584–611 ms repeat variation cannot
be used as a performance result; primary FP64/DRAM/participation counters agree.
Replay uses 38–39 passes for leaves and 35 for the other kernels, with no cache
flush requested. Replay, warm-cache effects, profiler memory save/restore,
managed memory and a shared host prevent treating these durations as clean
application times. In particular, the aggregation's 10.438 ms does not replace
the earlier 22.171 ms mean from the lighter Nsight Systems trace.

## 2. Source-to-instruction attribution

The unchanged leaf L2 source contains, schematically:

```cpp
result += pow(point[j] - query[j], 2);  // each of 128 coordinates
result = pow(result, 0.5);
```

The actual profiled binary executes the general `__internal_accurate_pow`
helper, not merely a multiply for each square. Runtime source counters show
four unrolled power call sites at relative leaf PCs 5792, 6720, 7568 and 8432,
each reached by 40,709,216 warp calls / 266,888,544 predicated-on thread calls,
plus the final call at relative PC 10096 with 1,272,163 warp calls /
8,340,267 predicated-on thread calls. The call-site sums match the helper's
entry counts exactly:

| Primary leaf quantity | Both repeats |
|---|---:|
| Total executed warp instructions, including helper | 82,850,110,074 |
| Warp instructions inside accurate power helper | 73,979,421,387 |
| Helper share of executed warp instructions | 89.2931% |
| Helper warp entry/call count | 164,109,027 |
| Helper predicated-on thread entry/call count | 1,075,894,443 |
| Processed non-self point distances, derived from final call | 8,340,267 |
| Calls per processed point distance | 129 = 128 squares + 1 root |

Helper sampled-stall shares are 91.5804% and 91.5654%; these are shares of
profiler samples, **not additive shares of wall time**. The smaller leaf has
89.3055% of warp instructions in the same helper, supporting the diagnosis
beyond one query batch. Internal kernels also execute this helper; across their
four launches it accounts for 90.3978% of warp instructions.

[Instruction ledger](instruction_ledger.csv) preserves warp, thread and
predicated-on thread totals separately by function/opcode. [EVIDENCE.json](EVIDENCE.json)
retains relative call sites, top sampled sites and static selected-function
hashes, including the 480-instruction helper. No raw vendor SASS or runtime
addresses are published. Every source-group instruction sum matches the NCU
hardware warp-instruction total for its run.

The whole executable hash is
`41920f5cb28b209a2b49598a7c413f714f588dc48b3a6629499c349f05f37951`.
The three native function hashes match the preceding query-stage campaign.
The result is specific to this compiled source/toolchain/resource-adapted
baseline; it is not a claim about every historical GTS binary or all GPU trees.

## 3. Other inefficiencies are real, but not the leading current explanation

- The large leaf launches 1,272,163 blocks of 512 threads, with 44 reported
  registers/thread (48 allocated), 47,536 bytes of reported launch stack,
  theoretical occupancy 66.67% and achieved occupancy 16.82–16.83%.
  The prior static resource report's 47,528-byte frame is a different reporting
  quantity; do not silently equate it with NCU's launch stack size.
- Average executed/predicated-on threads per warp instruction are 6.87/6.77.
  This is now dynamic participation evidence, not simply a source-code bound.
  It does not mean 6.77/512 or achieved occupancy is the useful-lane fraction.
- Primary leaf scheduler averages are 2.02 active warps and 0.08 eligible warps
  per scheduler per active cycle; issue-active is 7.77%. Short-scoreboard and
  fixed-latency wait averages are 14.70–14.71 and 9.76 cycles per issued
  instruction, versus 0.29 for long-scoreboard. Top samples are in the power
  helper's arithmetic/dependency path. Stall labels alone do not prove that a
  particular memory or synchronization mechanism caused the delay.
- Global-load useful bytes per sector are only 4.02 out of a 32-byte sector;
  access efficiency is poor. Nevertheless, measured DRAM/L1/L2 throughput is
  low while FP64 is highly utilized. Poor coalescing can coexist with an
  arithmetic bottleneck; it is not evidence that bulk bandwidth is saturated.
- Aggregation has only 0.02 eligible warps/scheduler and 41.72 long-scoreboard
  cycles per issued instruction, with no power-helper work. That is a different
  latency/parallelism diagnosis, not the main SIFT leaf computation mechanism.

These measurements support an FP64 power-path bottleneck. A same-contract
single-mechanism ablation is still required to quantify removable cost.

## 4. Revised next control and research boundary

**Prioritize a leaf-only L2 power-function control before the 512-to-32 launch
control or a TC rewrite.** Keep the tree, candidates, buffers, one-thread-per-point
mapping, 512-thread launch and all other stages unchanged. Replace general
power for squaring with explicit multiplication and use an explicit root
operation; preserve/count-check the declared integer SIFT semantics. Validate
full oracle, sanitizer and paired complete-query timing against the original
in the same campaign. No such optimization was implemented or timed here.

The later launch-size and access-layout controls remain worthwhile, especially
after the power path is removed. Do not combine them into the first ablation.
A future TC comparison should include the ordinary optimized scalar L2 path;
beating unnecessary general FP64 power work alone is not a tree-specific TC
contribution. This implementation/compiler-path issue does not establish a new
thesis or an inherent redundancy of all GPU trees.

## 5. Access, validation and reproduction

The user authorized this privileged follow-up after the earlier unprivileged
attempt was denied. `sudo ncu` successfully collected counters, consistent with
[NVIDIA's administrative profiling access guidance](https://developer.nvidia.com/nvidia-development-tools-solutions-err_nvgpuctrperm-permission-issue-performance-counters).
No driver settings, capabilities, modules, clocks or foreign jobs were changed;
`RmProfilingAdminOnly` remained 1. GPU0 was clear before/after every process.

Hardware/software: RTX PRO 6000 Blackwell Server Edition, 188 SMs, driver
590.48.01, CUDA13.1.115, NCU2025.4.1.0 build37053803. SIFT N65,536/D128,
Q128/r500 primary and Q32/r300 boundary; exact range counts include self.
[Contract](CONTRACT.md) was frozen before collection. Two new unprofiled checks
and five profiler processes all passed the independent integer oracle. Parent
memcheck/synccheck gates were verified by exact binary hash; sanitizers were not
rerun here. No correctness result for IDs, kNN/updates, Graphs or general floats.

One runner watchdog correction was made after collection: the two initial
unprofiled checks originally lacked a timeout and completed in 8.578/4.040 s;
the delivered runner wraps them in the same 600-second task-only timeout. All
five measured NCU processes already had that timeout. The original collection
runner hash and final delivery source hashes are separately retained; the
benchmark binary and profiler commands were not altered. The delivered runner
also captures the same provenance schema automatically instead of a separate
post-collection CPU-only command. Its reproduction interface requires the
versioned NCU launcher to pin the corresponding core executable, rather than
the toolkit dispatcher that selected the same verified core during collection.

Use the original measured parent scratch, or reproduce its build and explicitly
rebind the binary provenance before a new campaign. A fresh rebuild may have a
different container hash even with identical selected SASS; do not bypass the
runner's exact-binary assertion. Set `PARENT_SCRATCH`, an absent `NCU_OUTPUT`,
`NCU` to the absolute versioned installation launcher (`$NCU_INSTALL_ROOT/ncu`,
not the CUDA toolkit dispatcher), and `ADMITTED_GPU0_UUID` after
checking allocation. Administrative access must already be authorized.

```sh
python3 diagnostics/query_breakdown/ncu_privileged/test_analysis.py
python3 diagnostics/query_breakdown/ncu_privileged/run.py \
  "$PARENT_SCRATCH" "$NCU_OUTPUT" --gpu "$ADMITTED_GPU0_UUID" --ncu "$NCU"
```

Collection begins only after parent fixture, binary and sanitizer receipt checks.
The delivered runner captures the NCU version/core-executable hash, static
function hashes and final GPU snapshots in private `provenance.json`. Then
curate with:

```sh
python3 diagnostics/query_breakdown/ncu_privileged/analyze.py "$NCU_OUTPUT" "$CURATED_OUTPUT"
```

Raw reports, source CSVs, full commands and receipts remain private; their sizes
and SHA256 hashes are retained in the public ledger. Portable numeric CSVs and
source-derived counts contain no process identity, private path or absolute PC.
