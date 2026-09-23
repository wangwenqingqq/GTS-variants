# Exact-L2 GTS full-query versus dense Tensor Core control

**Decision: do not promote this tree-TC integration.** Across four measured
shapes, replacing the integrated SIMT leaf kernel with TC did not establish a
stable full-query improvement, and a no-tree control was consistently faster.
This rejects the current implementation under the frozen warm-count contract,
not Tensor Cores, every tree, or the historical GTS paper's results.

## Results

Wall-time marginal medians, milliseconds per CPU-delivered query batch:

| Queries | Radius | O: original | S: tree + SIMT | T: tree + TC | D: dense TC |
|---:|---:|---:|---:|---:|---:|
| 32 | 300 | 152.071 | 175.939 | 175.889 | 0.155 |
| 32 | 500 | 181.242 | 175.979 | 175.959 | 0.155 |
| 128 | 300 | 557.760 | 191.965 | 191.949 | 0.398 |
| 128 | 500 | 643.453 | 191.938 | 191.783 | 0.395 |

N=65,536, D=128 integer SIFT coordinates; six processes per shape. These are
**implementation-specific warm-query latencies**, not cold-start throughput or
an intrinsic algorithmic advantage. In particular, S/T retain native query
workspaces and managed outputs while D has reusable device output buffers.

The predeclared estimator is the geometric mean of six process-median ratios,
not the ratio of the marginal medians above. Ratios >1 favor the denominator:

| Q/r | S/T paired ratio [95% CI] | T wins | T/D paired ratio [95% CI] | D wins |
|---|---|---:|---|---:|
| 32/300 | 1.006 [1.000, 1.013] | 4/6 | 1123.6 [1100.9, 1143.1] | 6/6 |
| 32/500 | 1.000 [1.000, 1.000] | 5/6 | 1126.2 [1106.9, 1145.2] | 6/6 |
| 128/300 | 1.350 [0.9998, 2.459] | 3/6 | 361.1 [194.4, 502.0] | 6/6 |
| 128/500 | 1.282 [0.9999, 2.101] | 5/6 | 297.9 [178.1, 496.1] | 6/6 |

Q128 is **bimodal and order/process-dependent**, not a reproducible 28-35% TC
benefit. For Q128/r300, five process-median T latencies are about 192 ms and one
is 31.734 ms. S-first versus T-first paired ratios are 1.000 versus 1.822. For
Q128/r500, T process medians are 192.080, 191.943, 191.956, 40.158, 191.919 and
43.655 ms; S-first versus T-first ratios are 1.000 versus 1.645. All observations
are retained, including favorable outliers. Rounded intervals at 1.000 do not
imply exact equality; full precision, p10/p90, every process, secondary CPU/event
times and all 40 comparison estimates are in [EVIDENCE.json](EVIDENCE.json).

All four tree-TC continuation gates failed. All four dense-control gates passed,
including the repeated-query check: T/D paired ratios for groups of sixteen
separately timed calls were 1176.5, 1179.6, 398.1 and 365.7 in table order.
Do not reinterpret those groups as uninterrupted throughput.

Replacing the native leaf distance/count path has a separate, mixed result:
S regresses on Q32/r300 (O/S paired ratio 0.870, CI [0.857, 0.878], 0/6 wins)
and improves on Q128/r300 (2.868, CI [2.826, 2.910], 6/6 wins). Q128/r500 also
favors S but has a fast-process outlier: O/S paired 4.414 versus marginal 3.352;
its repeated-query paired ratio is 3.433. This is not clean TC attribution or
an isolated test of counting alone.

[samples.csv](samples.csv) preserves all 2,400 numeric observations in process
and variant order. No timed kernel was tuned or replaced after observing these
results. The measured binary and source-generation hashes are retained.

## What is being compared

| Mode | Query path |
|---|---|
| O | Resource-adapted original GTS traversal, native leaf distances and nested result counting |
| S | Same live GTS traversal and candidate formation, parent coalesced SIMT leaf distance/count kernel |
| T | Same live GTS traversal and candidate formation, parent WMMA leaf distance/count kernel |
| D | No tree traversal: the same WMMA kernel scans flat 16-point tiles with all-active masks |

