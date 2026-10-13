# Reproduce the CPU Gate0 artifact

No GPU runtime is imported. Requirements used: Linux x86-64, installed g++ 13.3.0
with OpenMP, Python 3.12.3, NumPy 1.26.4. Matplotlib is needed only for figures.
No package installation or framework is part of this artifact.

## Public checks (no restricted data)

From the repository root:

```sh
ART=artifacts/progressive_lossless_gate0_20261013
python3 "$ART/check_artifact.py"
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
# Use a new temporary directory. Build flags come from the immutable contract.
BUILD=$(mktemp -d)
export BUILD
(cd "$ART" && python3 -c 'import os; from pathlib import Path; from run import build; print(build(Path(os.environ["BUILD"]) / "lossless.so"))')
python3 "$ART/test_format.py" --library "$BUILD/lossless.so"
python3 "$ART/plot.py"
```

Build/test output is not a repeat of the full database replay or a GPU result. Regenerating figure files
requires rebuilding the publication manifest before claiming that modified copy
matches the committed manifest. Do not edit the registered measurement sources.

## Exact database replay (private inputs required)

Obtain the original dataset independently, not from this repository. It must have
SHA-256 `f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7`, a
12-byte `<iii>` header `(960,1000000,2)`, then row-major original FP32 coordinates.
`REFERENCE_CACHE` must contain the Gate2 ordered-FP64 score files named
`<query_id>.f64`; each is 8,000,000 bytes. The 32 hashes are frozen in the parent
identity and checked before and after search. No public raw input license or
redistribution right is inferred from hashes. Access to those private inputs is
required for this full replay; public scalar checks cannot substitute for it.

```sh
export CUDA_VISIBLE_DEVICES="" OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
export OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
ART=artifacts/progressive_lossless_gate0_20261013
# DATA, REFERENCE_CACHE and WORK are user-supplied paths. WORK must not exist.
timeout --signal=TERM 1800s nice -n 10 python3 "$ART/run.py" \
  --data "$DATA" --cache "$REFERENCE_CACHE" \
  --parent-identity artifacts/progressive_gpu_gate2_20261013/evidence/INPUT_IDENTITY.json \
  --work "$WORK"
```

This launches exactly one bounded population process: hash checks, CPU build,
corner fixtures, one query-independent encoding, whole-database recovery, first4096
qualification for every query, then all 32 x 1M pairs. Failure preserves a receipt
and stops; an existing work directory is not reused or altered. The candidate
function receives only layer pointers and the full query. During the formal
32 x 1M replay, oracle files are opened for validation after candidate search
returns. The first4096 qualification maps its oracle slice beforehand, but never
passes any oracle pointer to candidate search. The encoded file's hash,
original dataset, references and registered source hashes are rechecked at closure.

Fresh scalar curation needs an empty output tree containing the same contract and
four registered measurement sources; `analyze.py --private "$WORK" --root "$OUT"
--repo "$REPO"` uses exclusive output writes. Do not overwrite the historical
published observation with a reproduction. Raw arrays and the 3.84 GB encoded
source remain outside Git; their identities are in evidence/RAW_MANIFEST.json.
Public registration removes the process ID; if a private environment receipt is
supplied as `ENVIRONMENT_PRIVATE.json`, only required software/numeric and per-run
worker fields are retained. `evidence/CURATION.json` bridges raw and public hashes;
the original receipts are not edited. Administrative placement, host topology and
unused device configuration must remain private.

## Read-only private evidence audit

```sh
nice -n 10 python3 "$ART/check_artifact.py" \
  --raw "$WORK" --cache "$REFERENCE_CACHE"
```

The optional audit checks all saved terminal widths, visited lower bounds, final
score bits, and complete member IDs against unchanged reference files. It neither
calls the candidate nor generates a new population observation.

Gate0's threshold precedence is recorded in CONTRACT.json. Only GO could admit a
new frozen GPU campaign. This recorded run is NO-GO; Gate1 must not be inferred,
auto-started, or tuned from it.
