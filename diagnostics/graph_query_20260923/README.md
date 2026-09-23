# GTS fixed-capacity CUDA Graph comparison

**Decision: keep Graph replay for this bounded query-only prototype.** Against the
same fixed-capacity ordinary-stream computation, Graph reduces median query
latency from **146.09 to 108.85 µs (1.342×)**. This establishes a submission-cost
opportunity in this GTS path, **not a new GPU-tree algorithm or a universal result**.

## Frozen scope and comparators

RTX PRO 6000 Blackwell Server Edition, CUDA 13.1.115, driver 590.48.01, `sm_120`.
Real Words subset N=2000; 64 deterministic distinct query IDs; batch one; inclusive
radius 4; immutable height-3 tree, fanout 10, leaf capacity 20; no updates or kNN.
Physical GPU 0 was admitted under its existing lock; clocks/settings were not
changed. Source copies and the original source remained hash-identical to the
[pinned author revision](../original_tree_redundancy/SOURCE_PINS.json).

| Variant | What executes | Median process-mean query µs | Median loop CPU µs/query |
|---|---|---:|---:|
| A | Original query functions, per-query allocations/waits, original projection; common result-delivery driver | 493.81 | 466.42 |
| B | Reused capacity, device counts, preallocated CUB, stream ordering | 146.09 | 146.21 |
| C | Exactly B's enqueue function, captured once and replayed | 108.85 | 109.01 |

The timer includes input preparation/transfer, query execution, completed host
result delivery and A's per-query teardown. Outputs include IDs, distances and
count in native order. Timing runs exclude output hashing from per-query time;
loop CPU includes those hashes. Build/setup/warmup are excluded and reported
separately. B/C pay for fixed delivery of 2220 ID/distance slots, whereas A delivers
only valid results. All variants use the same immutable managed tree/data.

**Attribution:** A→B is **3.380×**, combining allocation, control, scan implementation
and delivery changes; A→C is **4.536×**, not a Graph-only gain. B→C isolates Graph
submission and is **1.342×**, or **25.49% lower latency**. A is an original-function
comparator in the same binary, not a claim that the untouched main executable
was changed only by adding a graph.

Six fresh-process rounds ran in preregistered orders `ABC, CBA, BCA, ACB, CAB, BAC`,
4096 queries per process after 64 warmups. C wins all six. The paired geometric
mean B/C ratio is **1.332×**, with exact paired-bootstrap 95% interval
**[1.322, 1.341]**. This paired estimator differs from the primary ratio of medians;
the interval is not an interval for 1.342×. Sustained checks of 16384 queries per
process give **1.327× (BC order)** and **1.324× (CB order)**. Raw order and all
observations, including failures, remain in the private evidence archive.
Those longer loops last about 1.8–2.4 seconds; they are repetition checks, not
minutes-long thermal-steady-state or production-service certification.

## Mechanism evidence, not profiler speedup

NSYS node-level traces contain 193 queries each (first + 64 warmup + 128 sampled).
B and C have exactly the same ordered **24 kernels/query**, launch dimensions,
register counts and shared-memory settings. They also perform the same four
explicit query copies. B issues 24 host kernel launches plus four async-copy
calls/query; C issues one graph launch/query. Capture creates those nodes once.
Whole-trace host kernel API counts are B=4641 (9 build + 193×24) and C=33
(9 build + 24 capture), with 193 `cudaGraphLaunch` calls in C. A default graph-level
trace was retained; it hides individual C kernels, so it was not used to assert
kernel equivalence. [EVIDENCE.json](EVIDENCE.json) includes the checked signature.

Graph has **not fused or removed the 24 GPU kernels**, fixed the distance routine,
or increased a one-block kernel's parallelism. In these diagnostic traces,
`getQresultCount` still takes approximately **42.24 µs/query** in C, versus
100.64 µs summed GPU kernel time/query. Profiler times are perturbed and are not
the clean end-to-end denominator. The existing large per-thread distance stack
is retained (resource dump: 47528 bytes for traversal/leaf distance kernels).
No NCU run was part of this A/B/C campaign. The separate original-flow
[privileged NCU follow-up](../original_flow_20260923/NCU_PRIVILEGE_RETRY.md) must not
be represented as C's counters.

**CPU work/query falls, but CPU utilization percentage does not.** Median loop
CPU occupancy is approximately 94.53%, 100.02%, 100.03% of one core for A/B/C.
B/C complete the same work in less time while still keeping a core busy; rounding
and helper threads can exceed 100%. Do not claim Graph releases the CPU core,
proves CPU distance arithmetic is the bottleneck, or proves high SM utilization.

## Setup, correctness and negative evidence

| One-time metric, median of six clean processes | B | C |
|---|---:|---:|
| Workspace setup, including capture for C | 1432.40 µs | 2158.22 µs |
| Capture + instantiate (subset of setup) | — | 742.89 µs |
| First query, separately timed | 409.10 µs | 219.31 µs |

Capture-only cost divided by the measured steady saving is about **20 queries**;
this is an amortization estimate, not a measured cold-start crossover. C's first
query is not a steady replay sample. Setup excludes tree construction and common
initialization; A's setup is almost empty because A allocates inside each query.

- **23 full-output runs** pass independent byte-edit-distance CPU membership,
  distance and count checks, plus original-order agreement where A is valid.
  Radii 0, 4 and 256 cover exact matches, normal pruning and all 2000 hits.
