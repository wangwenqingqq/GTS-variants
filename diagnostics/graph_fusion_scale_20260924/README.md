# Graph continuation and large-scale fusion: unvalidated checkpoint

**No new GPU experiment has run.** The gateway responds, but the target SSH
connection stalls/timeouts and GPU admission could not be completed. An earlier
session returned a hostname/date but not the GPU queries. The final bounded
probe timed out during SSH banner exchange. This does not establish GPU
occupancy, a driver fault, or host failure; do not guess the cause, kill foreign
processes, or start a benchmark without a fresh idle/lock check.

This checkpoint implements the supplementary experiment, not its result.
CUDA compilation, selector execution, full-query correctness, sanitizers,
profiling, timing and promotion are **pending**. CPU-only generator, mocked
collector-cleanup, missing/stale phase-admission tests pass. Source preparation
checks the pinned original files and preserves the exact B/C result branch.
The previous measurements remain unchanged; there is no new speedup claim.

## Planned comparison

| Mode | Result processing | Submission |
|---|---|---|
| B | Existing fixed-capacity sequence | Stream |
| C | Same as B | Graph |
| D | Fused stable result selection/projection | Stream |
| E | Same as D | Graph |

Shapes: N=2,000 / 100,000 / 611,756 at K=1, plus full N at K=32.
K is serial bundling, not parallel queries. All modes retain full ordered
host output, fixed output copies and original distance/traversal work.

The existing small-N selector is reused rather than replaced: a 512-thread CTA
uses CUB BlockScan ranks and aggregate to emit stable mapped IDs/distances,
carrying its count across tiles. Only its maximum-capacity contract is widened
from 111 candidates to the checked runtime capacity (at most 111,111). New tests
cover 352 combinations across four capacities, including poisoned inactive
flags, dense/empty/sparse/tile-boundary hits, nonidentity maps, rollover and
fresh allocations. These are implemented GPU tests, **not yet executed tests**.
The single-CTA tiled loop may scale poorly; that is part of the hypothesis,
not a presumption that fusion must win.

The driver retains all B/C result operations and introduces a distinct D/E
branch. It does not fuse tree traversal, candidate generation or leaf distance
computation. Workspace remains allocated even where D/E no longer need it,
so reduced memory allocation is not a claimed mechanism. The deletion-prefix
scan remains charged before fused projection.

The frozen contract, readiness/ownership card, estimator, negative hypotheses
and gates are in [CONTRACT.md](CONTRACT.md). [STATUS.json](STATUS.json) records
only offline preparation/provenance, never invented GPU measurements.

## Missing original Graph observations

`continue_graph.py` creates a **fresh** continuation root from the private,
interrupted scale snapshot. It checks every retained receipt/sample hash,
author source pins, the original executable, full-N input/reference hashes,
manifest query IDs, and oracle-derived expected hashes. It does not delete,
rename or overwrite the old failed process. It repeats full-output smoke at
K=1/32, collects the four missing B/C NSYS node traces, and reruns all six K32
rounds plus both sustained orders. No old favorable round is spliced into the
new comparison. Prior correctness/sanitizer/stress gates are carried only for
the identical frozen executable; this is recorded, not portrayed as rerun.

Only the runner's failure handling changes for this continuation: bounded NVML
probes, cleanup of owned child processes on collector failures, and retained
failure records. The CUDA executable is identical. Each run binds its runner
hash. On telemetry failure the collector stops its owned benchmark; it never
signals an observed foreign PID. Timing phases require hash-bound prior gates.

```bash
D=diagnostics/graph_fusion_scale_20260924
# BASE is the original private extracted scale snapshot, not the public JSON.
# CONTINUATION must not already exist. No GPU activity during prepare.
python3 "$D/continue_graph.py" prepare "$BASE" "$CONTINUATION"
# Re-admit the intended physical GPU 0 and original host/toolkit first.
# Run these manually only after reliable GPU state and idle/lock admission.
python3 "$D/continue_graph.py" run "$CONTINUATION" smoke
python3 "$D/continue_graph.py" run "$CONTINUATION" profile
python3 "$D/continue_graph.py" run "$CONTINUATION" timing
```

## Prepare the four-mode campaign

Python 3.10+ standard library, a C++17 compiler, CUDA 13.1, NSYS and Compute
Sanitizer are required on the measurement host. No dependency or GPU settings
are installed/changed. Do not use Python `-O` or C++ `-DNDEBUG`.
`AUTHOR_SOURCE_ROOT` contains `GTS/`; source/data are external and not shipped.
The preparation root must be fresh. Fixture preparation reuses the previous
scale generator and additionally creates the deterministic first-32-ID
`bundle.qid` with its manifest hash. Only the four selected shapes run.

```bash
D=diagnostics/graph_fusion_scale_20260924
python3 "$D/test_cpu.py"  # CPU only; fake child processes, no nvidia-smi call
python3 "$D/prepare.py" source "$AUTHOR_SOURCE_ROOT" "$SCRATCH"
python3 "$D/prepare.py" fixtures "$WORDS" "$SCRATCH"
(cd "$SCRATCH" && c++ -std=c++17 -O3 oracle.cpp -o bin/oracle)
python3 "$SCRATCH/fixtures.py" oracles "$SCRATCH"
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -Xptxas=-v \
  -Isource/include graph_bench.cu -o bin/graph_bench && \
 "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -lineinfo -Xptxas=-v \
  test_selector.cu -o bin/test_selector)
# Keep compiler output; inspect final resources and selected-selector SASS.
# After GPU admission, first run the stand-alone selector gates.
python3 "$SCRATCH/suite.py" "$SCRATCH" selector n2000_k1
CASES='n2000_k1 n100000_k1 n611756_k1 n611756_k32'
for phase in smoke gates; do
  python3 "$SCRATCH/suite.py" "$SCRATCH" "$phase" $CASES || exit 1
done
python3 "$SCRATCH/suite.py" "$SCRATCH" profile n2000_k1 n611756_k1 n611756_k32
python3 "$SCRATCH/suite.py" "$SCRATCH" timing $CASES
```

Run directories cannot be overwritten. Missing or stale phase gates block
measurement. Success markers bind benchmark/selector binaries and raw receipt
hashes. The final evidence summarizer and promotion audit remain pending actual
collection; a phase marker is not by itself a performance conclusion.
Raw data, code copies, reports and machine diagnostics stay outside Git.

## Current decision and next action

- Implementation: generated offline; CUDA build/runtime **unvalidated**.
- Mechanism: larger-shape fusion/Graph interaction **unknown**.
- Requested supplementary measurements: **not completed**.
- Next action: restore reliable target access and re-admit GPU 0, or obtain an
  explicitly authorized replacement host/GPU. A hardware change requires fresh
  comparator measurements, not ratios against the old device's numbers.
