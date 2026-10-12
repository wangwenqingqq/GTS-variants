# Rebuild change amplification diagnostic

**NO_GO_LOCAL_MAINTENANCE:** canonical leaf membership changes 99.982% / 99.985%
and node topology changes 100% in the two actual rebuilds. Sparse logical updates
therefore cause real organization churn, not mostly identical tree state.
Packed surviving coordinates are 99.999% identical under occurrence alignment,
but dense physical rows move; no correct or faster delta mechanism is admitted.

One GIST N1M D960 trace, one observer GPU process, no optional GPU repeat, no
production algorithm/threshold change and no new latency result. Read RESULTS.md,
DECISION.md, CONTRACT.json and **POSTPROCESS_CLARIFICATION.md**. The original
pre-run schema and analysis v1 remain retained; final analysis explicitly separates
physical bytes, logical content, regenerated cardinality and instruction counts.

## CPU reader check

Requires existing Python 3 + NumPy; no dependencies are installed by these scripts.

```bash
python3 scripts/test_analyze.py
python3 -m py_compile scripts/*.py
python3 scripts/analyze.py "$SNAPSHOTS" "$OUT"
```

The synthetic regression changes physical row/node indices while preserving leaf
content, and catches false semantic churn. Exact full snapshot inputs are private;
no sampled packed-data substitute is accepted. `packed.f32` is 3,840,000,000 bytes
per snapshot. Four complete files remain on the experiment host with hashes.
Other raw artifacts and structural snapshots are replicated in a private small
archive. See evidence/RAW_ARCHIVE.json and summary/SNAPSHOT_MANIFEST.json.

## Exact observer reproduction

This is a recipe for the frozen authorized hardware/source/trace, **not an
instruction to run on an arbitrary shared GPU**. First verify allocation, GPU
UUID digest/driver/toolkit/NUMA and idle users; both existing locks are mandatory.
Changing hardware or workload requires a new contract, not editing old evidence.
The observer process timeout is 1,200 seconds; it only signals its owned group.

Inputs (must be recovered by pinned hashes, not fabricated):

- `$KEEPER_SOURCE`: original 25-file P2/source; evidence/SOURCE_AUDIT.json pins it.
- `$PRIOR`: completed external mixed closure with immutable P2 binary, cases/target,
  deps/locked.py + helpers/run_locked.py, checker, INPUTS, REGISTERED, CLOSURE,
  and primary/outputs/r1_P2.*.
- `$DATA`: exact binary dataset; `$NATIVE_REFERENCE`: pinned rank-oracle prefix.
- `$ROOT`: fresh task-owned scratch directory. Never overwrite the prior campaign.
- `$DIAG`: this published diagnostic directory; `$CUDA_ROOT`: CUDA 13.1 installation.

```bash
mkdir "$ROOT"
python3 "$DIAG/scripts/instrument.py" "$KEEPER_SOURCE" "$ROOT/observer_source"
cp "$DIAG/CONTRACT.json" "$ROOT/CONTRACT.json"
cp -R "$DIAG/scripts" "$ROOT/scripts"
"$CUDA_ROOT/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -lineinfo -rdc=true \
  -Xnvlink=--ignore-host-info --ptxas-options=-v \
  -I"$ROOT/observer_source/include" "$ROOT/observer_source/src/main.cu" \
  -o "$ROOT/observer" >"$ROOT/build.log" 2>&1
python3 "$ROOT/scripts/run.py" "$ROOT" "$PRIOR" "$DATA" "$NATIVE_REFERENCE"
```

run.py refuses an existing REGISTERED.json, verifies the keeper/data/case and
observer-source pins, executes one locked GPU process, checks complete byte parity
and event/rebuild semantics, invokes the frozen quality checker and analyzes all
saved state. Its CLOSURE is the initial closure, not the full post-close provenance
receipt. Timing includes deliberate snapshot stalls and must not be used for
latency comparison. No extra sanitizer, stress or external run is part of this
budget. Source CUDA bodies are preserved; identical SASS is not asserted.

For CPU-only closure of a recovered completed run, retain its original analysis,
RESULT, SNAPSHOT_MANIFEST and CLOSURE as `analysis_v1/`; retain original and clarified
scripts as separate versions if they differ. Supply the prior public raw-file
manifest as `$ROOT/PRIOR_RAW_FILE_MANIFEST.json`. Then:

```bash
python3 "$ROOT/scripts/analyze.py" "$ROOT/snapshots" "$ROOT/summary_v2"
python3 "$ROOT/scripts/analyze.py" "$ROOT/snapshots" "$ROOT/summary_v2_repeat"
python3 "$ROOT/scripts/close.py" "$ROOT" "$PRIOR" "$DATA" "$NATIVE_REFERENCE"
```

close.py rehashes every snapshot byte on the host, checks exact CPU determinism,
rebinds all original output hashes and rechecks dependencies against the prior
campaign's pins. Later script bindings are marked post-close, not retroactive
preregistration. The original CPU closure schema failure and repair are retained.
Recovery/publishing never grants another GPU run; optional replay was unused.

For independent verification of the recovered small raw archive without extraction:

```bash
python3 scripts/verify_archive.py "$SMALL_RAW_ARCHIVE" "$RAW_MANIFEST" "$LOCAL_RECEIPT"
```

This checks every small member byte, source/quality/closure bindings and the four
host-only pack manifest entries. It does **not** claim to read those pack bytes
on the client. The final original run uses 174 small archived files and four large
pack files; post-close dependency verification covers 1,770 prior pinned files.
