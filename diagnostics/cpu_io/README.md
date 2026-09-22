# CPU / GPU boundary attribution: GTS incremental

## Status and decision

**Source-confirmed CPU work and redundant transfers exist, but the dominant
cause of the reported CPU utilization is not measured yet.** No application or
profiler workload was launched on a GPU: all eight devices were occupied during
the 2026-09-22 preflight, including the only admitted device, GPU 0. Do not
substitute static call counts or old experiments for a CPU profile.

The diagnostic target is `archive/GTS_incremental`, commit
`2c92590ac11c204f8e0c9d2107026d01bc7baced`. Source hashes in
[SOURCE_PINS.json](SOURCE_PINS.json) identify the exact input. The remotely
installed main and all 14 include headers matched this snapshot during the live
inspection. The archived implementation remains unmodified. Preparation writes
only an instrumented copy, and its blocking-wait control is opt-in.

The three user-selected roles remain separate:

| Role | Variant |
|---|---|
| Original rebuild-centric baseline | `backup4080_data/GTS_plus_plus` |
| Legacy unsafe direct-insertion diagnostic target | `archive/GTS_incremental` |
| Current Safe-C1 prototype, not measured here | `safe_arrival/source` |

This investigation does not certify legacy insertion, calibrated pruning, or
query completeness. It does not modify the manuscript or establish novelty.

## Source-confirmed execution map

All locations below refer to the **unmodified pinned source**, not the generated
instrumented copy. These are source facts, not a ranking of measured costs.

| Phase / condition | Actual CPU work | CPU/GPU boundary | Exact source |
|---|---|---|---|
| Every invocation: load | Per-line split into strings; one stringstream and float conversion per numeric coordinate | CPU writes a managed float data allocation, later read by GPU | `include/file.cuh:15-86`, before the index timer in `src/main.cu:130,206-209`; `config.cuh:5` aliases `short` to `float` |
| Initial build and every rebuild | CPU repairs leaf flags, counts leaves, insertion-sorts leaf IDs by `lid`, creates and fills padded ID storage | Full node/empty arrays copied D2H twice; IDs copied D2H; padded IDs and nodes copied H2D | `include/tree.cuh:460-552` |
| kNN initialization only (`process_type=0`) | Allocates full host copies and destroys them | Copies the entire numeric dataset, original-N ID prefix and node array D2H **even without ground truth** | `src/main.cu:235-251` |
| Ground-truth-enabled kNN calibration | CPU recall membership loops, up to O(Qc*k*k) per trial | Repeated GPU searches; synchronized CPU reads of managed result IDs; parameter uploads; repeated workspace allocation | `src/main.cu:261-366` |
| Every successful direct insertion (`process_type=2`) | CPU tree routing and distance evaluation; repeats the selected leaf-pivot distance for L2/L1/Linf | CPU reads managed point/pivot rows; two mandatory tiny H2D copies, an optional third | `include/incremental_insert.cuh:55-212` |
| Deleting a directly inserted ID | CPU scans/compacts leaf IDs, then shifts two insertion-tracking arrays | Whole leaf IDs D2H and H2D, one node H2D | `include/incremental_insert.cuh:215-250` |
| Base-object deletion | CPU binary-searches a logical ID and marks a managed delete bitmap | GPU prefix scan, explicit synchronization, CPU reads managed prefix values; frequent alternation if the prefix is dirty | `include/update.cuh:176-209,544-552,841-860` |
| Static queries | CPU stack/shape bookkeeping, launches and waits; distances and Thrust sort/scan/reduce execute on the GPU | Many device synchronizations; GPU reduction results return to CPU; managed `size_list` crosses the boundary | `include/search_v2.cuh:1070-1266,2054-2294` and the other kNN overloads |
| Queries inside updates | CPU selects query ID and consumes result count | The native entry fixes qnum=1; fast path synchronizes after leaf collection and result compaction | `src/main.cu:529-531`, `include/update.cuh:614-649,893-945` |
| Output | Text formatting, file writes, per-result flushing, optional recall loops | CPU reads managed results; vector `saveK` lies inside the nominal search timing span | `src/main.cu:378-419,421-463,489-503`; `include/file.cuh:331-367` |

### A definite unused full-data round trip

`AutoTuneAndUpload` (`include/residual_tuner.cuh:408-441`) uses only `tree_h`
from its input arguments, initializes small parameter arrays, and uploads them.
It does **not** use `node_list`, `num_nodes`, `data_h`, `id_list_h`, `dim`, `n`,
or `metric_type`. The nearby CPU sample collection/model fitting helpers are
definitions, not calls on this path. Calling them a measured training bottleneck
would be wrong.

