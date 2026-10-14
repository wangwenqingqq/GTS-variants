# Reproduction

Use an existing Python3/NumPy/C++17 environment. No dependency installation,
GPU, host configuration, or upstream code execution is required for verification.
Set REPO to this delivery checkout, ARTIFACT to
`$REPO/artifacts/pdx_bond_gpu_realizability_gate4_20261015`, and SCRATCH to fresh
private task-owned scratch. Normal Python is mandatory; never use optimized mode.

```bash
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python3 "$ARTIFACT/verify.py" --repo "$REPO" --out "$SCRATCH/verify"
```

This rebuilds the CPU library, runs four independent fixtures, checks exact
public histograms/gates and every parent/source identity, regenerates CPU scalar
analysis, and verifies NOT_RUN GPU evidence. It does not regenerate actual
32M-pair raw data or run CUDA. Only synthetic host compilation is claimed.

## Optional figure regeneration (external installed helper)

This is **not a standalone checkout plotting command**. It additionally requires
an existing Matplotlib environment and the external installed paper-figures
`paper_style.py` helper. Set FIGURE_STYLE_SCRIPTS to that helper's scripts directory.
Runtime/managed skill source is deliberately not redistributed in this repository.
Without that external helper, inspect the committed CSV/PDF/SVG/PNG instead;
the scalar/fixture verification above does not depend on it.

```bash
PYTHONDONTWRITEBYTECODE=1 MPLCONFIGDIR="$SCRATCH/mpl" \
  python3 "$ARTIFACT/plot.py" --data "$ARTIFACT" --out "$SCRATCH/figures" \
  --style-root "$FIGURE_STYLE_SCRIPTS"
```

The two CPU/source figures have deterministic CSV and vector PDF/SVG plus
400-DPI PNG. No latency/DRAM plot is fabricated. Rendering timestamps can vary;
compare CSV and geometry rather than vector file bytes.

## Separate full-population resource admission

Provision privately the original data and32 full-authority files matching
CONTRACT.json, with the inherited parent REGISTERED.json schema: data,
data_sha256,reference,reference_hashes,qids,radius. Paths are private parameters.
After current CPU/user/memory checks, one nice10 coordinator uses at most four
single-thread workers. Existing datasets and old campaigns are read-only.

```bash
env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 nice -n 10 python3 "$ARTIFACT/run.py" \
  --parent "$PRIVATE_PARENT_REGISTERED" --work "$SCRATCH/population"
python3 "$ARTIFACT/analyze.py" --repo "$REPO" \
  --results "$SCRATCH/population/RESULTS.json" --out "$SCRATCH/analysis"
```

The driver hashes inputs before/after, computes official global FP32 means,
qualifies32×4096 pairs, checks all32M ordered score bits, and stores complete
nominal/guarded dimension arrays privately. It writes a failure before draining
active workers; no new work follows a known failure. CPU wall time is never a
search benchmark. The original raw archive identity is in evidence/RAW_VALIDATION.json.

## GPU is not admitted by this reproduction

GPU source/controller are an uncompiled draft. The first source preflight failed
before GPU work creation. GPU_CONTRACT.json deliberately has
`decision_priority_approved=false`; gpu_campaign.py must fail closed. Do not
change that flag merely to run it. After human confirmation, create an append-only
recovery registration with a fresh current dependency snapshot and confirmed
decision/measurement rules, then qualify and measure one candidate. Source
routing is private; never overwrite old scratch or silently rebind registration.
