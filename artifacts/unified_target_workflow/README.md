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

## Preparation and build

Use installed NumPy/CUDA/Thrust and a fresh scratch directory **outside this
publication checkout**. Do not disable Python assertions. Preparation fetches
original GTS at the pinned SHA (or accepts `--upstream` for a verified checkout).
It applies the existing qualified adapter before the small target overlay.

```bash
python3 artifacts/unified_target_workflow/run.py prepare --work "$SCRATCH/target-build"
python3 artifacts/unified_target_workflow/run.py build --work "$SCRATCH/target-build" --nvcc nvcc
c++ -std=c++17 -O2 artifacts/unified_target_workflow/test_input.cpp -o "$SCRATCH/test-input"
python3 artifacts/unified_target_workflow/test_input.py --binary "$SCRATCH/test-input" --work "$SCRATCH/parser-cases"
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
python3 artifacts/unified_target_workflow/qualify.py small \
  --work "$SCRATCH/quality" --cases "$SCRATCH/cases" \
  --binary "$SCRATCH/target-build/bin/target" \
  --guard diagnostics/native_knn_faiss_ivf_20261003/run_locked.py \
  --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" \
  --legacy "$SCRATCH/target-build/parent/cases"
```

`qualify.py sanitize` and `qualify.py transition` use the same arguments without
`--legacy`. Sanitizer processes are diagnostic, not primary timing. The CPU
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