For N numeric points of dimension D and V allocated nodes, the unused D2H
payload is **4ND + 4N + V*sizeof(TN)** bytes per program invocation in kNN mode.
Despite the `short*` spelling, `include/config.cuh:5` defines `short` as `float`:
the compiled numeric data is 32-bit floating point, not 16-bit integers.
With the source's five 32-bit TN fields, sizeof(TN)=20 on the inspected build
ABI. At N=1,000,000 and D=128, the point payload alone is 512 MB (488.28 MiB);
at D=960 it is 3.84 GB (3662.11 MiB). These are **derived byte counts**, not
observed transfer durations or page-migration counts. They exclude managed
memory migration. This copy is not inside the printed calibration timer.

The ID copy covers N entries although `id_list` has already been expanded with
padding; it is not a faithful packed logical-ID snapshot. Since the consumer
does not read it, that does not make this particular copy necessary.

### Construction is not GPU-only

The two host snapshots around leaf repair/padding are separate. Before any
optional leaf-flag writeback, their aggregate explicit D2H payload is
`2V*(sizeof(TN)+sizeof(int)) + N*sizeof(int)`. If L leaves exist, padding sends
`(N+64L)*sizeof(int) + V*sizeof(TN)` back H2D. Repair may additionally write the
whole node array H2D. Update initialization then separately reads node, empty,
and max-distance arrays D2H again.

The leaf-ID sort is **insertion sort**, despite comments mentioning qsort.
Its work is O(L + inversions), worst-case O(L^2). If all leaves are already in
`lid` order it is linear. A large CPU-sort contribution must therefore be
measured, not inferred from the worst case. Host padding is paid even for a
static query invocation that never inserts anything.

### Direct insertion combines arithmetic with memory-residency risk

For numeric distances the route is O(D*h) plus child selection; the chosen
leaf-pivot distance is computed again before the optional radius update.
For strings, CPU edit-distance DP is O(length1*length2) per visited level.
After routing, success publishes a 4-byte ID and a 20-byte node, optionally
a 4-byte radius. These are 2-3 **calls**, not a bandwidth-saturating payload.
Many tiny calls can be latency/driver limited even with very few transferred
bytes. Capacity fallback and rebuild have different costs and must be separated.
The original driver loads its point array before processing a trace of update
IDs. These tiny copies describe metadata publication for already addressable
points, **not true-arrival payload delivery**. A future true-arrival experiment
must include payload H2D rather than crediting the legacy replay with zero cost.

`data_d`/`data_s`/`size_s` are managed allocations. CPU routing and GPU queries
touch the same storage; explicit memcpy statistics alone cannot establish the
total traffic. UVM migration/page faults are a **hypothesis pending a trace**,
not a conclusion implied by the pointer type. The post-insertion radius update
does not implement all metrics supported by routing; this is one more reason
not to treat this unsafe archive as a correctness keeper.

### High CPU utilization need not mean useful CPU arithmetic

CUDA's default device scheduling can busy-spin while waiting. Default events
also have a separate wait policy. This archive does not set blocking device
flags and creates ordinary timing events. Its numerous synchronization points
can therefore consume a CPU core without performing indexing arithmetic.
Changing the policy may reduce CPU time without improving wall time; it is an
attribution control, not automatically a system speedup or a research novelty.
[CUDA 13.1 device scheduling](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/group__CUDART__DEVICE.html),
[event synchronization](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/group__CUDART__EVENT.html).

The application host flow is essentially serial: one fully busy core may be
reported as approximately 100% process CPU, not 100% of the whole server. GPU
sorting via `thrust::device` must not be mislabeled as CPU sorting. Conversely,
CPU padding insertion sort is real host work. Driver helper threads and kernel
UVM work need separate accounting from the main thread.

## Existing, narrower supporting evidence

The retained native-policy experiment has a host-read control in
`research/native-fence-policy-20260919`,
`experiments/native_policy/README.md:83-92`. For its adjacent-source-order
**Fence** policy, its recorded mean insertion statistic changes from 868.37 us
in v7 to 36.70 us in v8 when CPU routing reads the already retained host point
array. This is an earlier, different harness/policy, not a fresh measurement of
the unmodified legacy executable. It supports prioritizing residency tests; it
does not provide measured UVM fault counts or this program's CPU percentage.

## Diagnostic contract and runnable preparation

Experiment ID: `gts_20260922_cpu_io_attribution`; state: **built / unvalidated
runtime**, no measured performance claim. Preserve the original binary, source,
inputs and all failed runs. Do not change original algorithms, gamma, k, radius,
input order, tree parameters or update visibility to obtain a faster profile.

Before any GPU run, fill the execution card with an idle admitted device UUID,
host, exact command, input hashes, N/D/metric, query/update counts and order,
ground-truth mode, driver/toolkit, CPU affinity, binary hashes, stop rule and log
directory. Record process CPU seconds, wall seconds, kernel intervals, explicit
H2D/D2H counts/bytes, and UVM faults/migrations **separately**. Initial loading,
construction, calibration, steady queries, insertions, deletions, rebuilds and
output are different denominators. This run has no model/checkpoint component.

Preparation (repository root; output must not exist):

```sh
python3 diagnostics/cpu_io/test_prepare.py
python3 diagnostics/cpu_io/prepare.py diagnostics/cpu_io/work/profiled
```