- **12 sanitizer runs** pass: memcheck/synccheck for A/B/C, initcheck for B/C,
  plus B/C memcheck at radius -1 and 256. Leak checking was not enabled.
- **16384 changing-query stress calls per A/B/C** pass output-count and ordered
  ID/distance hashes derived from fully CPU-validated results. Fresh processes
  cover new allocations; no simultaneous in-flight graph instances were tested.
- **Rejected boundary:** radius -1 is an intentional empty-frontier robustness
  probe, not a normal search workload. A reports 65 invalid-argument leaf launches
  despite exit status zero; its run is rejected and retained. B/C independently
  return the correct empty result, including memcheck. Do not claim every native
  A boundary passed. A separately pinned zero-grid fix is the reopen condition.
- The freshly rebuilt **untouched executable anchor** passes 4096 native counts;
  process wall time is 2.5474 s. It uses the older 32-query sample and original
  logging/lifecycle, so it is not used in the A/B/C ratios. Native averages over
  zero actual updates print infinity and are excluded.

Acceptance gates in [CONTRACT.md](CONTRACT.md) pass **for radius-4 replay only**.
No full-data, larger-shape, update/concurrency, arbitrary query-vector, other
architecture or other-tree promotion is implied. B/C support changing IDs into
the fixed data array; each graph instance fixes the radius. Padding and extra
copy traffic may dominate at larger capacities. Next test: representative larger
N/query batches and selection densities with a newly frozen capacity contract;
keep launch/capacity changes separate from aggregation or distance optimizations.

## Reproduction

Use the pinned external author source and real Words dataset, neither redistributed
here. `AUTHOR_SOURCE_ROOT` contains `GTS/`. All destination directories must be
fresh. Python tools use only the standard library; CUDA provides Thrust/CUB.
Do not use Python `-O` or C++ `-DNDEBUG`: validation uses assertions.

```sh
D=diagnostics/graph_query_20260923
python3 diagnostics/original_tree_profile/make_fixture.py "$WORDS" "$FIXTURES" --sizes 2000
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$FIXTURES" "$SCRATCH"
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info \
  -Isource/include graph_bench.cu -o bin/graph_bench)
python3 "$D/oracle.py" make "$SCRATCH/fixtures/words_2000.txt" "$SCRATCH/fixtures/queries.qid" "$ORACLE"
# GPU 0 must be explicitly admitted and idle; run.py takes its nonblocking lock.
for m in A B C; do
  python3 "$D/run.py" "$SCRATCH" --gpu 0 --label "smoke_$m" --mode "$m" --dump
done
python3 "$D/oracle.py" check "$ORACLE" 4 "$SCRATCH/runs/"smoke_{A,B,C} \
  --expected "$SCRATCH/fixtures/expected_4.json"
```

Before timing, repeat full-output checks at 0 and 256, memcheck/synccheck for each
mode and initcheck for B/C. For example add `--tool memcheck --dump` with a fresh
label. Test radius -1 separately; A is expected to fail its runtime-error gate,
not to be admitted. `oracle.py check --expected` creates the monitored hash file
only after full independent checks and cross-variant order agreement. Never
skip these correctness gates based on receipt exit status alone.

After those gates, keep the lock across the complete timing suite:

```sh
export SCRATCH
PYTHONPATH="$D" python3 - <<'PY'
import fcntl, os
from pathlib import Path
from run import execute
root=Path(os.environ['SCRATCH']).resolve()
with open('/tmp/gtspp_gpu0.lock','a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    for m in 'ABC':
        assert execute(root,'0',f'stress_{m}',m,4,256,64,'clean',False)
    for i,order in enumerate(['ABC','CBA','BCA','ACB','CAB','BAC']):
        for m in order:
            assert execute(root,'0',f'timing_{i}_{m}',m,4,64,64,'clean',False)
    for i,order in enumerate(['BC','CB']):
        for m in order:
            assert execute(root,'0',f'sustained_{i}_{m}',m,4,256,64,'clean',False)
    for m in 'BC':
        assert execute(root,'0',f'nsys_node_{m}',m,4,2,64,'nsys-node',False)
PY
python3 "$D/test_cpu.py"
```

`analyze.py EXTRACTED_ROOT ORACLE ARCHIVE OUTPUT_JSON` regenerates this campaign's
summary, checks all retained labels, rejects the known bad native boundary,
verifies source/data/binary pins, full results, stress hashes and NSYS equivalence.
The private archive is identified by SHA256 in EVIDENCE.json. It includes original
source copies, binaries, fixture data, commands, receipts, ordered per-query
samples, sanitizer logs and profiler reports. Only portable code, sanitized
summaries and hashes are published. Fresh-build binary hashes can vary with build
paths; compare source/flags and validate the new run rather than assuming binary
identity across rebuild locations.

## Novelty boundary

Reducing repeated short-kernel submission through Graph is established; see
[NVIDIA's 2019 example](https://developer.nvidia.com/blog/cuda-graphs/) and
[2024 launch-cost analysis](https://developer.nvidia.com/blog/constant-time-launch-for-straight-line-cuda-graphs-and-other-performance-enhancements/).
This experiment is an engineering attribution result. It cannot rescue a paper
thesis whose mechanism is merely applying CUDA Graph to fixed-shape work.
