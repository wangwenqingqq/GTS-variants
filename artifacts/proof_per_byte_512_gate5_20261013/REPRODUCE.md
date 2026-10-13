# Reproduction

Python 3 with NumPy, Linux g++ with OpenMP, and the unchanged private inputs are
required for full reproduction. No CUDA library, new dependency installation,
framework or alternate layout is needed. The scalar checker uses only stdlib;
plotting optionally uses existing Matplotlib. Do not start the populations on a
shared host before verifying CPU/memory/disk admission and existing processes.

From the repository root, set `DATA` to the original file whose hash is in
`CONTRACT.json`, `CACHE` to the 32 frozen `<query_id>.f64` score files, and
`WORK` to a **new task-owned scratch directory**. Preserve prior runs; no retry or
automatic resume is part of this contract. The dataset header is three little-endian
int32 values `(960,1000000,2)`, followed by 3.84 GB of original FP32 values.

```sh
A=artifacts/proof_per_byte_512_gate5_20261013
unset PYTHONOPTIMIZE
export CUDA_VISIBLE_DEVICES="" PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir "$WORK"
timeout --signal=TERM 3600s nice -n 10 python3 "$A/run.py" --stage A \
  --data "$DATA" --cache "$CACHE" --repo "$PWD" --work "$WORK/a"
```

Inspect `a/RESULTS.json`. **Only STRONG_HEADROOM**, zero numerical-boundary pairs
and all quality gates permit this one next population:

```sh
timeout --signal=TERM 1800s nice -n 10 python3 "$A/run.py" --stage B \
  --stage-a "$WORK/a" --data "$DATA" --cache "$CACHE" --repo "$PWD" --work "$WORK/b"
nice -n 10 python3 "$A/analyze.py" --stage-a "$WORK/a" --stage-b "$WORK/b" \
  --cache "$CACHE" --output "$WORK/scalars"
```

The observer hashes and verifies the saved arrays without invoking candidate
search. `analyze.py` also carries the published, source-identified routing audit
when the reproduced result is GO. The human novelty judgment is documentary
evidence, not an automatically established absence proof. Raw arrays, source
PDFs and deployment placement stay outside Git.

Public closure checks, from the repository root:

```sh
python3 "$A/check_artifact.py" --repo "$PWD"
python3 "$A/check_artifact.py" --repo "$PWD" \
  --raw-a "$WORK/a" --raw-b "$WORK/b" --cache "$CACHE"
```

The first command checks scalar conservation, exact parent identities, registered
measurement-source hashes, gate precedence, per-query distributions, index
ownership and moment bytes. The second additionally verifies all saved partials
against frozen full scores. It does not recompute O1 selection or remeasure GPU
traffic. Original live proof arrays and their hashes are retained privately.

For native fixtures alone, build `probe.cpp` using the exact flags in the contract
and run `test_probe.py --library <absolute-library-path>`. The qualified target
binary hash is recorded under `evidence/A/BUILD.json`. Clean-copy build and
qualification are separate from the original population evidence.
Use ordinary, non-optimized Python for the native fixture script: its reference
assertions must remain enabled. Do not run it with `-O` or `-OO`.

Regenerate figures only in a new scratch copy, not the frozen publication tree:

```sh
test ! -e "$WORK/figure_copy" && cp -R "$A" "$WORK/figure_copy"
python3 "$WORK/figure_copy/plot.py"
```

Plotting overwrites figures and initializes its own visual QA as `PENDING`.
Complete render inspection before accepting regenerated figures. Render metadata
may change SVG/PNG hashes; these are not expected to reproduce the publication
manifest byte-for-byte. Do not replace the original audited QA receipt.
