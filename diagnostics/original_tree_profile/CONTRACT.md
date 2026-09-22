# Original-tree CPU / GPU boundary diagnostic

Experiment: `gts_20260922_original_tree_cpu_io`. Designed before runtime data.
State: designed; GPU 0 occupied at preflight. GPU 1 requires explicit admission.
No production algorithm, paper, GPU setting, or foreign process is changed.

## Hypotheses and cheapest tests

| ID | Hypothesis | Test | Rejection / limitation |
|---|---|---|---|
| H1 | High host CPU during GPU queries includes active CUDA waiting | Same instrumented binary, default versus blocking device scheduling, direction-balanced fresh processes | Reject the spin-dominance diagnosis if CPU time does not materially fall; lower CPU alone is not a wall-time speedup |
| H2 | GPU-Tree construction issues N host node allocations | Nsight CUDA API counts within the getIndex range; compare input N with calls and time | Call counts establish amplification; an allocation-pool speedup is not measured by this experiment |
| H3 | Query cost is bulk host-device data transfer | GPU timeline and explicit transfers, plus a separate UVM-enabled trace where available | Small explicit memcpy totals do not rule out UVM migration; unsupported UVM evidence leaves that part unknown |
| H4 | GTS update query allocates/scans repeatedly even without a changed bitmap | Query-only operation trace through native update entry, per-phase/API accounting | This isolates update-query plumbing, not dynamic insertion correctness or full mixed-workload throughput |

## Frozen first-stage scope

- Hardware: RTX PRO 6000 Blackwell, CUDA 13.1.115, Nsight Systems 2025.5.2;
  actual admitted UUID, process inventory and clocks recorded before each run.
- Author source commit/hashes: `../original_tree_redundancy/SOURCE_PINS.json`.
  All generated files are scratch copies; source tree stays untouched.
- Real input: deterministic evenly spaced subset of Words (raw byte strings).
  First size N=2000, Q=32, radius 4, k=4. Native GTS MAX_H=3 and leaf cap 20
  are sufficient for this size. A smaller smoke subset N=1000 is also retained.
  Query IDs are deterministic and input/oracle hashes are saved.
- Query-only update trace: 32 searches with the same IDs, no insertion/deletion.
  The native driver's update-average divide by zero is not an admitted timer;
  use the explicit phase scope and per-query results instead.
- GTS query workspace is explicitly bounded to 256 MiB in the diagnostic copy,
  rather than converting half a 96-GiB device's free space to 32-bit elements.
  This is a disclosed portability/resource adaptation, not untouched-native
  large-workspace performance. No leaf, pruning, distance, aggregation or
  batching algorithm is optimized. GTS's serial reductions remain intact.
- GPU-Tree initial pivot seed is fixed to 0 to make default/blocking comparisons
  reproducible. Unused local pointers are initialized to null solely for safe
  cleanup. Neither change removes query/build work.
- Output parity: GTS native range counts and kth distances; GPU-Tree range counts
  and kth distances exported after its search timer. Independent CPU full-table
  edit-distance oracle includes self (distance zero). Query-only update counts
  must match the same oracle; a failure narrows that path to diagnostic-only.
- Timing: named inclusive function wall and main-thread CPU time, no added GPU
  synchronization inside phase scopes. Whole-process CPU is recorded separately.
  No nested durations are added. Validation/output work is outside query scopes.
- First observation is cold. Six fresh-process default/blocking pairs (3 each
  relative order), no per-process warmup: this measures the native one-shot
  lifecycle with load/build/query separately, not steady-state service latency.
  No profile durations are substituted for unprofiled phase timing.
- Correctness smoke precedes profiling; bounded memcheck and synccheck are
  collected. Failing correctness/sanitizer results are retained, not promoted.
  A failed path may still be traced to localize an error, explicitly unvalidated.
- Clean CPU fractions and wall times are reported per path with process medians,
  paired ratios and raw order, not as an all-workload speedup claim. No optimized
  keeper is selected. Do not claim full-ID correctness from count/kth checks.
- Standard-library tools and the existing `cpu_io/profile.hpp` are reused.
  No new benchmark framework or dependencies. CPU sampling remains disabled
  because host perf permissions deny it; no security settings are changed.
- One nonblocking GPU advisory lock, idle/process checks before/after each run,
  120 s process timeout (300 s under sanitizer), fresh output paths, stop on
  foreign GPU activity or unexpected errors. Terminate only task-owned children.

## Publication / decision ledger

H1-H4 initially **unknown**. Raw logs, source/binary/input hashes, commands,
failed gates and reports remain in ignored local evidence. A report/manifest
may be committed locally; public upload remains blocked by the earlier unresolved
repository visibility/disclosure question. No current result is paper-ready.

## Predeclared scale extension (after bounded smoke, before scale data)

GPU 0 became idle and was admitted by live process checks. All ten bounded
smoke cases matched the CPU oracle. GTS passed both sanitizer tools; GPU-Tree
range failed on invalid cleanup frees and kNN failed on an out-of-bounds write
in `initPQ`. GPU-Tree is excluded from clean paired performance statements.
Its trace is diagnostic only, and build/API counts precede the failing boundary.

Extend **GTS only** to an evenly sampled Words N=65,536, Q32, r4 / k4, and
32 query-only update operations. Preserve the 256 MiB workspace and change only
`MAX_H=3` to `MAX_H=5` in a separate copy: the original height cannot represent
this size with its 20-point leaf cap. This is an explicitly adapted-original
algorithm, not an untouched default configuration. Source and binary hashes
are separate. Generate the same independent CPU oracle, run whole-N memcheck
and synccheck before paired measurement, retain six fresh-process pairs in
AB/BA order, and collect one separate UVM-enabled trace per path. If a gate
fails, stop promotion of that path; do not reinterpret a fast wrong answer.
