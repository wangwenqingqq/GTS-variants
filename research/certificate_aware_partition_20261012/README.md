# Fixed-certificate partition causal test

**Result: PARTIAL_CO_DESIGN_SIGNAL.** Changing balanced membership improves PCA
certifiability, but misses the 60% ancestor / 30pp original-control gate. No GPU
implementation is admitted. See [decision and exceptions](DECISION.md),
[predeclared contract](CONTRACT.json), [prior-art gate](PRIOR_ART.md) and
[ledger](LEDGER.md). Base: `a7af442546370f0b1f048bb7cee715888b91719c`.

## Evidence entry points

- `evidence/aggregate_summary.json`: all 18 primary PCA-only cells and decision.
- `evidence/per_query_partition_summary.csv`: all 144 query/partition/level/C4-C8 rows.
- `evidence/P0_NATIVE_BRIDGE.json`: separate exact old native+PCA reproduction.
- `evidence/leave_660835_out.csv`, `HARD_QUERY_SUMMARY.json`: exception sensitivity.
- `evidence/region_contamination.csv`: all retained-region counts at U/1.05U/1.10U.
- `evidence/COMPACTNESS.json`: mean widths and mean/p50/p90 diagonals.
- `evidence/PARTITION_AUDIT.json`, `CERTIFICATE_VALIDATION.json`: G1–G4.
- `evidence/INPUT_IDENTITY.json`, `SAMPLES.json`, `RAW_MANIFEST.json`: provenance.
- `evidence/BUILD_RECEIPT.json`: construction substep costs, not query latency.
- `evidence/figures/partition_evidence.pdf`: four vector pages.

Figure captions (one message each):
1. Geometry-aware assignment improves fixed-box alignment but misses the absolute
   promotion threshold; 8M-pair deterministic counts, no population confidence intervals.
2. Exact original-distance truth remains very selective while most objects remain
   after the PCA-only certificate; each level is a separate counterfactual.
3. All six original hard queries improve, but several remain weak; 1M-pair per-query
   denominators, fixed PCA8 and frozen hard-query selection.
4. A retained region still mostly contains far objects under P2. Every d<=U
   observation is shown; boxes summarize finite observations, not uncertainty.
   Whiskers use1.5IQR; dotted line is one near object per region. Axis is logarithmic.

## Reproduction

Python without `-O`, installed NumPy, no new dependencies for construction/counts.
Plots additionally use Matplotlib and pypdf. Linux worker: CPU affinity count1,
BLAS/OMP/MKL threads1, nice>=10, empty CUDA_VISIBLE_DEVICES. Source/input identities
must match the checked-in freeze; do not refit the PCA basis.

Supply private paths through variables; do not put device paths in public files.
Large inputs and derived raw arrays are intentionally outside Git. Required hashes,
byte lengths and ordered score/coordinate contracts are published. `DATA` is the
original header+FP32 vectors; `INDEX` the original GTS index; `SCORES` the unchanged
8x1M ordered FP64 score cache; `PROJECTED` is the exact prior1Mx16 FP64 coordinate
file (PCA columns8:16). `ANCESTORS` and `PRIOR_INTERVALS` are the frozen prior
artifacts pinned in INPUT_IDENTITY. Existing prior campaign source regenerates
these inputs; original data access remains a prerequisite, not bundled here.

```sh
TASK=research/certificate_aware_partition_20261012
python "$TASK/test_partition.py"
# Acquire an owned CPU advisory lock and bind an admitted CPU core outside Python.
# Freeze already exists at $TASK/evidence. For a new ordinal replay, use a fresh path:
# python "$TASK/freeze.py" --out "$NEW_FREEZE"
env CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  numactl --physcpubind="$CPU" --membind="$NUMA" nice -n10 \
  flock -n "$OWNED_LOCK" timeout 600s python "$TASK/build.py" \
  --data "$DATA" --index "$INDEX" --scores "$SCORES" --projected "$PROJECTED" \
  --ancestors "$ANCESTORS" --prior-intervals "$PRIOR_INTERVALS" \
  --freeze "$TASK/evidence" --out "$NEW_RUN"
python "$TASK/evaluate.py" --freeze "$TASK/evidence" --run "$NEW_RUN" \
  --ancestors "$ANCESTORS" --out "$NEW_EVALUATION"
python "$TASK/replay.py" --freeze "$TASK/evidence" --run "$NEW_RUN" --out "$NEW_REPLAY"
python "$TASK/plot.py" --evidence "$NEW_EVALUATION" --out "$NEW_FIGURES"
```

Optional NEW_FREEZE regeneration requires restoring prior ancestors to
`research/certificate_compression_20261011/local/stageA2/ancestors.npz` and prior
intervals to `research/projection_certificate_20261011/local/run4/intervals.npz`.
The admitted build/evaluate reproduction uses the committed freeze and explicit
input arguments, and does not require that layout.

Every output path must be fresh. Metadata records remain32/64B without hidden
padding; basis/cache storage is charged separately in the CSV. No native bound
is transplanted into P1/P2. Build functions do not consume labels, queries or U;
validation subsequently reads those frozen values. CPU timings are resource
observations, not latency comparisons and have no repeated-run CI.

The hard-query JSON is reproducible directly from the per-query CSV: for each
partition and level, select PCA8 and the six CONTRACT.hard_queries, sum both
remaining-object columns and compute `(6000000-remaining)/(6000000-truth)`.
Publication manifest excludes itself; raw evidence hashes identify omitted large
artifacts. The baseline repository/license/history remain unchanged. No paper
text, main branch, submission, GPU settings or foreign process is changed.
