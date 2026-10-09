# Submission A: rebuild attribution and CPU/GPU baseline admission

**Completed:** two independent real-rebuild diagnostic profiles, six native
CPU static diagnostic processes, all384 query-quality checks, and concrete
GPU_TREE/MVPT capability/blocker audits. The shallow pivot-distance mapping is
the next supported intervention. **Not completed:** tiled candidate, submission-B
identity/sanitizer gates, submission-C paired workflow or formal external rounds.

- [Rebuild stage account](REBUILD_BREAKDOWN.md)
- [Actual capabilities and blockers](BASELINES.md)
- [Static diagnostic results and boundaries](BASELINE_RESULTS.md)
- [Frozen pre-registration](CONTRACT.json), [attempts/corrections](ATTEMPTS.md)
- [Claim/effect/end-to-end ledger](CLAIMS.md)

Old phase-B18 primary processes and all earlier evidence are preserved. This
overlay changes only Host instrumentation for the profile and adds native CPU
static adapters. No new GPU kernel, manuscript, raw input vectors, private host
configuration, cookie, long workload or default promotion is published.

## Prerequisites and safe reproduction

Start in the repository root, with Python assertions enabled (never `-O`). Reuse
existing Python/NumPy, sklearn1.6.1/threadpoolctl, native Faiss1.15.1, numactl,
C++17/OpenMP, CUDA13.1/Thrust, cuobjdump and NSYS2025.5.2.266. Do not install or
upgrade environments for this recipe. Set `SCRATCH` to a **new external private
directory**, `GIST_F32BIN` to the registered original binary, `TREE_PYTHON` and
`FAISS_PYTHON` to existing environment executables without resolving away venv
symlinks. Resolve `GPU_UUID`/`NUMA_NODE` from a fresh user/process/topology check.
Use a caller-selected admitted idle device and live-verified device-local NUMA
placement, not a hard-coded slot. Preserve all
foreign jobs and shared settings. Own CPU diagnostics are serialized; the host
is not represented as globally CPU-exclusive.

```bash
R=artifacts/rebuild_tree_baselines
B=artifacts/unified_target_workflow/phase_b
GUARD=diagnostics/native_knn_faiss_ivf_20261003/run_locked.py
python3 "$R/test_checks.py"
python3 "$R/profile.py" --work "$SCRATCH/profile_build_clean" --nvcc nvcc
```

Preparation fetches the same pinned minimal ancestor via the existing overlay;
`--upstream "$PINNED_UPSTREAM"` reuses a verified local source. A directory
transfer must whitelist regular source files and preserve hashes, not include
AppleDouble `._` files. Keep PREPARED/PROFILE_PREPARED/BUILD metadata private.

### Exactly two profile jobs, no primary latency inference

Register before collection (names/count/prefix/source/binary/data identity):

```bash
export SCRATCH GIST_F32BIN
python3 - <<'PY'
import json,os,sys,time
from pathlib import Path
sys.path.insert(0,'artifacts/rebuild_tree_baselines')
from cpu import sha
s=Path(os.environ['SCRATCH']);r=Path('artifacts/rebuild_tree_baselines')
destination=s/'PROFILE_REGISTERED.json';assert not destination.exists()
assert sha(Path(os.environ['GIST_F32BIN']))=='f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7'
destination.write_text(json.dumps(dict(registered_unix=time.time(),jobs=['A_NSYS','B_NSYS'],
 binary_sha256=sha(s/'profile_build_clean/bin/target'),instrumentation_sha256=sha(r/'profile.py'),
 contract_sha256=sha(r/'CONTRACT.json'),prefix_sha256=sha(r/'REBUILD_PREFIX.txt'),
 data=os.environ['GIST_F32BIN'],scope='diagnostic-only event48; unchanged ACK fences'),indent=2)+'\n')
PY
```

On the measured host, ordinary-user process sampling was unavailable. Scoped
sudo was used for **only this guard/profiler process tree**, with no sysctl/device
changes. If process-tree sampling is already available, omit `sudo -n`. Inspect
ownership before stopping anything; the guard signals only its own process group.

