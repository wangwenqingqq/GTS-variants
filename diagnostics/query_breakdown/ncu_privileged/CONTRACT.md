# Privileged counter follow-up — frozen 2026-09-23

Parent delivery: 11f93aae8357063407f84c337fd3ce0109a1bb16. User explicitly
requests another NCU attempt using the existing administrator privileges. This
is a new diagnostic follow-up, not a rewrite of the earlier denied attempt.
No optimization or novelty claim; no candidate/keeper promotion.

## Invariants and admission
- Reuse the original measured bench5 binary and frozen fixtures, with hashes
  checked against the parent EVIDENCE.json. No recompilation or source changes.
- SIFT: N=65,536, D=128, exact integer L2 range counts including self; Q128/r500
  primary and Q32/r300 boundary. MAX_H=5, MAX_SIZE=20, 256 MiB workspace.
- Default CUDA wait policy. Full-table CPU integer oracle; one correct query
  and three warmups before cudaProfilerStart; all three measured outputs checked.
- Physical PRO 6000 Blackwell GPU0 only. CUDA13.1.115, driver590.48.01,
  NCU2025.4.1. Existing memcheck/synccheck gates bind to the SAME binary/shape;
  rerun an unprofiled correctness check for both shapes before profiling.
- Global /tmp/gtspp_gpu0.lock plus pre/post idle checks; stop on contamination,
  correctness failure, profiler error or timeout. Preserve every attempt.
- Use sudo only for the explicitly named profiler command, under a 600-second
  timeout per process. No driver reload, reboot, capability/configuration change,
  clock locking, process killing outside the task or foreign GPU access.
  RmProfilingAdminOnly must remain 1. Other GPUs may be busy on this shared host.

## Collection order
1. Fresh unprofiled correctness: Q128/r500, Q32/r300.
2. Leaf Q128/r500, first measured launch, two fresh processes.
3. Leaf Q32/r300, first measured launch, one fresh process.
4. Aggregation Q128/r500, first measured launch, one fresh process.
5. Internal node Q128/r500, four levels of the first measured query, one process.

NCU uses --profile-from-start off with the driver's existing cudaProfilerStart,
matching kernel names, kernel replay, --cache-control none, --clock-control none.
Collect SpeedOfLight, ComputeWorkloadAnalysis, MemoryWorkloadAnalysis_Tables,
LaunchStats, Occupancy, SchedulerStats, WarpStateStats, SourceCounters and
InstructionStats. Keep full reports privately plus portable raw metric CSVs
(after removing runtime IDs, process/file paths and absolute addresses).

No launch change, warp rewrite, L2 specialization, TC integration or throughput
campaign is authorized by this contract. The 512-to-32 control remains separate.

## Decision and limitations
- Diagnose arithmetic saturation, memory traffic/dependency, sparse useful lanes,
  and launch/resource effects symmetrically. High occupancy alone is not useful
  occupancy; high cache hit rate alone is not efficient transactions.
- Preserve SM/DRAM throughput, duration, bytes/sectors/requests, scheduler
  active/eligible/issue, warp/thread execution, dominant stalls, resources and
  selected-function identity. Missing/unsupported metrics remain unknown.
- Source-counter PC reach is not predicated-on participant count. A sampled
  stall identifies an observation site, not a causal mechanism proof.
- NCU kernel replay changes execution and may perturb caches/managed memory;
  --cache-control none does not reproduce a clean warm-query cache state in
  every pass. These durations are profiler diagnostics, never substituted for
  the earlier clean host timings or used as speedup denominators.
- Two primary leaf profiles are a repeatability check, not a confidence interval
  or benchmark distribution. Do not generalize SIFT evidence to Words/all trees.
- Reopen the next single-mechanism control only from the collected evidence;
  report failure/uncertainty rather than inferring a bottleneck from absent data.
