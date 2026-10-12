# Fixed-partition projection-capacity diagnosis

**Primary L4 decision: CAPACITY_LIMITED.** PCA64 complete point sets recover
81.9431% guaranteed hard6 exclusion alignment, with44.5056% worst hard alignment,
passing both70%/40% conditions. But L3 needs the tested128D prefix to pass70%:
its64D alignment is69.6309%, not a pass rounded to70%. L5 first reaches70% at32D,
and passes the joint hard/worst capacity gate at64D. All levels are retained.

This establishes information availability on the frozen projected point sets,
NOT cheap compression into64B/128B metadata, a deployable certificate, a novel
representation, a better search objective or a GPU/system speedup.

## Main result

Guaranteed safe-pruned object-query memberships / original truth-prunable
object-query memberships. Hard6 denominators at L3/L4/L5 are5,960,000 /5,995,500 /
5,999,540. Explained variance is a separate full-database spectrum statistic.

| k | Hard6 L3 | Hard6 L4 | Hard6 L5 | Canary359924 L4 | Variance |
|---:|---:|---:|---:|---:|---:|
| 8 | 29.8658% | 39.5413% | 51.5420% | 10.3082% | 47.9038% |
| 16 | 39.2617% | 52.4994% | 66.5504% | 14.8719% | 58.3662% |
| 32 | 51.6443% | 66.0529% | 78.4415% | 20.9668% | 67.5946% |
| 64 | 69.6309% | 81.9431% | 91.1423% | 44.5056% | 77.3951% |
| 128 | 84.8658% | 93.1816% | 97.8763% | 74.5997% | 86.3824% |
| 256 | 95.3356% | 98.6807% | 99.7842% | 95.7466% | 93.5699% |
| 512 | 99.4295% | 99.9016% | 99.9888% | 99.7898% | 98.3307% |
| 960 | 100.0000% | 100.0000% | 100.0000% | 100.0000% | 100.0000% |

The canary359924's L4 denominator is999,200; at64D it certifies444,700 memberships.
At128D its alignment is74.5997%, versus10.3082% at8D. It is not assumed to be the
minimum hard query at every dimension. Exact all8/hard6/per-query counts, optimistic
possible counts, arithmetic-ambiguous pairs, central-proxy false classifications
and projection-induced false survivors are retained for all192cells.

## Dimension thresholds and scope

| Level | K50 hard | K70 hard | K90 hard | Protocol decision |
|---|---:|---:|---:|---|
| L3 | 32 | 128 | 256 | MODERATE_CAPACITY_REQUIREMENT |
| L4 | 16 | 64 | 128 | CAPACITY_LIMITED |
| L5 | 8 | 32 | 64 | CAPACITY_LIMITED |

These are **first measured grid points**, not minimum dimensions among untested
prefixes. Per-query k30/k50/k70/k90 and possible/guaranteed thresholds are in
`evidence/per_query_dimension_thresholds.csv`. Both arithmetic brackets give the
same listed hard thresholds; no threshold bucket is selected from an ambiguous
interval. PrimaryL4 was declared before measurement; L3/L5 are not averaged away.
All D1-D4 predicates and any overlaps remain in `aggregate_summary.json`.

D1 -> D3 -> D2 -> D4 precedence was frozen: a canary directional bottleneck would
outrank a pooled moderate-capacity label. The labels are protocol buckets, not an
intrinsic-dimension estimate or evidence that an unmeasured objective is superior.

## What was executed and validated

Same GIST1M x960 FP32, K8/B1, eight original frozen queries/six hard, U*, ordered
RN-FP64 original scores/truth and unchanged P2 PCA-balanced L3/L4/L5 membership.
Full covariance uses all1M rows (8192-row blocks); one complete960x960 PCA fit,
one common contraction scalar, eight nested prefixes. No query label/U* conditions
fitting; the query IDs are ordinary database rows. Cache stores uncentered linear
coordinates; translation cancels in point distances, while covariance is centered.

CPU only: one NUMA-local Xeon Gold6530 core, one BLAS thread, nice10, task lock,
bounded1800s phases, GPU hidden. Build/accumulation costs are resource accounting,
not deployable query latency. `COST_ACCOUNTING.json` records fit CPU/wall time,
7.68GB cache, logical operations/reductions and process peak RSS.

Accepted source2 passes all192cells, all7,104,000 dimension/query/region own-truth
checks, full raw-distance/lower/upper/mask monotonicity and zero false prunes.
Signed directed Gram intervals certify the actual full matrix contraction and
near-isometry; every prefix is a row subset of that common matrix. At960D all
three levels match original truth classifications and100% alignment, but distances
are NOT bit-identical: maximum absolute difference9.73e-12. Original score contract
remains the endpoint, not silently replaced by BLAS/PCA arithmetic.

