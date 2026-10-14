# Reproduce the fixed-sector diagnostic

Use the existing Linux g++/OpenMP and Python/NumPy environment. Do not install a
framework or dependencies, initialize CUDA, or overwrite previous runs. Verify
CPU/memory/disk admission and active users before using a shared host. The parent
sources listed in CONTRACT.json must be present unchanged; the new native source
reuses the parent's guards and fixture functions.

From the repository root set `DATA` to the original GIST FP32 file, `CACHE` to the
32 frozen `<query_id>.f64` files, and `WORK` to a **new task-owned scratch path**.
The file has a three-int32 little-endian header `(960,1000000,2)`. Original vectors,
queries and full-score/proof arrays are not redistributed; their hashes identify
inputs but cannot replace access to them.

```sh
A=artifacts/sector_proof_per_byte_gate6_20261014
unset PYTHONOPTIMIZE
export PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES=""
export OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir "$WORK"
timeout --signal=TERM 3600s nice -n 10 python3 "$A/run.py" --stage A   --data "$DATA" --cache "$CACHE" --repo "$PWD" --work "$WORK/a"
```

Inspect A/RESULTS.json. Only **STRONG_SECTOR_HEADROOM**, zero numerical-boundary
ambiguity and every quality check admit the one B process; all other labels stop.

```sh
timeout --signal=TERM 1800s nice -n 10 python3 "$A/run.py" --stage B   --stage-a "$WORK/a" --data "$DATA" --cache "$CACHE"   --repo "$PWD" --work "$WORK/b"
nice -n 10 python3 "$A/analyze.py" --stage-a "$WORK/a" --stage-b "$WORK/b"   --cache "$CACHE" --output "$WORK/scalars"
```

For A stop cases, omit `--stage-b` from the observer. It checks hashes and saved
partials without replaying search. B reuses frozen Gate5 moments, not a fresh
estimate. No retry or additional candidate is authorized. The published result
is CONDITIONAL_SECTOR_PROOF, so no dedicated post-GO audit or GPU follows.

Public closure and optional private read-only validation:

```sh
python3 "$A/check_artifact.py" --repo "$PWD"
python3 "$A/check_artifact.py" --repo "$PWD" --raw-a "$WORK/a" --raw-b "$WORK/b"   --cache "$CACHE" --data "$DATA"
```

The first is a stdlib scalar/source/gate/ownership check, not a raw-array replay.
The second additionally hashes and checks all saved partials and independently
reconstructs all32 query sector choices from frozen moments and original queries.
Neither reruns the oracle/probe population or any GPU timing.

For native fixtures compile `probe.cpp` with the exact contract flags and run
`native_check.py --library <absolute-library-path>`. Non-optimized Python is
required; original and new assertion/reference checks stay enabled.

Regenerate figures in a **new scratch copy**, not the frozen publication tree:

```sh
test ! -e "$WORK/figure_copy" && cp -R "$A" "$WORK/figure_copy"
python3 "$WORK/figure_copy/plot.py"
```

Plotting overwrites renders and initializes QA as PENDING. Reinspect all renders
before accepting them; SVG metadata can change hashes. Never overwrite the
original audited QA or publication manifest to make a checker pass.