**The denominator is warm query dispatch to exact counts available in a CPU
vector, with vectors and query IDs already resident.** It includes native query
allocations/frees, level traversal, scans, live candidate formation, conversion
to the bridge layout, masks, FP16 packing, padded arithmetic, count recovery,
synchronization and CPU result delivery. This is not resident candidate replay,
not kernel-only timing, and not end-to-end ingestion or fresh-program runtime.
It measures exact range counts, not materialized result IDs, kNN, dynamic updates
or newly uploaded external query vectors.

The tree variants intentionally retain native allocation, synchronization and
Unified Memory behavior. The bridge is one minimal implementation, not an
optimized GTS replacement. In particular, `tc_refine` reads the managed size
metadata on the host to obtain the native list stride. The cost of that added
boundary was not independently isolated. D uses reusable fixed flat-tiling and
count buffers rather than the original 256 MiB per-query workspace. These
implementation/control costs are in scope, not evidence against every tree.

D is a cheap **same-kernel dense control**, not cuBLAS, Faiss, an optimized dense
scan, or a comparison with all GPU indexes. It computes more useful distances
but has fully occupied distance tiles and no traversal/mask construction. The
same driver builds a GTS index for O/S/T; D's timed calls do not access it, but
its standalone cold startup was not measured. Do not add independent phase
medians to fabricate a cold-start speedup.
Recorded setup phases are input parsing, norms plus integer checks, oracle,
index construction, and combined bridge preparation. Context initialization is
excluded but was not separately timed; bridge setup is not a dense-only setup
measurement.

## Frozen contract and validation

See [CONTRACT.md](CONTRACT.md). Base repository: `642a37f`. Original author
source: `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`; 18 pinned CUDA files verified.
Previous campaigns and original sources are untouched.

- Same SIFT fixtures as the parent experiment: first 65,536 rows, 128D integer
  values in [0,255], query IDs floor(i*N/Q), Q=32/128, radii=300/500. Smoke:
  N=2,000/Q=32/r=300. Every result includes self and is exact, not approximate.
- Resource adaptations: MAX_H=5 for 65,536 rows, native MAX_H=3 for smoke;
  MAX_SIZE=20 and the parent's 256 MiB workspace. Query diagnostics are muted
  identically in O/S/T. The result buffer is freed by the wrapper after every
  CPU delivery to prevent a leak in repeated native calls.
- PRO 6000 Blackwell Server Edition, physical GPU0 only, CUDA13.1.115,
  driver590.48.01, GCC13.3.0. Advisory lock and pre/post process checks; no GPU
  clocks/power or foreign processes changed. The host is shared, not exclusive.
- **All modes use blocking CUDA waiting.** Main-thread CPU times therefore do
  not measure the default native application's busy-wait CPU consumption.
- Six fresh processes per shape, orders OSTD, TDOS, SODT, DTSO, DSOT, TOSD.
  Every pair appears in each relative order 3 times. Five warmups/path, twenty
  individual queries/path, then five groups of sixteen repeated queries/path.
- The group-of-16 statistic is the mean of sixteen individually timed,
  CPU-delivered and validated calls, with event/validation gaps between them.
  It tests repeated-query behavior; it is **not an uninterrupted batch
  throughput window**. No CUDA Graph, concurrent-stream or production claim.
- Every measured count vector is checked against independent full-table integer
  L2 outside the timed scope. FP16 integer coordinates and FP32 accumulation
  obey the parent's <2^24 exactness bound; no precision correction is required
  for this contract. No claim covers arbitrary floating-point inputs or other
  metrics. The reused kernels were not changed after timing began.

All five workload shapes passed O/S/T/D count checks, memcheck and synccheck;
the smoke case also passed initcheck and racecheck. Repeated calls passed before
and after timing. Static TC code generation is a separate gate from these
runtime checks. The previous full candidate-distance diagnostic remains in
[the parent experiment](../tc_leaf_probe/README.md); this full-query driver
validates counts on every call, not a newly exported full distance matrix.

## Mechanism limits

The parent workload has weak pruning: about 84% of all point pairs remain at
radius 300 and 99% at radius 500. Its TC leaf tiles use only 34-41% of distance
cells; flat dense tiles use all cells. This explains why a dense counterexample
is plausible, but it is not a measured attribution of the full latency gap.

