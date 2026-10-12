# High-dimensional certificate compressibility

**Decision: AXIS_ALIGNED_HIGH_DIM_COMPRESSION_KILLED.** On the frozen GIST/P2 workload, PCA64 L4 keeps only37.03% of point-set-safe pruning; PCA128 L4 keeps32.69%. Both preregistered kill conditions hold. Stage B is NOT_ADMITTED; FP16/INT8/INT4 are not measured.

## Full Stage A matrix

Alignment denominator: pooled original-truth-prunable objects for the six frozen hard queries. Retention denominator: matching pooled point-set-safe objects, not a mean of per-query ratios. All nine dimension/level cells and72 query cells are measured.

| PCA | Level | Point-set alignment | FP32 alignment | Retention | Worst-hard retention | Record bytes |
|---:|---:|---:|---:|---:|---:|---:|
| 32 | L3 | 51.64% | 22.90% | 44.35% | 27.92% | 256 |
| 64 | L3 | 69.63% | 23.05% | 33.11% | 15.50% | 512 |
| 128 | L3 | 84.87% | 23.20% | 27.34% | 10.95% | 1024 |
| 32 | L4 | 66.05% | 30.07% | 45.53% | 35.16% | 256 |
| 64 | L4 | 81.94% | 30.34% | 37.03% | 19.99% | 512 |
| 128 | L4 | 93.18% | 30.46% | 32.69% | 12.41% | 1024 |
| 32 | L5 | 78.44% | 42.59% | 54.30% | 36.63% | 256 |
| 64 | L5 | 91.14% | 43.79% | 48.05% | 19.56% | 512 |
| 128 | L5 | 97.88% | 44.55% | 45.52% | 14.50% | 1024 |

## Canary and loss decomposition

Canary359924, L4/PCA64: point-set alignment44.51%, FP32 alignment8.90%, point-set retention19.99%. This is the fixed canary, not a result-selected worst query.

Primary hard counts: original truth5,995,500, point-set4,912,900, FP321,819,300. Projection loss1,082,600; summary loss3,093,600. These telescope exactly. Quantization loss is unmeasured/null, not zero. Summary loss includes numerical widening and common-margin conservatism, not an isolated pure-geometric attribution.

## Safety and provenance

- Full128D coverage:3,000,000 object memberships /768,000,000 physical endpoint-coordinate checks. Exact prefix slicing proves32/64D coverage too:9,000,000 prefix memberships. Nine physical packed records roundtrip.
-2,664,000 query-prefix-region lower-bound checks; zero original strict-squared false prunes. All72 prior point-set counts, original truth arrays and U* match.
- Independent all-member replay:24 original regions,8,880 object memberships,72 prefix checks; not72 independent regions.
- NumPy1.26.4 remote and2.4.3 local reproduce every count, summary float and full bound array bit-identically.
- Initial run used premeasurement freeze03a7c761d994b430791d60f1c0425cfd6a724dec5b30a457cfdb7535acae4694. After observing the kill, a read-only audit prompted **input hash/receipt binding only**. No arithmetic, estimator, membership or threshold changed. Freezecf777289196dd03e1bfc3163993b0e82eb75db6fb0cabbabae91f93a8d76ee32 covers the complete rerun. Run1/run2 raw arrays, counts and budgets are identical. Both runs are retained privately; initial pins and exact patch are public.
- G5 precision nesting is N/A with only FP32. No quantization success, GPU claim or latency claim is inferred.

## Metadata and logical cost

The records are256/512/1024 bytes at32/64/128D, already16-byte aligned, with no per-record scales/offsets/header/padding. Region totals and all shared terms are in `evidence/metadata_budget.csv`: inherited full basis7,372,800 bytes; physical eight-query128D cache8,192 bytes; active B=1 prefix coordinate cache256/512/1024 bytes. These shared terms are not included in the record-only x-axis.

`cost_proxy.csv` counts standalone level/prefix full-scan metadata bytes,13k+6 directed bound primitives per region,4k query interval primitives,960k query projection updates, and960 times all surviving original objects. No fusion/hierarchy reuse, measured hardware traffic, timing or speedup is implied. The private7.68GB projected cache is an offline oracle input, not a proposed deployment footprint.

## Reproduce

No new Python dependencies: Python, NumPy; matplotlib/pypdf only for figures. Linux execution uses installed `numactl`, `flock`, `timeout` and `nice`. Run from this directory without Python `-O`. Original data/score/cache paths are portable arguments, not embedded device paths. Hash/size pins are in `evidence/INPUT_IDENTITY.json`. Private restricted vectors and large endpoint files are not redistributed.

```sh
python test_safety.py
python test_build_binding.py
python replay.py

# CPU-only Linux: first check active users/processes and select an available CPU/NODE.
# This task-owned lock serializes all phases; no foreign process is signaled.
(
set -eu
exec 9>"$TASK_LOCK"
flock -n 9
run() { timeout 1800s nice -n 10 numactl --physcpubind="$CPU" --membind="$NODE" python "$@"; }
export CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
run build_highdim_aabb.py \
  --cache "$PROJECTED_F64" --scores "$SCORES_F64" --permutation "$PERMUTATION_I32" --out "$BUILD_OUT"
run evaluate_fp32.py \
  --build "$BUILD_OUT" --pointset "$POINTSET_NPZ" --out "$EVAL_OUT"
run validate_independent.py \
  --data "$DATA_F32" --permutation "$PERMUTATION_I32" --cache "$PROJECTED_F64" \
  --build "$BUILD_OUT" --out "$INDEPENDENT_OUT"
) # lock released on success or failure

# Published evidence figures (optional installed paper_style helper).
python plot.py --out "$FIGURE_OUT"
```

For private raw replay add `--raw-build`, `--raw-bounds` and `--pointset` to `replay.py`. All outputs are exclusive-create directories. Source and build-manifest mismatches fail closed.

## Interpretation and next action

Measured: more projected information does not translate into comparable pruning for these independent coordinate boxes. Inference: region shape/cross-coordinate occupancy is a likely limit, because axis-wise enclosure permits coordinate combinations absent from member points. This is **not** a theorem that all finite summaries fail. Stop the low-bit AABB sweep. Before implementing a different summary, run its own nearest-prior-art kill test, then the same-contract cheap retention test. GPU-native value remains unknown.

See `CONTRACT.json`, `SAFETY.md`, `PRIOR_ART.md`, `DECISION.md` and `LEDGER.md`. Four vector figures are bundled in `evidence/figures/highdim_compressibility_evidence.pdf`. No existing paper/Overleaf files were modified.
