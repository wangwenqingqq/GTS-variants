# Unmodified GTS whole-flow utilization diagnostic

Experiment: `gts_20260923_original_flow_words`. State: designed before new runs.
This extends the September 22 attribution campaign, not an optimization campaign.

## Frozen boundary

- Primary executable: freshly compiled, byte-identical author GTS CUDA sources
  pinned by `../original_tree_redundancy/SOURCE_PINS.json`; no workspace cap,
  height change, waiting-policy change, instrumentation, or kernel repair.
- Hardware: RTX PRO 6000 Blackwell Server Edition, GPU 0 only after live idle
  checks and the existing nonblocking GPU lock. CUDA 13.1.115, GCC 13.3,
  driver 590.48.01, NSYS 2025.5.2, NCU 2025.4.1. No clock/security changes.
- Baseline workload: existing Words N=2000 raw-byte subset, 32 deterministic
  query IDs, inclusive r=4 / k=4. Native MAX_H=3, fanout=10, leaf cap=20.
  Range, kNN, and query-only update entry are tested separately. No insertion
  or deletion and no full-dataset throughput claim.
- Correctness: retained independent CPU count/kth-distance oracle, not full IDs.
  Fresh smoke first; memcheck and synccheck before interpreting valid paths.
  Failed paths may be profiled only to locate their failure, never promoted.
- Longer observation: repeat the same 32 IDs 128 times (4096 queries), preserving
  their order and expected counts/distances. Three independent unprofiled
  processes per admitted path, then separate NSYS and NCU runs. This is the
  native one-shot load/build/query lifecycle, not an artificially fused service.
- Stop rule: 120 s ordinary process, 300 s sanitizer, 180 s NSYS/NCU; stop on
  foreign GPU activity, output mismatch, or unexpected runtime error. Terminate
  only this campaign's process group. Failed receipts remain append-only.

## Questions and evidence

| Hypothesis | Test / denominator | Important alternative or falsifier |
|---|---|---|
| CPU utilization is high | Process user+system seconds divided by process wall; 100% means one CPU core; temporal process sampling where available | Startup and active CUDA waiting are not useful CPU arithmetic; host has many cores |
| GPU memory use is small | Baseline-relative device used-memory samples, native allocations from NSYS, capacity fraction, input size | Low capacity occupancy can be appropriate for a small dataset; native static workspace policy may allocate much more |
| GPU has intermittent work | Unprofiled management samples plus NSYS union of kernel/copy/memset intervals, gaps, and binned activity | Management utilization is windowed; a kernel's presence does not imply all SMs are busy |
| Running kernels underuse the GPU | Targeted NCU LaunchStats, Occupancy, SpeedOfLight, SchedulerStats/WarpStateStats when permitted; NSYS grid/block metadata as a weaker fallback | NCU replay perturbs latency; permission failure leaves hardware utilization unknown |

NSYS: whole-process CUDA/NVTX/OS runtime trace, memory allocation tracking and
UVM faults in a separate diagnostic recording; no denied CPU sampling. API time
can overlap GPU activity and is not added to kernel time. Gaps are unattributed,
not automatically CPU-bound. NCU uses `--clock-control none`; replay timings
are not clean application latency. If profiling counters are denied, retain the
exact failure and do not elevate privileges or silently replace counter evidence.

The prior novelty/prior-art screen remains in the adjacent audit. This task asks
for measurement, not a new paper thesis. Reports/scripts/numerical summaries and
hashes may be published under the user's existing authorization; raw data,
source copies, logs, device identities and machine configuration remain ignored.

## Trace-overhead control, declared after full trace and before light trace

The full UVM/allocation trace lengthens the update query span relative to clean
native timing. Add one NSYS recording per valid path with UVM fault and allocation
tracking disabled (`nsys-light`) to check whether temporal gaps persist. Keep both
traces; do not use either as clean throughput. Long memcheck and synccheck were
also added for all 4096 queries; earlier 32-query gates remain bounded evidence.

The first sanitizer and full NSYS attempts were stopped by a conservative
monitor: descendant tracking initially missed children that exited before a
snapshot or were launched from a profiler worker thread. Retain the stopped
runs; track all task-thread child lists and retain known child IDs on retries.
Only the campaign process group was signaled. No original source/binary changed.

After the hardware-counter permission failure, attempt one NCU LaunchStats-only
collection to determine whether non-counter launch metadata are permitted. This
is not a replacement for achieved occupancy/SM/DRAM counters and changes no
permissions, user identity, device clocks, or application source.