The newly linked compiler report shows 47,528-byte stack frames in the native
`nodeProcessRnn` and `dataProcessRnn`, inherited from generic metric code that
contains an edit-distance table. The TC body has 40 registers, 9,216 B shared,
no stack/spills and 16 static HMMA instructions; SIMT has 36 registers, 32 B
shared in this relocatable-device-code build and no stack/spills. The frame
size alone does not prove executed local traffic, allocated backing, or causal
latency. Compiler spill counts of zero do not mean zero explicit local arrays.

Any Nsight result is diagnostic, not the public wall-time denominator. The
trace also includes setup/index build and validation calls. Kernel/call/UM
summaries must retain that scope. A gap outside a kernel is not automatically
CPU arithmetic, PCIe saturation, or removable synchronization.

### What the trace does and does not establish

The optional Q128/r500 trace contains five query calls per variant plus setup.
The native `dataProcessRnn` alone takes 584.49 ms on average (five calls), while
`mergeResRnn` takes 21.27 ms on average. Across the whole trace,
`cudaDeviceSynchronize` accounts for 4.724 s, or 98.4% of captured CUDA API time;
all `cudaMalloc`/`cudaMallocManaged`/`cudaFree` calls together take only 20.32 ms.
API waits overlap GPU work and must not be added to kernel durations.

With the explicitly selected **blocking** wait policy, marginal main-thread CPU
time is only 2.08-2.65 ms for O/S/T despite 152-643 ms wall time. This localizes
the measured delay primarily to GPU execution/waiting, not hundreds of
milliseconds of measured main-thread CPU arithmetic. Other CPU threads and the
original application's default spin-wait behavior were not characterized.

Unified Memory activity exists: whole-trace totals are 35.500 MB HtoD, 1.819 MB
DtoH, 332 CPU page faults and 56,791 GPU page faults. These include input/setup
and every variant; they do not by themselves establish saturation or causality.
The offline [per-launch overlap](PROFILE_OVERLAP.json) distinguishes T's
10,000-by-8 grid from D's 4,096-by-8 grid:

- T leaf calls span 1.021-157.008 ms; D calls span 0.365-0.372 ms.
- S leaf calls span 1.360-156.326 ms. This instability is not exclusive to TC.
- Slow S/T leaf calls overlap only 1.740-2.205 ms of recorded GPU-fault event
  intervals, with 49-103 faults in the overlapping events. Some much faster
  calls have more faults. Fault counts are therefore not a monotonic latency
  explanation, and interval overlap is not causal stall time.
- Native O leaf calls remain about 584 ms with zero to three overlapping faults.

These observations rule out blaming only host allocation-call duration. They
do **not** isolate whether managed output placement, migration/coherence,
atomic contention, native generic-metric resources or another effect causes
the slow GPU execution. Kernel-duration variation remains an unresolved
implementation issue, not a result to smooth away.

## Claim ledger and next falsifiable test

Experiment ID: `gts_20260923_tc_e2e_exact_counts`. Last collection: 2026-09-23,
PRO 6000 GPU0. All claims below use the frozen contract and the oracle/sanitizer
gates above; source, binary, fixture, process and raw-file provenance are in
`EVIDENCE.json`.

| Claim | State | Strongest allowed wording / counterevidence |
|---|---|---|
| Exact full-query counts | measured | All five shapes and every timed call matched the integer full-table oracle; no materialized-ID or arbitrary-FP32 claim. |
| Stable TC benefit over integrated SIMT | inconclusive | Q32 gain is negligible; Q128 is bimodal/order-dependent and confidence includes no gain. No stable TC speedup established. |
| Promote this tree-TC implementation | rejected | All four predeclared continuation gates fail; D wins all four shapes. |
| Dense control beats current tree paths | measured | Same resident integer-count contract only; neither best dense library nor all tree implementations tested. |
| Slow calls imply heavy CPU arithmetic | rejected | Under blocking waits, measured main-thread CPU time is much smaller than wall time; default-spin CPU usage remains unknown. |
| Unified Memory causes the entire gap | unknown | Fault activity and unstable managed-output kernels observed; no residency/allocation ablation, and fault count does not track latency. |
| Large native stack frames cause the gap | unknown | Static resource fact only; no L2-specialized same-contract control yet. |
| Generic indexed TC distance is novel | rejected | TED-JOIN already establishes the core mapping; this is a diagnostic experiment, not a new thesis. |

