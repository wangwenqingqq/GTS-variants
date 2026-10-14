# Reproduce this CPU diagnostic

Checkout this artifact and the exact parent files in CONTRACT.json. Python 3,
NumPy and g++ with OpenMP must already be installed; do not install dependencies
or alter shared services for this diagnostic. Use the Linux host with an already-installed GNU timeout watchdog. Set REPO to the checkout root and
ART=$REPO/artifacts/certificate_sector_packing_gate7_20261014.

Acquire the original GIST1M FP32 file and frozen parent oracle files by their
SHA-256 identities, not by filename alone. Large inputs, packed data, shared
libraries and 256MB candidate proofs are deliberately outside Git. Parents'
S1/C1 saved proofs are needed only for contribution/quality observation.
DATA is the original12-byte-header file; CACHE contains<query_id>.f64 scores.
Use a new task-owned WORK directory for every command; never overwrite old runs.

```sh
export CUDA_VISIBLE_DEVICES=
export OMP_NUM_THREADS=4 OMP_DYNAMIC=FALSE
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
mkdir "$WORK"
timeout 900 nice -n10 python3 "$ART/run.py" --stage training --repo "$REPO"   --data "$DATA" --work "$WORK/training"
timeout 3600 nice -n10 python3 "$ART/run.py" --stage evaluation --repo "$REPO"   --data "$DATA" --cache "$CACHE" --training "$WORK/training"   --work "$WORK/evaluation"
nice -n10 python3 "$ART/analyze.py" --repo "$REPO"   --training "$WORK/training" --evaluation "$WORK/evaluation"   --cache "$CACHE" --s1-raw "$S1_RAW" --c1-raw "$C1_RAW"   --output "$WORK/derived"
python3 "$ART/check_artifact.py" --repo "$REPO"
```

Each training/evaluation invocation uses a nonblocking campaign lock and exclusive
receipt creation. Any population failure stops; no automatic retries. Fixing a
read-only observer uses a fresh output directory and retains original evidence.
Compiler flags prohibit contraction/reassociation; native fixtures must pass
before population execution. The packed-only full audit restores original order.

The public checker independently reconstructs the 1.84 MB W from TRAIN_TOP128.u16,
repeats the specified greedy with a stdlib oracle, and checks the exact integer
and rational gates. It does not generate a second candidate or replay a population.
For a fresh build fixture (not a new benchmark):

```sh
g++ -std=c++17 -O3 -shared -fPIC -fopenmp -fno-fast-math   -ffp-contract=off -frounding-math -fno-associative-math   "$ART/probe.cpp" -o "$WORK/fixture.so"
python3 "$ART/native_check.py" --library "$WORK/fixture.so"
```

Plots require already-installed matplotlib and the local paper_style helper;
no runtime/system skill source is copied into this repository:

```sh
cp -R "$ART" "$WORK/plot-scratch"
python3 "$WORK/plot-scratch/plot.py" --style-helper "$PAPER_STYLE_DIR"
```

Generate plots only in this new scratch copy: plot.py writes figure files and
a fresh PENDING QA receipt. Never replace frozen figures, QA or the publication
manifest in the checkout. The scratch manifest is no longer a release manifest.

For an optional independent input-score audit (no pair-distance replay):

```sh
python3 "$ART/check_artifact.py" --repo "$REPO" --data "$DATA"
```

Stored figures are rendered and checked separately; regenerated PNG/SVG/PDF
metadata need not be byte-identical. Numerical files, permutation and source
hashes must match. No GPU action, fallback or next-stage registration is part
of reproduction. Whole-campaign CPU wall times include full quality audits and
are operational logs only, never a speedup denominator.
