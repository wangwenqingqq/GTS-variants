# Original GTS / GPU-Tree: measured CPU and I/O attribution

Date: 2026-09-22. **Diagnostic campaign completed; no optimized implementation
or paper-facing speedup is promoted.** Source originals were not edited.

## Conclusion

**High CPU consumption is real, but much of it is CUDA waiting rather than CPU
distance computation.** On the 65,536-object Words subset, changing only device
waiting policy reduced main-thread CPU time by 71-81% across the three GTS paths.
It did not improve elapsed latency: range slowed about 4%, kNN was inconclusive,
and query-only operations through the update entry slowed about 16%.

The strongest remaining GPU bottleneck is result counting for range and update
queries. Measured host/device copy payloads are small; they do not support a
bulk PCIe-bandwidth bottleneck in these workloads. Unified-memory fault handling
and fine-grained CPU/GPU control remain real costs, not ruled out by small bytes.

GPU-Tree's per-node allocations are also confirmed: **2,000 input objects caused
2,000 individual `cudaMalloc` calls in the node-allocation loop**. However, its
cleanup and kNN queue have sanitizer failures, so its whole-implementation
performance is not admitted as a clean comparator.

## 1. Contract and provenance

The predeclared hypotheses and scope are in [CONTRACT.md](CONTRACT.md); machine-
readable paired samples, gates, binary hashes, and evidence hashes are in
[EVIDENCE.json](EVIDENCE.json).

