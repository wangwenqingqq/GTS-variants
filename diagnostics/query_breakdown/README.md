# Original GTS: which part of the query costs time?

**Measured: leaf distance processing dominates this SIFT L2 range workload;
high host CPU consumption is overwhelmingly wait-policy-sensitive.** These are
two different observations. A long distance kernel is not yet a demonstrated
arithmetic-throughput bottleneck, and this is not a TC speedup experiment.

## 1. Clean measurements: where the query time goes

PRO 6000 Blackwell Server Edition, physical GPU0, CUDA13.1.115, driver590.48.01,
GCC13.3.0. Six matched fresh-process pairs per shape, 48 processes in total,
384 retained queries and 3,072 stage observations. Every count vector matched
the full-table integer oracle. All required sanitizer checks passed. The host
was shared and clocks were observed, not locked; all samples/outliers remain.

Default-wait marginal wall medians and medians of per-query stage fractions:

| Q / radius | Full query ms | Leaf distances | Internal distance/pruning | Result aggregation |
|---|---:|---:|---:|---:|
| 32 / 300 | 151.638 | 83.76% | 7.33% | 5.68% |
| 32 / 500 | 180.333 | 84.84% | 6.43% | 5.34% |
| 128 / 300 | 544.011 | 91.68% | 5.04% | 2.17% |
| 128 / 500 | 666.948 | 91.54% | 4.20% | 3.32% |

Percentages are independent medians of sample-wise fractions, **not** ratios of
stage medians to a total median, and must not be forced to sum to 100%. Remaining
stages are scheduling, allocation/init, candidate formation, cleanup and CPU
delivery. Median total-minus-all-stages residual is 0.006-0.009 ms under default
wait and 0.019-0.024 ms under blocking wait. Full distributions and every
process/order are in [EVIDENCE.json](EVIDENCE.json); exact observations are in
[samples.csv](samples.csv) and [stages.csv](stages.csv).

### Default waiting consumes a CPU core without doing CPU distance work

All values below are marginal medians, milliseconds per complete query batch:

| Q / radius | Default wall | Blocking wall | Default main-thread CPU | Blocking main-thread CPU |
|---|---:|---:|---:|---:|
| 32 / 300 | 151.638 | 153.726 | 151.052 | 2.225 |
| 32 / 500 | 180.333 | 181.309 | 177.531 | 2.238 |
| 128 / 300 | 544.011 | 541.058 | 541.185 | 2.329 |
| 128 / 500 | 666.948 | 667.988 | 663.822 | 2.504 |

The paired geometric default/blocking CPU ratios are 67.86, 77.65, 233.31 and
259.30: blocking lowers main-thread CPU time in all six pairs per shape. This
is approximately 98.5-99.6% less CPU under the paired estimator, not faster
queries. Default main-thread CPU/wall medians are 98.4-99.6% of one core;
blocking gives 0.38-1.44%. Whole-process CPU, including helper threads, remains
only 3.02-3.55 ms at the marginal median under blocking.

Paired wall default/blocking ratios [bootstrap 95% CI], in table order:
0.9934 [0.9881, 0.9999], 0.9952 [0.9940, 0.9964],
1.0004 [0.9844, 1.0193], 0.9923 [0.9795, 0.9994]. There is no demonstrated
latency optimization here; three shapes favor default waiting slightly and
Q128/r300 is inconclusive. Do not replace the application's wait policy as a
performance improvement based on CPU reduction alone. No CPU call-stack/perf
sampling was collected; the one-variable intervention establishes sensitivity
to CUDA waiting, not a complete host arithmetic flame graph.

## 2. GPU timeline corroboration and missing counters

Six separate Nsight traces captured only three measured queries each. Across
the four default lighter traces, recorded GPU kernel/copy/memset interval unions
cover 96.4-99.3% of their query ranges. This is **temporal coverage, not achieved
SM utilization**. It differs from the earlier small Words update-entry path
with many one-block launches and large timeline gaps.

For Q128/r500, mean native kernel durations in the lighter default trace are:

| Native operation | Mean time per query |
|---|---:|
| `dataProcessRnn`: leaf distances and hit flags | 610.756 ms |
| `nodeProcessRnn`: four internal levels combined | 27.858 ms |
| `mergeResRnn`: result counting | 22.171 ms |

The blocking trace has a nearly identical leaf duration (610.903 ms mean).
Native `dataProcessRnn` launches 1,272,163 blocks of **512 threads** for that
case. Its source assigns one thread per leaf point; the unchanged parent index
has 6-12 points per leaf (mean 6.5536). Thus only 6-12 threads/block enter the
point-distance branch (self matches skip arithmetic), not 512. This is source
and launch-geometry evidence, **not a dynamic active-lane/occupancy counter**.
The same leaf kernel performs serial per-thread coordinate loops and indirect
point access; no experiment here isolates arithmetic from memory transactions.