Next test: hold live candidates, launch geometry, arithmetic, output semantics,
timer and comparator fixed; change **only S/T count-buffer allocation/residency**
from native managed output to an explicitly device-resident buffer, retaining
zeroing and CPU delivery inside timing. Recheck exact counts and balanced
fresh-process distributions. If bimodality survives, reject this explanation;
if it disappears, separately test residency versus atomic behavior. A separate
native L2-specialization control is needed before blaming its generic stack.
Neither control was executed in this campaign. Reopen tree-TC performance only
after a stable same-contract implementation also competes with the dense control;
larger N or stronger pruning needs a new frozen campaign, not extrapolation.

## Reproduce

Python standard library, CUDA13.1 and compute-sanitizer are required. Nsight
Systems2025.5.2 is optional. No new dependencies are installed. Run from a clean
checkout. Set `AUTHOR_SOURCE_ROOT` to the directory containing `GTS/` and
`GPU-Tree/`, `SIFT_BASE_TEXT` to the original SIFT text, `CUDA_HOME` to the real
toolkit root, `SCRATCH` to new task-owned scratch, and `ADMITTED_UUID` to the
explicitly admitted physical GPU0 UUID. A script argument is not GPU permission.

```sh
python3 diagnostics/tc_e2e/test_prepare.py "$AUTHOR_SOURCE_ROOT"
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n2000" --n 2000
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n65536" --n 65536
for h in 3 5; do
  python3 diagnostics/tc_e2e/prepare.py "$AUTHOR_SOURCE_ROOT" "$SCRATCH/source$h" --height "$h"
  "$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
    -Xptxas=-v -Xnvlink=--ignore-host-info -I"$SCRATCH/source$h/GTS/include" \
    "$SCRATCH/source$h/GTS/src/main.cu" -ldl -o "$SCRATCH/bin/bench$h" \
    >"$SCRATCH/logs/build$h.log" 2>&1
done
"$CUDA_HOME/bin/cuobjdump" --dump-sass "$SCRATCH/bin/bench5" >"$SCRATCH/logs/bench5.sass"
for stage in check sanitizer timing; do
  python3 diagnostics/tc_e2e/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage "$stage"
done
# Optional diagnostic, after the timed campaign:
python3 diagnostics/tc_e2e/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage profile
nsys stats --report cuda_gpu_kern_sum,cuda_api_sum,cuda_gpu_mem_time_sum,cuda_gpu_mem_size_sum,um_total_sum,um_cpu_page_faults_sum \
  --format csv --output . "$SCRATCH/runs/profile_n65536_q128_r500/trace.nsys-rep"
python3 diagnostics/tc_e2e/profile_overlap.py "$SCRATCH/runs/profile_n65536_q128_r500/trace.sqlite" \
  > "$SCRATCH/PROFILE_OVERLAP.json"
mkdir -p "$SCRATCH/diagnostics/tc_e2e"
for name in prepare.py bridge.cuh driver.cu run.py analyze.py test_prepare.py CONTRACT.md README.md; do
  cp "diagnostics/tc_e2e/$name" "$SCRATCH/diagnostics/tc_e2e/$name"
done
python3 diagnostics/tc_e2e/analyze.py "$SCRATCH" "$SCRATCH/curated"
```

The fixture manifest must match the parent campaign, not just the shape. Runs
refuse overwrite and stop on failed correctness, sanitizer return code or a
foreign GPU0 process. The full campaign is longer than the parent component
probe because every repetition includes the native query framework.

Only authored glue/analysis, curated numeric observations and evidence manifests
are published. Do not publish generated upstream copies, SIFT data, binaries,
raw profiler reports, host configuration or private receipts. Relative raw
paths in the manifest resolve against the task-owned scratch retained locally.
`source_sha256` is the collection-time snapshot, not the final delivery hash.
`delivery_source_sha256` records final authored files and curated observations;
the contract's original bytes remain an unchanged prefix before its appended
outcome. Final prose, the offline overlap analyzer, and address redaction in
profile curation were added after collection; the measured driver, bridge,
preparation, and leaf kernels are unchanged.

Nearest prior art remains [TED-JOIN, HiPC2022](https://jan.ucc.nau.edu/mg2745/publications/Gallet_Gowanlock_HiPC2022.pdf): indexed shared-candidate Tensor Core Euclidean
distance is already established. This campaign diagnoses one implementation
and checks whether its tree remains useful; it introduces no new research
mechanism and does not compare its timings with TED-JOIN.