- Author source commit: `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. All 18
  original CUDA source files were matched against the user-designated remote
  source before preparation. Original source pins remain in the adjacent audit.
- Hardware: RTX PRO 6000 Blackwell Server Edition, admitted physical GPU 0,
  driver 590.48.01, CUDA 13.1.115, GCC 13.3.0, Nsight Systems 2025.5.2.
  No GPU settings or foreign processes were changed. Process checks before and
  after each run and a nonblocking advisory lock admitted the GPU. This was not
  an otherwise-exclusive CPU host; observed GPU clocks and process state are
  retained, not forced.
- Real data: deterministic evenly spaced raw-byte Words subsets of N=1,000,
  2,000 and 65,536, from the 611,756-object dataset. Q=32, inclusive radius 4,
  k=4, deterministic query IDs. Independent CPU full-table edit-distance oracle.
- The update-entry workload is **32 queries with no insertion or deletion**.
  It isolates recurring update-query allocation/scheduling and unchanged-bitmap
  work; it does not establish insertion/deletion throughput or correctness.
- GTS workspace is capped at 256 MiB to avoid the original 32-bit conversion of
  half a 96-GiB device's free memory. N<=2,000 uses native MAX_H=3. The scale
  extension changes MAX_H to 5 so leaves remain within the native 20-slot limit.
  These are explicitly resource/height-adapted originals, not untouched default
  executables at arbitrary N. No pruning, distance, aggregation or tree-layout
  algorithm was optimized; the original result-count reductions remain.
- GPU-Tree seed is fixed to 0 and unused local pointers are initialized to null
  for reproducibility/cleanup safety. The sanitizer failures below remain even
  after those limited preparation changes.
- Native output contracts are range **counts** and kNN **kth distances**, not
  complete ID sets. All quoted correctness follows that scope.
- Context initialization is explicitly ranged before loading in both wait-policy
  arms. Cold process startup, loading, construction, query, and result export
  are separate. The query numbers below exclude all but the declared query phase.

## 2. Clean causal control: default vs blocking CUDA waits

Same instrumented binary, same input/results, six fresh-process pairs at each
size and path, alternating AB/BA order. No profiler in these observations.
Timers use monotonic wall time and **main-thread** CPU time. They are not total
machine CPU utilization or a direct measure of useful arithmetic. These are
one-shot native lifecycle queries after a fresh build, not warm service timing.

### N=65,536: primary scale extension

Times are marginal medians in milliseconds. Ratios/intervals are genuinely
paired geometric ratios (blocking/default), not ratios of those medians.

| Path / timed denominator | Default wall | Blocking wall | Default CPU | Blocking CPU | Paired CPU ratio [95% CI] | Paired wall ratio [95% CI] |
|---|---:|---:|---:|---:|---|---|
| One range batch, Q32 | 32.044 | 33.237 | 31.338 | 8.914 | 0.293 [0.271, 0.316] | 1.041 [1.025, 1.057] |
| One kNN batch, Q32 | 16.226 | 16.643 | 9.574 | 2.634 | 0.263 [0.241, 0.287] | 0.999 [0.952, 1.048] |
| Update entry, 32 query-only operations | 165.972 | 193.571 | 157.112 | 29.694 | 0.188 [0.176, 0.201] | 1.158 [1.110, 1.208] |

CPU time decreased in **all six pairs for every path**. Range and update wall
latency increased in all six pairs. kNN wall time had three pairs in each
direction. Intervals use Student-t on six paired log ratios, not individual
kernels as independent samples. This is a CPU-resource tradeoff, not a speedup.

### N=2,000: same-direction bounded evidence

| Path | Paired CPU ratio [95% CI] | Paired wall ratio [95% CI] |
|---|---|---|
| Range Q32 | 0.446 [0.381, 0.521] | 1.036 [0.741, 1.450] |
| kNN Q32 | 0.520 [0.492, 0.549] | 0.989 [0.759, 1.289] |
| 32 update-entry queries | 0.612 [0.562, 0.666] | 1.321 [1.222, 1.428] |

The independent scoped context-initialization cost also explains why whole-
process CPU percentages are especially misleading for tiny one-shot runs.
Do not combine startup CPU with steady-query arithmetic.

## 3. What the GPU timeline actually shows

These are **separate, UVM-enabled diagnostic traces**, one per path/size. They
are not the clean latency observations above. CUDA API waits overlap GPU kernels
and must not be added to them. Nested NVTX ranges overlap; unaccounted timeline
gaps are not labeled pure CPU work.

### N=65,536

| Query scope | Traced wall (ms) | Main GPU work observed | Explicit D2H payload | Recorded UVM payload, both directions |
|---|---:|---|---:|---:|
| Range Q32 | 31.515 | `mergeResRnn`: 19.822 ms, **62.9%** of traced wall | 24 B / 6 transfers | 84 KiB / 21 transfers |
| kNN Q32 | 15.786 | Leaf distance 2.292 ms; radix-sort onesweep kernels 1.080 ms; no single result counter dominates | 40 B / 10 transfers | 124 KiB / 31 transfers |
| 32 update-entry queries | 177.999 | `getQresultCount`: 105.935 ms (**59.5%**); `getQnodeCount`: another 8.986 ms | 256 B / 64 transfers | 1,704 KiB / 156 transfers |

The source calls Thrust reduction from inside the result-count kernels. The
prior campaign established the installed toolchain's sequential per-caller
fallback. This new campaign directly remeasures their time, not a new SASS
instruction-level attribution. It does not establish how the 2024 paper's
historical binary executed.

Actual copy-engine durations, including recorded UVM transfers, were 0.022,
0.031 and 0.187 ms respectively. This supports rejecting a **bulk copy bandwidth**
explanation here, not rejecting page-fault latency. The traces report CPU UVM
fault events of 10 / 15 / 65, and GPU fault counts of 2,843 / 2,546 / 6,194.
These are profiler event/count semantics, not counts of unique migrated pages.
Fault handling can appear in kernel stalls or unattributed gaps and is not
bounded by the copy-engine duration alone.

The range path additionally zeros its entire **256 MiB device workspace** in
this contract (about 0.232 ms in the trace). That is real capacity-based traffic,
but GPU memory initialization, not 256 MiB sent over PCIe.

### Repeated allocation and control are measurable

For the 32-query update-entry trace at N=65,536:

- **514 `cudaMalloc` + 264 `cudaMallocManaged` = 778 allocation calls**;
- 777 `cudaFree`, 960 kernel-launch calls, and 512 device synchronizations;
- allocation/free API intervals total about **13.642 ms** inside the 177.999 ms
  traced scope. This is runtime API wall time, not additional CPU arithmetic or
  a standalone speedup bound. It must not be summed with overlapping GPU time.

For GPU-Tree at N=2,000, the node-allocation range contains exactly 2,000
`cudaMalloc` calls. In its range trace these occupy 8.376 ms of that diagnostic
range's 8.769 ms. This is a measured pre-error allocation-loop fact, not an
admitted whole-index performance comparison. Its range-query trace also records
228 device allocations and 228 frees; its sanitizer-failing kNN trace records
601 device allocations, 605 frees and 64 single-tile sort kernels. The latter
is **unvalidated diagnostic work inventory**, not a valid query throughput result.

## 4. Correctness, failed gates, and limits

There are 109 preserved GPU process receipts: 61 bounded-stage and 48 scale-
extension runs. The 99 GTS runs all returned successfully and matched the native
count/kth oracle. Every retained default/blocking observation was checked.

- GTS range, kNN and query-only update passed both memcheck and synccheck at
  N=1,000 and the full N=65,536 extension. No full-ID, insertion, mixed-metric,
  long-running service or concurrent-update certification is implied.
- GPU-Tree normal smoke outputs matched the oracle at N=1,000/2,000. This does
  **not** override its memory-safety failures.
- GPU-Tree range memcheck reports **four invalid `cudaFree` calls in main's
  cleanup**. The run still returned matching range counts. The failure is
  preserved; its clean paired campaign was skipped.
- GPU-Tree kNN memcheck first reports an out-of-bounds global write in
  `initPQ`, `priority_queue.cuh:49`, called by `getKnnBound` at `search.cuh:602`.
  It then reports launch failure; no valid result was produced under memcheck.
  Its paired campaign was also skipped. Synccheck passes do not waive either
  failure. Fix and independently revalidate before comparison.
- No kernel optimization, blocking-policy production change, speedup keeper or
  universal GPU-tree conclusion is promoted. CPU sampling was unavailable under
  existing perf permissions; no host security setting was changed.

## 5. Claim-evidence / decision ledger

| Claim | State / scope | Evidence and counterevidence | Allowed decision |
|---|---|---|---|
| Changing waiting policy lowers GTS host CPU | **measured**, two sizes, three query paths, native output parity | 72 clean observations; all paired CPU ratios below 1. Wall latency not improved | Much observed CPU use is wait-policy-sensitive; do not equate it with CPU distance arithmetic |
| Large payload CPU/GPU copy bandwidth dominates these GTS queries | **rejected for tested scope** | Low copy payloads/durations versus large counter-kernel times; UVM faults still present | Do not make bulk PCIe transfer the paper thesis from CPU utilization alone; reopen for out-of-core/true-arrival or directly measured fault-service dominance |
| GPU-Tree performs per-point host allocations | **measured prefix / partial system evidence** | 2,000 calls for N=2,000; downstream sanitizer failures | Allocation amplification exists; no whole-index performance promotion until baseline repair |
| Result aggregation is the main range/update GPU issue here | **measured** for these Words traces, not kNN or all metrics | 62.9% range / 59.5% update result-counter fractions; old campaign provides execution-path context | Repair/parallelize the baseline's counters while preserving outputs, then remeasure residual allocation/control/UVM costs |
| Workspace reuse / GPU-resident traversal alone is new research | **not established** | Existing C1 and the prior-art audit already cover generic techniques | No new thesis without a distinct same-contract mechanism and repaired external comparators |

Next experiment: a separate, output-equivalent parallel-counter baseline, then
one-mechanism allocation/control/UVM ablations. Preserve default and blocking
negative latency evidence. Do not remove result work to manufacture a win.

## 6. Reproduction and retained artifacts

Use a new scratch directory; runners deliberately refuse to overwrite run
folders. GPU admission is external to the scripts and must follow the current
host's user/process rules. Never treat `--gpu` as authorization to use any device.

```sh
python3 diagnostics/original_tree_profile/test_prepare.py "$AUTHOR_SOURCE_ROOT"
python3 diagnostics/original_tree_profile/prepare.py "$AUTHOR_SOURCE_ROOT" "$SCRATCH/profiled_v2"
python3 diagnostics/original_tree_profile/make_fixture.py "$WORDS" "$SCRATCH/fixtures"
# Build each copied main with its matching include directory:
mkdir -p "$SCRATCH/bin"
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -DGTS_DIAG_NVTX \
  -I"$SCRATCH/profiled_v2/GTS/include" "$SCRATCH/profiled_v2/GTS/src/main.cu" \
  -ldl -o "$SCRATCH/bin/gts_profiled_v2"
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -DGTS_DIAG_NVTX \
  -I"$SCRATCH/profiled_v2/GPU-Tree/include" "$SCRATCH/profiled_v2/GPU-Tree/src/main.cu" \
  -ldl -o "$SCRATCH/bin/gputree_profiled_v2"
