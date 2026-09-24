# Bounded workflow attribution contract — 2026-09-24

User authorization now permits other idle GPUs. Use GPU2 UUID recorded by the
runner, with fresh admission and the existing per-device lock for every process.
Do not mix this GPU's timings with the earlier GPU0 correctness observations.
No clock/driver settings or foreign processes are changed.

The base is the pinned original GTS plus the separately named one-line rnum reset.
The diagnostic copy adds host wall/main-thread CPU clocks and NVTX ranges only.
All 50 CUDA kernel source bodies are checked byte-for-byte unchanged. It retains
native height3, leaf limit20, buffer threshold10 and THREAD_NUM512. The same
instrumented binary selects default or blocking synchronization before context
initialization; actual CUDA scheduling flags are recorded. Neither policy is an
algorithm optimization. An uninstrumented reset binary controls instrumentation.

Reuse the previous N1000/D128 integer-L2 data. Query128 issues 128 radius-zero
queries for row0. Mixed16 repeats the following 27-operation cycle 16 times:
query; insert row0; query; delete logical row1000; query; insert row0 ten times
(native rebuild); query; delete logical row1000 ten times; query. Thus there are
432 operations, 80 queries and 16 rebuilds. Per-cycle counts are 1,2,1,11,1.
Row0 is retained at position0 through every compaction; original/current identity
agrees for every inserted/query row. Both peak live rows and rebuilt tree size are
1010. An independent active multiset computes every count from integer distances.
This is a bounded repeated correctness/attribution workload, not SIFT/GIST or a
representative throughput benchmark.

Finite plan, frozen before timing:

- 14 gates: reset clean/memcheck/synccheck for both cases; diagnostic clean for
  both policies and both cases; diagnostic mixed16 memcheck/synccheck for both
  policies. Any semantic/runtime/sanitizer failure stops the suite.
- Three process-level comparisons per case, order RDB, BDR, DRB. R is the
  uninstrumented reset/default binary; D and B use the same diagnostic binary.
  No sample selection or repetition based on timing outcomes. Report all pairs
  and descriptive medians; three repetitions do not justify broad speed claims.
- Four NSYS traces: each case/policy, CUDA+NVTX+OS runtime with CPU/GPU UM fault
  tracing. These are for attribution only and are excluded from clean timings.

Main-thread CPU clocks include active CPU execution and CPU busy waiting, not GPU
work. Host range wall times include existing CUDA waits and UVM handling.
Nested ranges are inclusive: rebuild is inside insert; build.total includes the
initial build as well as rebuild calls. Never sum overlapping ranges. Report
update.total separately from runtime initialization/input/initial construction.
Compare R/D native query-time fields to reveal diagnostic overhead; these are
printed averages rounded to six decimal places. Query-only native update-time
fields divide by zero and are not timing observations.

NSYS GPU intervals are clipped to NVTX ranges and unioned; GPU temporal coverage
is not SM utilization or compute throughput. API wall time overlaps GPU work and
must not be added to it. Gaps are unclassified, not automatically CPU arithmetic.
Missing fault tables/counters mean unavailable, not zero. Explicit copy activity
and UVM migration must remain distinguishable where the trace allows it.

Preserve raw commands, source/binary/input hashes, counts, flag checks, process
exit status, sanitizer output and GPU admission snapshots in new run directories.
No additional optimization, NCU pass or large workload is part of this round.