```bash
set -e
NSYS_BIN=$(command -v nsys)
test -f "$NSYS_BIN"; case "$NSYS_BIN" in /*) ;; *) exit 1 ;; esac
for MODE in A B; do
  RANGE=NATIVE; test "$MODE" = B && RANGE=PAR_STRONG
  sudo -n python3 "$GUARD" --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" \
    --output "$SCRATCH/profiles/$MODE/guard" -- \
    "$NSYS_BIN" profile --trace=cuda,nvtx,osrt --sample=process-tree \
      --cpuctxsw=process-tree --backtrace=dwarf --capture-range=cudaProfilerApi \
      --capture-range-end=stop --cuda-um-cpu-page-faults=true \
      --cuda-um-gpu-page-faults=true --kill=none \
      --output="$SCRATCH/profiles/$MODE/trace" /usr/bin/env \
      REGION_MODE="$RANGE" KNN_MODE=FULL TARGET_WARMUP=1 U10_OBSERVE=1 \
      U10_TREE_AUDIT=0 TARGET_RESTORE_AUDIT=0 \
      "$SCRATCH/profile_build_clean/bin/target" "$GIST_F32BIN" \
      "$R/REBUILD_PREFIX.txt" 2 0.705625057220459 "$SCRATCH/profiles/$MODE/out" 8
  "$NSYS_BIN" export --type=sqlite --output="$SCRATCH/profiles/$MODE/trace.sqlite" \
      "$SCRATCH/profiles/$MODE/trace.nsys-rep"
  python3 "$R/analyze_profile.py" "$SCRATCH/profiles/$MODE/trace.sqlite" \
      --output "$SCRATCH/${MODE}_BREAKDOWN.json"
done
cuobjdump --dump-sass "$SCRATCH/profile_build_clean/bin/target" >"$SCRATCH/profile_target.sass"
```

Capture is only event48 of the same51-event prefix after cloned warmup/restore.
No per-stage sync is added. `verify_profile.py` can bind fresh complete answers
and all state rows to the retained admitted parent's round1 A/B prefixes:

```bash
python3 "$R/verify_profile.py" --raw "$SCRATCH" --parent "$PARENT_PRIMARY_RAW" \
  --parent-quality "$B/evidence/PRIMARY_QUALITY.json" \
  --raw-sass "$SCRATCH/profile_target.sass" \
  --normalized "$SCRATCH/profile_target.normalized.sass" \
  --output "$SCRATCH/PROFILE_QUALITY_BOUND.json"
```

The frozen all-function normalized hash verifies GPU-code identity, not speed.
The exact target-binary SHA can change with build paths/toolchain; record it,
do not replace the delivered hash. A new unmatched GPU-code hash requires a
new identity investigation. Stage attribution uses runtime correlation IDs,
not asynchronous completion within NVTX. Host/GPU/UM/nested times overlap.

### Six native CPU static diagnostics and independent complete checking

Reuse the two qualified phase-B snapshot folders via `SNAPSHOTS`; no new query
selection. If absent, the phase-B `snapshots.py prepare` recipe regenerates them
from the pinned original336-event trace and data with lineage/hash proofs; this
does not require rerunning the old18-process primary matrix. Reuse the existing
qualified CPU oracle library as `CPU_LIBRARY` with CPU_BUILD/CPU_ORACLE metadata
and conformance hashes, or rebuild/qualify via the phase-B `cpu-oracle` recipe.

```bash
mkdir "$SCRATCH/cpu"
python3 "$R/cpu_jobs.py" --register --work "$SCRATCH/cpu" \
  --snapshots "$SNAPSHOTS" --initial-data "$GIST_F32BIN" \
  --tree-python "$TREE_PYTHON" --faiss-python "$FAISS_PYTHON" --numa-node "$NUMA_NODE"
python3 "$R/cpu_jobs.py" --work "$SCRATCH/cpu" \
  --tree-python "$TREE_PYTHON" --faiss-python "$FAISS_PYTHON" --numa-node "$NUMA_NODE"
# Only after all six timing processes have exited, not concurrently with them:
numactl --cpunodebind="$NUMA_NODE" --membind="$NUMA_NODE" \
  "$TREE_PYTHON" "$R/qualify_cpu.py" --work "$SCRATCH/cpu" \
  --executed-source "$R/cpu.py" --library "$CPU_LIBRARY"
```

Each native process has900s/32GiB address-space limits, leaf128, single native
thread,8 warm queries/task,32 B1K8 and32 complete native range deliveries. Native
speed and any failure remain visible. The validator binds original successful
receipts and all inputs/coordinates/hashes before scoring every occurrence.
Do not replace failed measurements with zeros or rerun until favorable.

## Private evidence and publication whitelist

Keep registered inputs, snapshots/lineage, executables, full outputs, all
receipts, source checkpoints, NSYS reports/SQLite and SASS outside Git. Public
`evidence/` contains only complete diagnostic aggregates and their hashes.
`curate.py` expects the documented original receipt archive layout (raw_cpu,
raw_cpu_quality, raw_profiles, PROFILE_QUALITY_BOUND.json and upstream_audit) and fails closed; it does not
copy arbitrary raw folders. For a new run, make its own registration and retain
its real hashes rather than pretending to reproduce the old receipt.

`evidence/CPU_RESULTS.json` distinguishes the actual execution launcher from
the subsequently delivered registration helper. `PROFILE_BINDING.json` also
distinguishes the guard's NSYS executable hash from the target-binary hash.
The unresolved96B context symbols and MVPT/GPU_TREE blockers are retained.
Submission A is a staged checkpoint, **not completion of submissions B/C**.