The timer has a separate host-only check; it neither links CUDA nor creates a
GPU context (the CUDA header path is needed only for unused inline declarations):

```sh
g++ -std=c++17 -O2 -I"${CUDA_HOME:-/usr/local/cuda-13.1}/include" \
  diagnostics/cpu_io/test_profile.cpp -pthread -o /tmp/gts_test_profile
/tmp/gts_test_profile
```

Build on the target GPU host without executing a workload. Use the actual
toolkit path, not a relocated nvcc symlink. Set NVTX_INCLUDE to the installed
directory containing `nvtx3/nvToolsExt.h`:

```sh
CUDA_HOME=${CUDA_HOME:-/usr/local/cuda-13.1}
: "${NVTX_INCLUDE:?Set the installed NVTX header directory}"
mkdir -p diagnostics/cpu_io/work/bin
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info \
  -Iinclude src/main.cu -o diagnostics/cpu_io/work/bin/gts_baseline
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info \
  -DGTS_DIAG_NVTX -I"$NVTX_INCLUDE" \
  -Idiagnostics/cpu_io/work/profiled/include \
  diagnostics/cpu_io/work/profiled/src/main.cu -ldl \
  -o diagnostics/cpu_io/work/bin/gts_profiled
```

`profile.hpp` adds main-thread CPU time and wall time for named phases, plus
optional NVTX ranges. It inserts **no GPU synchronization**. Values are
inclusive/nested and must not be summed as disjoint phases; an asynchronous
function can return before its device work completes. CPU time includes
runtime spin-wait and excludes other threads. No value alone is a measure of
useful arithmetic. Instrumentation perturbs short paths: use the uninstrumented
baseline for clean timing. `GTS_DIAG_BLOCKING=1` changes both device scheduling
and timing-event waits in the generated copy; unset preserves default behavior.
All four kNN overloads carry the same range label; preserve argv to identify
which overload the original entry chooses.

After explicit device admission, preserve separate directories for every run:
the legacy binary overwrites `result_ids.txt`, `result_dists.txt` and its cost
file. Use the exact captured original command. The argument contracts are:

```text
gts_profiled DATA QUERY 0 K COST [id|vec] [GROUND_TRUTH]
gts_profiled DATA QUERY_IDS 1 RADIUS COST
gts_profiled DATA UPDATE_TRACE 2 RADIUS COST
```

The current preflight reports `perf_event_open` unavailable (paranoid level 4),
so native CPU instruction sampling is **not available** under the admitted
account. Do not change shared host security settings. A permissions-preserving
first trace uses installed Nsight Systems 2025.5.2 with
`--trace=cuda,nvtx,osrt --sample=none --cpuctxsw=none`. Run a **separate**
diagnostic with `--cuda-um-cpu-page-faults=true
--cuda-um-gpu-page-faults=true`; these options add substantial overhead and may
have platform restrictions. Record failure rather than silently dropping them.
The phase CPU clocks are the fallback, not equivalent to a sampled call stack.
[Nsight Systems user guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html).

The minimal order after admission is:

1. Verify baseline and instrumented results on the same bounded fixture;
   independently check correct output/visibility before any optimization claim.
   A compile pass or baseline parity alone does not establish algorithm correctness.
2. Capture one bounded default-wait trace and CPU phase table. Abort on CUDA
   errors, invalid output, unexpected memory growth, foreign device activity, or
   the predeclared 120-second workload limit; stop only the owned process tree.
3. Run default/blocking then blocking/default in fresh processes with fixed
   workload and compare both CPU and wall time. Retain all four observations.
4. Only if routing/residency is implicated, design a host-mirror versus managed
   read control with identical payload arrival and explicit host-memory costs.
5. Remove the unused kNN host copies as a separate correctness-checked candidate;
   preserve implicit ordering if necessary with an explicit dependency, never
   simply delete all synchronization points. Device-side padding/batched update
   publication are later candidates only if the measured denominator supports them.

## Research boundary

Working question: which repeated CPU/GPU boundary crossings are required for
correct dynamic metric search, and which are artifacts of placement, control
flow, or stale initialization? Removing dead copies, changing wait flags,
prefetching managed memory, batching copies, and replacing insertion sort are
established engineering techniques. None alone establishes a new paper thesis.
Before substantial experiments or rewriting the paper, compare any proposed
structural mechanism with the nearest dynamic-index and GPU-resident control
designs, then test same-contract end-to-end cost with an independent correctness
oracle. High CPU utilization is a symptom, not a novelty claim.

## Release boundary

Live repository metadata reported **public** visibility although the inherited
archive README says private and records no upstream license. No visibility
change or publication is implied. Until disclosure/rights are confirmed, retain
the task-owned local checkpoint and remote scratch only; do not publish raw
machine/process metadata, manuscript material, dataset contents, or generated
instrumented source. A local compile/diagnostic bundle is not an uploaded release.