Independent24 original-region pairs use ALL8,880 member objects (8,888 unique
original vectors including queries); separate ordered projection/prefix/scalar
arithmetic checks192prefix cells. Original squared truth is bit-identical. BLAS
versus ordered coordinates differ by at most5.11e-15, within the proved envelope;
no bit-identical BLAS claim. The private fixture row count is recorded exactly in
`CROSS_RUNTIME_REPLAY.json`, not assumed from the earlier campaign.

Cross-runtime replay recertifies the stored full matrix, all7,104,000 bounds/masks
and24 original-vector fixture rows on Python3.13.12/NumPy2.4.3 versus worker
Python3.12.3/NumPy1.26.4. Five primary CSVs and aggregate decisions are byte-identical;
51 descriptive FP64 sum/quantile cells differ by at most4ULP (2.33e-10 absolute),
disclosed in POSTPROCESS_REPLAY. Canonical worker statistics remain unchanged.

The previous PCA8 also used full1M covariance. Current one-thread fit/common full
scaling/BLAS numerical path differs from its four-thread/top8-scaled/ordered path.
`PCA8_CONSTRUCTION_BRIDGE.json` and `PCA8_HISTORICAL_BRIDGE.json` disclose this;
the historical oracle is a separate reference, NOT a bitwise8D anchor. These
arithmetic contracts yield different possible-ceiling counts; no isolated
margin-only attribution is claimed.

## Evidence and four figures

- `aggregate_summary.json`,192-row `per_query_capacity.csv`,24-row `per_level_capacity.csv`.
- `PCA_SPECTRUM.json`, `PCA_PREFIX_MANIFEST.json`, `basis.f64`, `MATRIX_PROOF.json`, `ARITHMETIC_PROOF.json`.
- `MONOTONICITY_VALIDATION.json`, `INDEPENDENT_VALIDATION.json`, `SAFETY_VALIDATION.json`.
- `projection_loss_summary.csv`: all8/hard6 median,p90,p99,signed sums at every k/level;
  negative central gaps are retained. Envelope-based RN sums are descriptive, not
  certified summation intervals or an alignment-gap/runtime attribution.
- `threshold_crossings.csv`: marginal gains and gains per added dimension.
- `INPUT_IDENTITY.json`, `SOURCE_FREEZE.json`, `OUTPUT_MANIFEST.json`: pinned
  inputs/source and retained raw private artifacts, including the7.68GB cache.
- `figures/projection_capacity_evidence.pdf`: four vector pages. Capacity curves,
  all6 hard-query curves, variance/certifiability in separate panels, and projection
  loss median/p90. Only measured arithmetic bands, no invented population CI.

## Reproduction

Portable public gates require installed Python and NumPy:

```sh
H=research/projection_capacity_diagnosis_20261012
python "$H/test_monotonicity.py"
python "$H/replay.py"            # Counts, source pins and arithmetic assumptions.
python "$H/replay.py" --matrix   # Recompute full stored Gram intervals.
```

Full replay additionally requires the pinned restricted original data/P2/scores.
Linux worker uses sched_getaffinity/proc CPU metadata, installed numactl/flock/nice/
timeout. Set DATA/SCORES/PERM/OLD to `INPUT_IDENTITY.json`, and CPU/NODE from local
preflight. OUT must be a new task scratch; preserve old runs. One thread only:

```sh
export CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$OUT"
cpu_run() { numactl --physcpubind="$CPU" --membind="$NODE" nice -n10 \
  flock -n "$OUT/cpu.lock" timeout 1800s python "$@"; }
cpu_run "$H/build_full_pca.py" --data "$DATA" --out "$OUT/build"
cpu_run "$H/compute_prefix_oracle.py" --build "$OUT/build" --scores "$SCORES" \
  --permutation "$PERM" --old "$OLD" --out "$OUT/oracle"
cpu_run "$H/validate_independent.py" --data "$DATA" --permutation "$PERM" \
  --build "$OUT/build" --oracle "$OUT/oracle" --out "$OUT/independent"
python "$H/analyze_capacity.py" --build "$OUT/build" --oracle "$OUT/oracle" --out "$OUT/analysis"
```

Public release count replay reads accepted evidence. A rerun emits a NEW analysis
directory; compare its counts with the accepted evidence rather than overwriting
it. A regenerated full eigensystem can differ in floating bytes; preserve its own
proof/cache identities and compare under the declared numerical contract. Optional
replay --raw/--bridge flags apply to hash-matching accepted private artifacts; do
not substitute a regenerated basis/cache silently into that replay. Figures
use installed Matplotlib/pypdf; no managed style code is copied into this repo:

```sh
python "$H/plot.py" --out "$OUT/figures"  # New directory, no overwrite.
```

## Next decision

Prioritize an independently novel information-compression test targeting the
existing64D/128D information. Treat the unchanged original truth/P2 as the keeper;
require safe fixed-budget representations to retain enough of this ceiling.
Do not claim64D point-set capacity proves a64B certificate. Do not start GPU or
latency work based on this offline curve alone. No Overleaf/default-branch/old
campaign/foreign GPU changes are part of this task.