Selected-function normalized SASS hashes and resources are recorded. Native
leaf/internal kernels report 47,528-byte stack frames (44/48 registers); the
counter reports 24 registers and no stack. Generic edit-distance code contains
a large per-thread table, but its presence does not prove a causal SIFT cost.

The first Q128/r500 light-trace query has 536 B of explicit D2H transfer and
421,888 B of combined recorded UM migration, with about 0.043 ms of copy-engine
activity. The separate fault-enabled trace records 14/15/15 CPU fault events
and 5,170/5,382/4,570 GPU faults across its three queries. Fault counts do not
mean unique pages, and copy duration does not bound fault-service stalls. The
256 MiB per-query memset is device-memory initialization, not PCIe upload.
These observations do not support bulk CPU-GPU transfer bandwidth as the
dominant explanation for a roughly 667-ms query.

**NCU hardware counters remain unavailable:** the one permitted attempt returns
`ERR_NVGPUCTRPERM`. Its application counts still validate, but counter collection
failed. No permissions/settings were changed and no retry was substituted.
There are no achieved SM/DRAM throughput, memory-sector, dynamic lane or stall
measurements. Arithmetic-bound versus memory/scheduling-bound remains unknown.

## 3. Reconcile the earlier CPU analysis: Words is not SIFT

The [earlier original-tree CPU report](../original_tree_profile/README.md)
measures Words strings with **edit distance**, Q32/r4, including range, kNN and
query-only update paths. Its range trace spends 62.9% of traced query wall in
result aggregation. That does not contradict the current SIFT **L2** leaf
dominance. The earlier clean control was a one-shot native lifecycle after
build; this one uses warm repeated queries with explicit CPU count delivery.
Profiler percentages and clean host-stage percentages are also distinct.

The common conclusion is wait-sensitive host CPU, not a universal GPU
bottleneck. Priority must be selected by metric, workload and execution path:
Words aggregation needs a counting control; this SIFT case needs a leaf-path
control. The earlier proposal of original / counter-only / access-only /
combined variants is an attribution design, not proof that coalescing is the
dominant mechanism. Do not apply a 32-lane coordinate reduction directly to
string edit distance, or transfer one dataset's percentage to another.

## 4. Claim ledger and next test

Experiment ID `gts_20260923_query_breakdown`, collected 2026-09-23. Provenance
maps to the frozen contract, per-run binary/fixture/source hashes, oracle gates
and retained raw receipt inventory in EVIDENCE.json.

| Claim | State | Allowed wording / limitation |
|---|---|---|
| Leaf processing dominates this SIFT range path | measured | 83.76-91.68% median host-stage share; corroborated by native leaf GPU durations, not all trees/metrics. |
| Most default query CPU is active CUDA waiting | inferred from measured one-variable control | All paired CPU ratios decrease sharply under blocking with no latency win; no sampled CPU flame graph. |
| Result aggregation is universally the main GTS bottleneck | rejected | True of the earlier Words range trace, not this L2 workload. |
| Leaf kernel is arithmetic-throughput-bound | unknown | NCU denied; stage/kernel time is not a roofline diagnosis. |
| Noncoalesced loads or generic stack cause the delay | unknown | Source/resource candidates, no single-mechanism causal control. |
| Bulk host-device copy bandwidth explains the delay | rejected for this traced scope | Recorded copy payload/time is small; fault/control latency remains a separate question. |
| TC is ineffective for tree distances | unknown in general | The earlier integration failed its gates; this diagnosis does not compare TC. |

Next bounded control: change only the native leaf launch from 512 to 32 threads
while preserving one-thread-per-point arithmetic, native buffers, result flags
and all query stages (MAX_SIZE=20). Keep the original comparator and exact
oracle. This tests oversized block/resource scheduling, **not** coalescing or
TC. If it fails, retain that negative result; investigate L2 specialization or
access layout separately. No such launch/metric/layout control was run here.

## Contract and interpretation

See [CONTRACT.md](CONTRACT.md). Parent repository commit: `80e4d06`. Original
author source: `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`, verified using the
existing 18-file source pins. Source originals and preceding campaigns are not
modified. Kernel bodies, launch geometry, native memory policy, arithmetic and
native synchronizations are unchanged.

Workload: the same 65,536 SIFT vectors with 128 integer coordinates, Q=32/128,
radius=300/500. Exact range counts include self and return to CPU. MAX_H=5,
MAX_SIZE=20, 256 MiB bounded workspace; smoke N=2,000 uses MAX_H=3. These resource
adaptations are necessary to run this bounded diagnostic and are not the
untouched historical paper binary. No generic GPU-tree conclusion follows.