python3 diagnostics/original_tree_profile/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage smoke
python3 diagnostics/original_tree_profile/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage sanitizer
python3 diagnostics/original_tree_profile/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage paired
python3 diagnostics/original_tree_profile/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage profile
python3 diagnostics/original_tree_profile/analyze.py "$SCRATCH"
```

The scale extension uses a separate, new `$LARGE` scratch root and the same
launcher, repeating full-size gates. The copied GTS-only tree is named `source/`,
matching the runner's source-hash inventory. After the preparation above:

```sh
mkdir -p "$LARGE/bin"
cp -R "$SCRATCH/profiled_v2/GTS" "$LARGE/source"
python3 - "$LARGE/source/include/tree.cuh" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1]); text = p.read_text()
assert text.count('__managed__ int MAX_H = 3;') == 1
p.write_text(text.replace('__managed__ int MAX_H = 3;', '__managed__ int MAX_H = 5;'))
PY
python3 diagnostics/original_tree_profile/make_fixture.py "$WORDS" "$LARGE/fixtures" --sizes 65536
"$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -DGTS_DIAG_NVTX \
  -I"$LARGE/source/include" "$LARGE/source/src/main.cu" -ldl -o "$LARGE/bin/gts_profiled_v2"
python3 diagnostics/original_tree_profile/run_large.py "$LARGE" --gpu "$ADMITTED_UUID"
python3 diagnostics/original_tree_profile/analyze.py "$LARGE"
```

`test_run_large.py` checks fresh output directories and source-hash coverage
with mocked launches, without contacting a GPU. Its directory-preparation fix
and the complete build instructions were added during the publication audit;
measured binaries and `EVIDENCE.json` are unchanged. Raw receipts contain exact commands,
input results, source/binary hashes, per-run GPU snapshots and full failure logs.
Copies of all NSYS reports/SQLite exports and receipts are retained under
ignored `local/small` and `local/large`; their SHA-256 inventory is checked in.
Explicit user authorization on 2026-09-22 resolved the initial disclosure hold
for task-owned diagnostic tools, reports, numerical summaries and evidence hashes.
Publication does not include raw logs, datasets, binaries, machine configuration
or generated original-source copies; it does not alter visibility or merge the
experimental branch. Upload completion must be verified against the remote SHA.
