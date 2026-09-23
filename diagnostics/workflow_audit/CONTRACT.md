# Complete GTSPP workflow audit — 2026-09-23

Frozen before new measurements. Parent 6b303b4; target is the 17 native pins in
../cpu_io/SOURCE_PINS.json, archive/GTS_incremental, not Safe-C1 or original GTS.
No novelty claim and no kernel optimization/promotion in this audit. Preserve
native sources and previous positive/negative campaigns.

Scope: enumerate every custom CUDA kernel definition in all pinned headers,
every launch and Thrust/CUDA boundary site; classify native entry, conditional
API, unused compiled code, and alternative unselected headers. Cover load,
initial build, static RNN, all four kNN overloads, update query qnum1 and general
API fallback, direct insert, overflow buffer, all three deletes, rebuild,
calibration/output and cleanup. Every row must carry memory access reasoning,
a candidate or explicit no-change decision, correctness constraint and evidence
state. A source audit is not a measured speedup; uncovered runtime paths remain
explicitly unmeasured. Existing static-query evidence is provenance-linked, not
silently reclassified as update-query evidence.

New dynamic diagnostic only: RTX PRO6000 Blackwell, GPU0 UUID verified at admission,
CUDA13.1.115, native default CPU waits, native tree/layout/pruning and allocation.
Use GPU0 lock and per-process idle checks; other GPUs/users remain untouched.
No driver changes or foreign process termination. All data/code/output in a new
scratch directory. Reuse pinned SIFT N2,000 and N65,536 128D integer data. Native
update replay references already loaded rows (possibly duplicates), not true
arrivals. Small scenarios explicitly cover query-only, base delete, direct
insert/delete, leaf capacity overflow, buffered query/delete, and rebuild.
An independent active-row multiset oracle checks counts; native self-inclusion
and all-include sentinel differences must be reported, not normalized silently.
Input, setup, build, query, mutation and output ranges remain distinct. Diagnostic
instrumentation adds no GPU synchronization except explicit oracle validation
outside recorded native operations. No performance ranking from failed correctness.

Run bounded checks/sanitizers first. Stop a scenario on an error, retain it, and
continue only independent processes/path probes. Profiling an invalid native
workflow is allowed only for diagnosis with that label, never as an optimization
baseline. Use NSYS to enumerate selected kernels/calls and CPU boundaries. Use
NCU on valid representative calls for access-efficiency evidence; absent counters
are unknown, not proof of coalescing or no opportunity. No exhaustive workload,
all-metric, sustained speedup or production-safety claim.

Before representative counter collection: NCU targets the first matching native
kernel in each process, not every level/distribution. Update/build uses N2,000;
static V2 uses N65,536/Q128 (RNN r500, kNN k100), checked original A binaries from
the prior pinned campaigns. All binary hashes are reverified. Static captures
start at cudaProfilerStart after checks/warmups. Direct/native update captures
include startup but select named kernels. Additional vector and kth probes cover
those selected shared kernels. Counters are not aggregated across these different
shapes. Every named definition without a matching observation stays unmeasured.

## Post-run diagnostic amendment (original observations retained)

The first native NCU launcher omitted GTSPP_MAX_IN_SIZE from the explicit sudo
environment. Its `ncu_rebuild_getNewData` process therefore did NOT rebuild and
reported no matching kernel. Its 69/69 count is not a post-rebuild pass and does
not contradict the 68/69 failures. Re-run only that target as a new `_envfix`
record with GTSPP_MAX_IN_SIZE=2 explicitly passed. Move timeout inside sudo to
ensure the watchdog can terminate its own root profiler; no original run hit
timeout and every original post-run GPU check was clear. Never overwrite the
original missing-profile run.

Original receipts also used the wrong phase parser and, for early memcheck runs,
searched only stderr for sanitizer summaries. Analyze original stdout/stderr to
recover these fields without modifying receipts. Failed oracle exits do not
unwind active scopes, so their phase timings are incomplete, not zero.
