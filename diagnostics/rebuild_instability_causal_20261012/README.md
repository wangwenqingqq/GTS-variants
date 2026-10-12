# Causal structural instability: standalone construction replay

This is a diagnostic of the frozen P2 tree organization, not a new production index. Start from `4ca13646a3968620069b70d71dcfe373b57c3486` and its four captured rebuild snapshots. The immutable contract is [CONTRACT.json](CONTRACT.json). Final evidence and decisions are in [RESULTS.md](RESULTS.md) and [DECISION.md](DECISION.md).

Only an optional early selected-pivot load is changed. The same POST FP32 coordinates, physical base order, native distance arithmetic, encoded-key sort, split geometry and deeper pivot rule remain fixed. Deeper PRE correspondence is a unique mutual maximum occurrence-membership overlap, never a numeric node-ID match. Missing pivots / ambiguous correspondence fall back to native and are counted.

## Reproduce in an authorized private scratch

Required: the 25 source-pinned keeper files, the prior complete snapshot/closure bundle, installed CUDA 13.1 with Thrust, Python + NumPy, and the preserved ownership-checking GPU runner. Large coordinates, raw keys, binaries and device configuration are intentionally not public. The public metadata does not make this a fresh-clone data release.

```sh
python3 scripts/prepare.py "$KEEPER_SOURCE" "$CASE_ROOT"
cp CONTRACT.json "$CASE_ROOT/CONTRACT.json"
CUDA_BIN="${CUDA_BIN:-/usr/local/cuda/bin}"
"$CUDA_BIN/nvcc" -std=c++17 -O3 -arch=sm_120 -lineinfo -rdc=true \
  -Xnvlink=--ignore-host-info --ptxas-options=-v \
  -I"$CASE_ROOT/source/include" "$CASE_ROOT/source/src/replay.cu" \
  -o "$CASE_ROOT/replay" > "$CASE_ROOT/build.log" 2>&1
cp -R scripts "$CASE_ROOT/"
python3 scripts/campaign.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$PRESERVED_RUNNER_DIR" native
python3 scripts/campaign.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$PRESERVED_RUNNER_DIR" C1
python3 scripts/analyze.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$CASE_ROOT/summary_C1"
python3 scripts/admit.py "$CASE_ROOT" C2
python3 scripts/campaign.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$PRESERVED_RUNNER_DIR" C2
python3 scripts/analyze.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$CASE_ROOT/summary_C2"
# Continue only after the independent input/decision closure passes.
python3 scripts/verify.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$CASE_ROOT/summary_C2"
cp "$CASE_ROOT/CLOSURE.json" "$CASE_ROOT/CLOSURE_C2_v1.json"
cp "$CASE_ROOT/RAW_MANIFEST.json" "$CASE_ROOT/RAW_MANIFEST_C2_v1.json"
python3 scripts/admit.py "$CASE_ROOT" C3
python3 scripts/campaign.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$PRESERVED_RUNNER_DIR" C3
python3 scripts/analyze.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$CASE_ROOT/summary_final"
python3 scripts/verify.py "$CASE_ROOT" "$REBUILD_SNAPSHOTS_ROOT" "$CASE_ROOT/summary_final"
python3 scripts/test_analyze.py
```

Do not reuse a registered directory, silently retry a failed GPU run, use GPU 0, change clocks, signal foreign processes, or expand to C4 / freeze-all. Both native PRE and C0 byte-replay gates must pass before interventions. Campaign timing/profiler data is not a performance result.

## Interpretation boundaries

- Exact sorted occurrence membership is the leaf-identity gate. Best overlap and Jaccard are descriptive only.
- Selected split pivots at decision levels 0..4 differ from inherited `TN.pid` at node levels 1..5. Root `TN.pid` is -1.
- Root full-membership identity necessarily changes when deleted occurrences are replaced; this is not movement to a different parent. Correspondence-retained common objects are reported separately.
- Captured ties concern exact **encoded keys**, including native node offsets / floating-point rounding, not an independently recomputed Euclidean-distance tie oracle. No secondary sort key is supplied. Tie diagnostics count adjacent input-rank descents and reordered common tie subgroups, not every pair inversion.
- Boundary crossing uses only common occurrences retained within explicitly matched parents, with imports/exports and unmatched counts reported. Crossing several boundaries is not several unique objects.
- No query quality, Graph, sanitizer/stress, latency, throughput, or production admission is claimed for the counterfactual structures.
