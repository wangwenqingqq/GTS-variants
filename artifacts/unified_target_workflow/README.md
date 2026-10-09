# GIST target-size qualification overlay

This is phase A of the frozen target-workflow plan, not a new index or a speedup
report. Historical artifacts remain unchanged. Read `TARGET_CORRECTNESS.json`
and `TARGET_RESULTS.md` for the exact gate reached and remaining work.

The executor reuses the pinned original GTS update owner, PAR range scheduling,
and existing FULL/BOUND kNN kernels. Supported qualification dimensions are
128 and 960; the required target is existing FP32 GIST N1M/D960/B1/K8 with
radius bits `0x3f34a3d8`. Insertions reference current physical rows, deletion
removes one current live-rank occurrence, and buffer occupancy 10 really rebuilds.
Mode A has common numeric/safety repairs; it is not untouched original GTS.

The subsequent [phase-B overlay and recipe](phase_b/README.md) provides cloned
warmup/restore, qualified observer, fixed 18-process short comparison and six
static native Flat diagnostics. Its [result ledger](phase_b/RESULTS.md) does not
promote a global default, 10k workload or broad external speedup.

## Preparation and build

Use installed NumPy/CUDA/Thrust and a fresh scratch directory **outside this
publication checkout**. Do not disable Python assertions. Preparation fetches
original GTS at the pinned SHA (or accepts `--upstream` for a verified checkout).
It applies the existing qualified adapter before the small target overlay.

```bash
python3 artifacts/unified_target_workflow/run.py prepare --work "$SCRATCH/target-build"
python3 artifacts/unified_target_workflow/run.py build --work "$SCRATCH/target-build" --nvcc nvcc
c++ -std=c++17 -O2 artifacts/unified_target_workflow/test_input.cpp -o "$SCRATCH/test-input"
"$SCRATCH/test-input"
python3 artifacts/unified_target_workflow/test_input.py --binary "$SCRATCH/test-input" --work "$SCRATCH/parser-cases"
```

Source identities are frozen in `PREPARED.json`; build rejects changed source,
changed overlay files, an existing build checkpoint or an unavailable compiler.
No environment or dependency is installed by these commands. Public manifests
use portable relative paths; raw machine receipts and data remain in scratch.

## Bounded validation

Pass the existing registered GIST binary via `--data`; the fixture generator
reads original FP32 rows rather than integer-reinterpreting them. Select an idle
single sm_120 device and verify its PCI NUMA node first. Use the existing guard;
never terminate someone else's job to obtain a GPU.

```bash
python3 artifacts/unified_target_workflow/validate.py fixtures --data "$GIST_F32BIN" --work "$SCRATCH/cases"
for STAGE in small extreme transition legacy32 growth sanitize million; do
  python3 artifacts/unified_target_workflow/qualify.py "$STAGE" \
    --work "$SCRATCH/quality" --cases "$SCRATCH/cases" \
    --binary "$SCRATCH/target-build/bin/target" \
    --guard diagnostics/native_knn_faiss_ivf_20261003/run_locked.py \
    --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" \
    --legacy "$SCRATCH/target-build/parent/cases" --data "$GIST_F32BIN" || exit 1
done
python3 artifacts/unified_target_workflow/high_precision.py \
  --data "$GIST_F32BIN" --output "$SCRATCH/exact-reference.json"
python3 artifacts/unified_target_workflow/check_stale.py \
  --work "$SCRATCH/stale" --case "$SCRATCH/cases/gist4096" \
  --binary "$SCRATCH/target-build/bin/target" \
  --guard diagnostics/native_knn_faiss_ivf_20261003/run_locked.py \
  --gpu "$GPU_UUID" --numa-node "$NUMA_NODE"
```

Set `SCRATCH`, `GIST_F32BIN`, `GPU_UUID` and `NUMA_NODE` before running these
commands from the repository root. Use a fresh scratch directory for a repeat;
existing fixture, build or guarded-output checkpoints are not overwritten.
`nvcc`, `compute-sanitizer`, `numactl`, Python/NumPy and a C++17 compiler must
already be installed and available on PATH. Dataset registration checks the
header, exact payload size and SHA256 against `SOURCE_PINS.json` before creating
fixtures and again before the million stage. It never downloads the dataset.

| Stage | Fresh-process scope |
|---|---|
| `small` | 48 A/B/C processes: GIST prefixes, synthetic threshold/tail cases, legacy K8 cases |
| `extreme` | 3 A/B/C processes: finite extreme FP32 inputs and valid infinite FP32 distance fields |
| `transition` | 3 A/B/C processes: GIST N65,536/D960 |
| `legacy32` | 9 A/B/C processes: boundary radius 10,000, zero-radius ties and sparse K32 cases |
| `growth` | 3 A/B/C processes: parent's N1000/D128 `ties8` data, 1010 insertions, 101 real rebuilds, final N2010 |
| `sanitize` | 3 BOUND processes: edge257 memcheck/racecheck/synccheck |
| `million` | 3 A/B/C processes plus BOUND memcheck: registered N1M/D960 binary in place, 19 events, 8 queries, one real rebuild |

The generator creates both large-trace event files and `extreme255`; it does not
copy the million-row data. Every successful GPU process is followed by a fresh
independent CPU oracle and all-member interval check, including million
sanitizer output. Full ID, field and query payloads must be byte-identical across
A/B/C (and million memcheck). Deterministic operation-state columns must match;
ACK/rebuild times must independently be finite and nonnegative, not identical.
Reported execution modes must equal the requested modes. These CPU-heavy diagnostics may take much
longer than the GPU process; their wall time is never an end-to-end denominator.
The standalone exact-reference command checks initial q0 and the post-rebuild
q1 coordinate using exact-rational arithmetic and individually rounded steps.

This recipe reproduces the qualification scope from a fresh checkout; it does
not require private r4/r5/r6 logs or the historical executable hashes. Historical
records and their explicitly limited cross-revision binding remain unchanged in
`TARGET_CORRECTNESS.json`. The recipe follow-up changed only Python admission
scripts/documentation, not the executed CUDA/C++ source identities.

Sanitizer processes are diagnostic, not primary timing. The CPU
oracle scans all occurrences in bounded chunks with ordered FP64 arithmetic;
it does not use tree pruning or early termination. Every field and multiplicity
is retained. Range canonical ordering is additionally compared across modes;
kNN ordering is independently checked by squared score then live rank.
`check_stale.py` deliberately corrupts actual publication metadata to verify
fail-closed common-pointer, PAR-epoch and kNN-mirror guards.

Complete Host-ready output grows on demand under a combined 1 GiB ID/field
budget; exhaustion fails the whole trace, not truncates it. This is not a promise
that every arbitrary 10k all-result trace fits. Long workload output admission,
separate warmup-state restoration, observer requalification, external native
Flat snapshots and paired end-to-end timing remain separate required gates.

No manuscript is included here. Method/evaluation prose stays in private Overleaf.
