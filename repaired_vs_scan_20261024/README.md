# Repaired GTS versus strong scan: incomplete admission checkpoint

**No new GPU comparison ran. GTS++ positioning remains undecided.** Physical
GPU 0 acquired a foreign VLLM process after the first idle observation. GPU work
was stopped before the first benchmark launch. A later read-only diagnostic was
idle; it was retained, not used to restart or replace the stopped attempt.

- [Report and all 18 required workloads](REPORT.md)
- [Frozen contract](CONTRACT.md) and [pre-GPU batching amendment](AMENDMENTS.md)
- [Machine-readable results](RESULTS.json): all GPU values are null, not zero
- [GPU admission evidence](evidence/GPU_ADMISSION.json)
- [Frozen calibration/query IDs](evidence/calibration.json)
- [Independent CPU oracle manifest](evidence/CPU_ORACLE.json)
- [Actual native ArborX configuration failure](evidence/ARBORX.json)
- [Validation scope](evidence/VALIDATION.json)

## What exists, and what does not

This directory contains CPU calibration/oracle generation, complete oracle
structure auditing, small runnable CPU regression checks, and a fail-closed
read-only GPU admission checker. Both complete input fixtures and eight original
GTS source files were verified against preserved SHA-256 pins.

It does **not** contain a newly assembled/compiled R CUDA binary, a strong native
batch scan benchmark, a full campaign runner, GPU output validation, sanitizer
results, instrumentation counts, or paired latency samples. Existing repair
source is referenced below rather than copied and represented as a newly
validated combination. This is not a completed experiment or a runnable GPU
continuation.

## CPU reproduction

Run from this directory. The full data and large oracle files are external to
Git; provide the exact Words text and preserved full float32 Tloc binary fixtures
identified in the contract. Use a fresh scratch directory; never overwrite an
old run. The oracle is independent full-table integer DP / float64 L2, built
with assertions enabled, four CPU workers, no CUDA dependency or GPU execution.

```sh
python3 test_cpu.py
mkdir "$SCRATCH" "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/fixtures"
cp "$WORDS" "$SCRATCH/fixtures/words.txt"
cp "$TLOC_F32BIN" "$SCRATCH/fixtures/tloc.f32bin"
cp oracle.cpp fixtures.py admission.py test_cpu.py summarize_cpu.py CONTRACT.md "$SCRATCH/"
(cd "$SCRATCH" && c++ -std=c++17 -O3 -pthread oracle.cpp -o bin/oracle)
python3 fixtures.py ids "$SCRATCH/fixtures"
"$SCRATCH/bin/oracle" cal words "$SCRATCH/fixtures/words.txt" \
  "$SCRATCH/fixtures/words.cal.qid" "$SCRATCH/fixtures/words.cal.json"
"$SCRATCH/bin/oracle" cal tloc "$SCRATCH/fixtures/tloc.f32bin" \
  "$SCRATCH/fixtures/tloc.cal.qid" "$SCRATCH/fixtures/tloc.cal.json"
python3 fixtures.py freeze "$SCRATCH/fixtures"
# Read radii only from the frozen calibration.json, not test observations.
python3 - "$SCRATCH" <<'PY'
import json, subprocess, sys
from pathlib import Path
p = Path(sys.argv[1]).resolve()
for name, v in json.loads((p/'fixtures/calibration.json').read_text())['datasets'].items():
    data = 'words.txt' if name == 'words' else 'tloc.f32bin'
    subprocess.run([str(p/'bin/oracle'), 'test', name, str(p/'fixtures'/data),
                    str(p/f'fixtures/{name}.test.qid'), str(p/f'fixtures/{name}.oracle'),
                    *map(str, v['radii'])], check=True)
PY
python3 summarize_cpu.py "$SCRATCH" "$SCRATCH/CPU_ORACLE.json"
```

Verify the two input SHA-256 values in CONTRACT.md **before** reproduction;
these tools do not download datasets. The recorded run used GNU 13.3.0 on
x86_64 Linux. Oracle binary hashes are compiler/platform dependent; input,
query, radius, output and source hashes are recorded separately. Large oracles
remain in the retained task scratch: Words 466,696,576 bytes, Tloc 32,795,308 bytes.
The source/header copies, binaries and raw machine/path-bearing diagnostics are
private local artifacts, not Git payloads. The public evidence is curated and
hash-bound; ask for the retained artifacts if independent raw-log inspection is
needed.

`admission.py` takes a scratch root with `logs/`, inspects only physical GPU 0,
uses the existing GPU-0 advisory lock plus a task lock, and never executes a
benchmark. Exit 75 means occupied/unreadable telemetry. An existing receipt
prevents overwriting that admission. A successful snapshot is not continuing
lock ownership or authorization to resume a stopped campaign.

## Remaining implementation route

Use the pinned original source, not the modified top-level backup implementation.
Keep all new generated CUDA code in this directory / fresh task scratch.

1. Compose fixed workspace/Graph from `diagnostics/graph_query_20260923` and
   `graph_scale_20260923`, stable selection from `fused_result_20260923` and
   `fusion_scale_20260924`, and multi-CTA/dead-count removal from
   `traversal_grid_l2_20260924` / `traversal_count_combo_20260924`.
2. Generalize multi-CTA traversal to Words without changing original predicates,
   distance arithmetic or output order. Do not silently substitute a different
   full-table/rolling distance implementation in A/R.
3. Reuse the exact rolling-row Words scanner and existing
   `diagnostics/flat_scan_l2_20260924`; implement strong native scan batching
   under AMENDMENTS.md, without requiring a metric tree for scan setup.
4. Implement the common complete-output host-ready timer and CPU-oracle checks,
   native A/R ordered comparison, boundary sanitizers, Graph stress, and a
   separate instrumented build. Only then collect six fresh paired rounds.
5. Native ArborX needs a usable CUDA-enabled Kokkos CMake package. This attempt
   stopped at native CMake configuration, before any benchmark adapter/build.
   No dependency was installed and no handwritten substitute was used.
6. A separately authorized full attempt must start with new idle/lock admission
   and retain the stopped attempt; never splice old or contaminated observations.

The original GTS Update API has a `qnum` argument. The preserved repair driver is
batch-one (serial bundling is not native batching); full-output Q1024 native
support was not established here. Optional Deep and any paper drafting remain
out of scope until the required comparison can be completed.
