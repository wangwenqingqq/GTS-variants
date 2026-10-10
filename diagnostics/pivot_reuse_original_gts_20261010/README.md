# Original kNN pivot-distance reuse

This directory tests an original-GTS redundancy, not the later FULL/BOUND range
scanner. See `BASELINE_AUDIT.md`, `CONTRACT.json` and `DESIGN_CARD.md` for identity,
the deleted-equivalent G2/G3 modes, boundaries and the frozen denominator.
Read `RESULTS.md` for the current validation/measurement state.

## Replay

Linux, Python3.11+, CUDA13.1, SM120, NumPy/CuPy, compute-sanitizer and numactl are
required. Reuse the preceding native-kNN campaign's input/cache/oracle layout
without modifying it. Data/index binaries are not shipped; exact hashes are in
the contract. Caller-supplied original source must match all eight upstream pins.

```sh
# Required read-only reference preflight. The inherited driver would otherwise
# build a missing cache; never point it at a missing reference index.
for name in GIST.index oracle_GIST_final256.json synthetic_96.f32bin \
  synthetic_960.f32bin synthetic96.index synthetic960.index \
  oracle_synthetic96.json oracle_synthetic960.json fixtures/synthetic_ragged33.qid
do test -f "$REFERENCE_ROOT/$name" || exit 1; done
bash build.sh "$PINNED_GTS_SOURCE" "$NEW_SCRATCH"
ARGS="--root $NEW_SCRATCH --reference $REFERENCE_ROOT --data $GIST_DATA --python $CUDA_PYTHON --gpu $IDLE_GPU_UUID --numa $VERIFIED_NUMA"
python3 "$NEW_SCRATCH/run.py" diagnose $ARGS
python3 "$NEW_SCRATCH/run.py" qualify $ARGS
# Inventory only known historical GIST IDs. Incomplete history is disclosed.
python3 history.py --root "$KNOWN_QUERY_COLLECTION" --out "$NEW_SCRATCH/HISTORICAL_INVENTORY.json"
python3 "$NEW_SCRATCH/run.py" freeze $ARGS
python3 "$NEW_SCRATCH/run.py" formal $ARGS
python3 analyze.py "$NEW_SCRATCH" "$NEW_SCRATCH/SUMMARY.json"
```

Optional separately preregistered correctness/attribution extensions run only
after the complete formal gate; they never replace its observations:

```sh
python3 boundary.py --campaign "$NEW_SCRATCH" --reference "$REFERENCE_ROOT" \
  --out "$NEW_BOUNDARY_SCRATCH" --python "$CUDA_PYTHON" \
  --gpu "$IDLE_GPU_UUID" --numa "$VERIFIED_NUMA"
python3 profile.py --campaign "$NEW_SCRATCH" --reference "$REFERENCE_ROOT" \
  --data "$GIST_DATA" --out "$NEW_PROFILE_SCRATCH" --python "$CUDA_PYTHON" \
  --trace-analyzer ../native_knn_faiss_ivf_20261003/analyze_profiles.py \
  --gpu "$IDLE_GPU_UUID" --numa "$VERIFIED_NUMA"
python3 audit_index.py "$PINNED_GIST_INDEX" "$NEW_WARP_SCREEN_JSON" --warp-screen
```

All extension output directories must be new. Contracts and input/source hashes
are recorded before their first process and checked again after collection.
An explicit unsupported-input rejection is not a successful N<K full search.

Scripts refuse existing evidence paths, hash drift, occupied GPU/lock failure,
native runtime-error logs, sanitizer errors and incomplete/incorrect outputs.
Telemetry has a10s bound; inherited runner cleanup only reaps its own benchmark
group/monitor. No clock/power changes or foreign-process signals are permitted.
Each formal process uses the same frozen source, query set, index, physical GPU
and NUMA binding; timing and profiler collection remain serialized.

Minimal CPU check:

```sh
python3 test_protocol.py "$PINNED_GTS_SOURCE" "$PINNED_GIST_INDEX"
```

## Evidence and rights

Public output is curated text with exact collection/source identities. Private
raw paths, unrelated workloads, index/data/result binaries and profiler captures
stay outside Git. Original GTS is attributed to
[ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS), revision
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Upstream headers are not redistributed;
the generator verifies caller-supplied source. No new license is imposed on
upstream or derived code. A cache-work reduction is not a latency win, novelty,
external superiority, or an update benefit.