All times exclude input parsing, context initialization, full-table integer
oracle, index build and warmup. Query allocation/free, traversal, candidate
formation, distances, aggregation and CPU delivery are included. There is no
materialized-ID, kNN/update, external-vector ingestion, cold-start, CUDA Graph,
concurrent-stream or production throughput claim.

Host stages are disjoint and include each region's original GPU waits. Thus a
long `leaf_distance` wall interval is not pure CPU arithmetic, and even a long
GPU leaf kernel is not proof of saturated arithmetic: it includes memory,
addressing, sparse useful lanes, dispatch and resource costs. GPU API waits
overlap kernels and must not be summed with them. Query total minus stage sum
is retained as an instrumentation/unaccounted residual.

The policy comparison changes only default CUDA waiting (D) versus blocking
waiting (B) in fresh processes. `cudaGetDeviceFlags` is recorded and schedule
bits checked. CPU/wall uses a **one-core denominator**; whole-process and main-
thread clocks are both measured over the query, not over oracle/index startup.
Six pairs per shape alternate D/B and B/D. Three warmups follow an initial
correctness call; eight retained calls per process. Every result is validated
outside timing. This is repeated-query diagnosis, not uninterrupted throughput.

Timing source contains host clock/map/NVTX instrumentation; no claim of zero
instrumentation overhead is made. Nsight uses separate runs and adds further
overhead. Profile capture covers exactly three `measured.query.*` ranges after
warmup, not setup or index construction. Lighter traces and an extra UM-fault
trace are distinguished. API-stage attribution uses entry-time containment on
the same CPU thread; unmatched calls remain unattributed. GPU stage attribution
is temporal overlap, not causal ownership or achieved SM utilization.

## Reproduce

Python standard library, the original source/data, CUDA13.1, NVTX3 headers,
compute-sanitizer and Nsight Systems are required. NCU is optional and existing
profiling permissions must be respected. No dependencies or driver settings are
installed/changed. Set `AUTHOR_SOURCE_ROOT` to the pinned root containing `GTS/`
and `GPU-Tree/`, `SIFT_BASE_TEXT` to the SIFT file, `CUDA_HOME` to the toolkit,
`SCRATCH` to an absent task-owned directory, and `ADMITTED_UUID` to the explicitly
admitted physical GPU0 UUID. A script argument is not GPU authorization.

```sh
python3 diagnostics/query_breakdown/test_prepare.py "$AUTHOR_SOURCE_ROOT"
python3 diagnostics/query_breakdown/test_analysis.py
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n2000" --n 2000
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n65536" --n 65536
for h in 3 5; do
  python3 diagnostics/query_breakdown/prepare.py "$AUTHOR_SOURCE_ROOT" "$SCRATCH/source$h" --height "$h"
  "$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
    -DGTS_DIAG_NVTX -Xptxas=-v -Xnvlink=--ignore-host-info \
    -I"$SCRATCH/source$h/GTS/include" "$SCRATCH/source$h/GTS/src/main.cu" \
    -ldl -o "$SCRATCH/bin/bench$h" > "$SCRATCH/logs/build$h.log" 2>&1
done
"$CUDA_HOME/bin/cuobjdump" --dump-sass "$SCRATCH/bin/bench5" > "$SCRATCH/logs/bench5.sass"
"$CUDA_HOME/bin/cuobjdump" --dump-resource-usage "$SCRATCH/bin/bench5" > "$SCRATCH/logs/resources.txt"
for stage in check sanitizer timing profile ncu; do
  python3 diagnostics/query_breakdown/run.py "$SCRATCH" --gpu "$ADMITTED_UUID" --stage "$stage"
done
mkdir -p "$SCRATCH/diagnostics/query_breakdown"
for file in CONTRACT.md prepare.py driver.cu stages.hpp run.py analyze.py test_prepare.py test_analysis.py; do
  cp "diagnostics/query_breakdown/$file" "$SCRATCH/diagnostics/query_breakdown/$file"
done
python3 diagnostics/query_breakdown/analyze.py "$SCRATCH" "$SCRATCH/curated"
```

The runner fails closed on busy GPU0, bad hashes, wrong results, sanitizer error,
timeout or post-run contamination. The one optional `ERR_NVGPUCTRPERM` result is
retained as unavailable counters, not a pass. Existing run folders are never
overwritten. Timed sources and frozen-contract hashes are retained separately
from final delivery hashes when documentation is appended after collection.

Only authored instrumentation, curated numerical evidence and manifests are
published. Raw inputs, generated upstream source, profiler reports/binaries,
machine configuration, runtime addresses and private receipts stay outside Git.
Relative raw-file hashes resolve against the task-owned scratch.
