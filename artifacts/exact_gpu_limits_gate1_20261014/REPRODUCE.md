# Reproduction and evidence boundary

Use the existing repository at the delivery commit. No package installation,
hooks, GPU, raw-data redistribution, or manuscript update is required.
All output paths below must be fresh task-owned scratch, not this artifact.
Set `REPO` to the checkout, `ARTIFACT` to
`$REPO/artifacts/exact_gpu_limits_gate1_20261014`, and `SCRATCH` to a new private
task directory. Run normal Python, never `-O`, `-OO`, or `PYTHONOPTIMIZE`.

## Public scalar reconstruction, fixtures, and immutable-subset verification

Requirements: Python3, existing NumPy, and an existing C++17 compiler.

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python3 "$ARTIFACT/verify.py" --repo "$REPO" --out "$SCRATCH/verify"
```

This checks every public file and parent dependency, binds executed source
identities, reconstructs complete-population histograms and exact gates, rejects
optimized Python and reused output directories, and builds/runs four independent
CPU numerical fixtures plus three algebraic tests. It does **not** recompute the
32M raw-vector diagnostic. The regenerated ANALYSIS provenance hash necessarily
refers to public SCALARS rather than the private result carrying diagnostic wall
times; all decision values and other reconstructed JSON must be identical.

## Recreate all figures

Use an already installed Matplotlib/NumPy environment. The runtime-owned
paper-figures skill remains external and is not copied into the repository.
Pass its scripts directory explicitly if not in the normal installed location.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 "$ARTIFACT/plot.py" \
  --data "$ARTIFACT" --out "$SCRATCH/figures" \
  --style-root "$FIGURE_STYLE_SCRIPTS"
```

The four figures have deterministic CSV data and PDF/SVG/400-DPI PNG outputs.
Vector metadata timestamps may differ; compare data and rendered geometry,
not file hashes from a fresh plotting runtime. SVG normalization removes only
trailing XML whitespace. No measured uncertainty is invented for a full finite
population or an algebraic plane.

## Recompute the full population (separate resource admission)

Provision the data and all32 authoritative score files privately, matching
CONTRACT.json. The parent REGISTERED.json schema is the one produced by
the previous exact-representation Gate1: `data`, `data_sha256`, `reference`,
`reference_hashes`, `qids`, and `radius`. Paths are resolved by that private
registration, not embedded in this public artifact. It must identify the same
12-byte header, N1M/D960 FP32 data, radius bits, query order, and score hashes.

After checking current CPU load, active users and memory, run one coordinator with at most
four low-priority single-thread query workers. Keep every preexisting process
and old campaign unchanged. The original run used128 logical CPUs, low load,
Python3.12.3/NumPy1.26.4 and g++13.3.0. CPU duration is not a search benchmark.

```bash
env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 nice -n 10 python3 "$ARTIFACT/run.py" \
  --parent "$PRIVATE_PARENT_REGISTERED" --work "$SCRATCH/population"
```

The driver hashes every input, runs fixtures and32x4096 bounded qualification,
then evaluates all32M pairs exactly once and rehashes inputs. Per-pair arrays,
orders, build records and the complete result remain private. A failed input,
numerical or provenance check stops with a retained failure, without automatic
retry. The original private raw archive has a published hash, not public data.

Known failure-path limitation of the immutable executed driver: after the
coordinator observes a failed worker future it submits no further query, but
already in-flight task-owned queries may finish while the process pool drains.
FAILURE.json is written after that drain, so peer stop-file checks are not
immediate cancellation. No such failure occurred in this completed run. Do not
claim strict cross-worker fail-fast behavior; a future campaign needing it must
fix and freeze a new driver version rather than rewrite this executed source.

```bash
python3 "$ARTIFACT/analyze.py" --repo "$REPO" \
  --results "$SCRATCH/population/RESULTS.json" --out "$SCRATCH/analysis"
python3 "$ARTIFACT/report.py" --repo "$REPO" \
  --data "$SCRATCH/analysis" --out "$SCRATCH/report"
```

No command in this artifact admits a kernel, GPU validation, new ordering
policy, update workflow, batching execution or paper after the NO_GO decision.
