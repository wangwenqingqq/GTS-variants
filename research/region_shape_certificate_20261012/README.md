# Fixed-PCA8 region-shape diagnosis

**Decision: PROJECTED_SHAPE_CERTIFICATE_KILLED.** All three new shapes lose to
the same AABB at every level. More importantly, the optimistic nearest-projected-
point diagnostic limits hard6 alignment to 29.87% at L3 and 39.55% at L4: even an
arbitrarily tight enclosing set in this fixed PCA8 cannot reach the declared 45%
ancestor signal gate. This is not an impossibility claim about other projections,
nonlinear representations, original-space certificates or GPU tree indexes.

## Main result (safe pruned objects / original truth-prunable objects)

| Shape | Aligned bytes/region | Hard6 L3 | Hard6 L4 | Hard6 L5 |
|---|---:|---:|---:|---:|
| AABB, unchanged keeper | 64 | 22.8859% | 29.8107% | 40.4884% |
| Centroid ball | 48 | 0.0000% | 1.3110% | 14.4204% |
| Approximate minimax ball, 64 fixed iterations | 48 | 0.3523% | 5.5091% | 20.9728% |
| Diagonal ellipsoid, metadata-heavy | 80 | 7.9027% | 14.4158% | 30.5855% |
| Projected point-set optimistic ceiling, diagnostic ONLY | Not deployed metadata | 29.8658% | 39.5547% | 51.5538% |

Hard truth-prunable denominators are 5,960,000 / 5,995,500 / 5,999,540 at
L3/L4/L5. All8 denominators and all 96 individual query/shape/level counts are in
`evidence/per_level_summary.csv` and `evidence/per_query_summary.csv`.

The L4 canary359924 is 7.0556% with AABB, 0.3903% with centroid ball, 0.5805%
with approximate minimax ball and 0.8006% with ellipsoid. Its optimistic projected
point-set ceiling is only10.3082%, so a 30% shape rescue is impossible for that
query under this fixed projected Euclidean-enclosure mechanism.

The full hard6 L4 distance-gap sum decomposes into 85.0319% original-to-projected
nearest-distance loss, 14.9681% geometry plus AABB numerical margin, and a tiny
separate projected-error interval width. This uses an additive sum over all
60,000 query-region pairs, NOT a ratio of medians, NOT an alignment percentage,
and NOT runtime attribution. See `evidence/gap_decomposition.csv`.

## What was actually executed

GIST1M, D960, K8, B1, the same eight frozen queries (six hard), same U*, original
ordered RN-FP64 score cache, fixed P2 PCA-balanced memberships and unchanged PCA8
basis/projected coordinates. Four certificates x three levels =12physical cells.
Shared Xeon Gold6530 CPU, one NUMA-local core/one library thread/nice10/bounded
task lock; GPU hidden. No latency, CUDA, ANN, formal256, 10K or index rebuild.

Accepted attempt3 passes all G1–G5: 3M object memberships per shape enclosed,
3,552,000 full bound/truth checks, zero bound violations/false prunes, all24
original AABB query-level bridges, all384 frozen original-vector pairs (128 at
EACH level) independently rebuilt. These cover142,080 object memberships and
135,317 unique original vectors (including the eight queries). The full twelve
48/64/80B metadata records were serialized/reloaded. The independent reference
also reconstructs signed FP32 AABB endpoints, not merely coordinate coverage.
Cross-runtime replay on
Python3.13.12/NumPy2.4.3 reproduced all bounds/counts and the 32-row original-
vector fixture after the original CPU worker used Python3.12.3/NumPy1.26.4.
The safety argument, rather than empirical agreement alone, is in `SAFETY.md`.

The minimax center is approximate, not an exact smallest enclosing ball. Its
witnessed cached half-diameter ratio is a numerical quality proxy, not a certified
approximation ratio. The chosen diagonal ellipsoid is not a minimum-volume or
full-covariance ellipsoid. Enclosures are not necessarily subsets of the AABB;
“different shape” is not automatically “tighter.”

## Evidence and four figures

- `evidence/aggregate_summary.json`: exact integer counts and terminal gate.
- `evidence/SAFETY_VALIDATION.json`, `G5_VALIDATION.json`: full and independent gates.
- `evidence/INPUT_IDENTITY.json`, `SOURCE_FREEZE.json`, `OUTPUT_MANIFEST.json`:
  frozen inputs/sources and hashes of all retained private raw results.
- `evidence/dead_space_summary.csv`: median/p90/p99, bounds stronger than AABB,
  both newly gained AND lost pruning, with full query-region denominators.
- `evidence/region_shape_stats.csv.gz`: all111,000 regions, aggregate geometric
  statistics/scales only; no original vectors or projected centers.
- `evidence/region_shape_stats.csv`: summary quantiles of those region statistics.
- `evidence/projected_oracle_summary.csv`, `projected_oracle_per_query.csv`,
  `gap_decomposition.csv`: auxiliary fixed-projection diagnostic, not a candidate.
- `evidence/figures/region_shape_evidence.pdf`: four vector pages, with PNG previews.

Figure1: all new shapes reduce hard6 certifiability; the dotted45% gate applies
only to ancestors L3/L4. Figure2: all60,000 hard6 L4 query-region pairs show larger
dead-space gaps for the replacements (4097 equally spaced empirical CDF ranks
per shape, no invented confidence bands). Figure3: no L4 hard-query rescue;
canary359924 is explicitly marked. Figure4: actual record bytes versus alignment;
80B ellipsoid is outside the64B matched-budget set, not an equal-budget win.
All four PDF pages and final-size 600DPI crops are visually verified.

## Reproduction

Run from the repository root with Python and NumPy. Public artifacts suffice for
integer gates, source pins, exact matrix proof and synthetic arithmetic fixtures:

```sh
H=research/region_shape_certificate_20261012
python "$H/test_shape_safety.py"
python "$H/replay.py"
```

Full replay requires the pinned original fixtures/caches retained outside Git.
Construction/evaluation/full G5 workers require Linux (`sched_getaffinity` and
`/proc/cpuinfo`) plus installed numactl, flock, timeout and nice. Portable public
count/arithmetic replay works without those Linux-only worker interfaces.
Set DATA, PROJECTED, SCORES, PERM and OLD to their matching input identities in
`evidence/INPUT_IDENTITY.json`. PROJECTED has N x16FP64 entries, PCA8 columns8:16;
PERM is the unchanged P2 int32 permutation, OLD its original PCA8 region NPZ.
OUT is a new scratch directory. Preserve any old run; all output directories
and receipt files are created exclusively rather than silently overwritten.
Use a locally admitted single CPU core and its NUMA node; do not signal jobs.
Set CPU and NODE after local preflight. The lock parent directory must exist.

```sh
export CUDA_VISIBLE_DEVICES= OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$OUT"
cpu_run() {
  numactl --physcpubind="$CPU" --membind="$NODE" nice -n10 \
    flock -n "$OUT/cpu.lock" timeout 900s python "$@"
}
cpu_run "$H/build_shapes.py" --data "$DATA" --projected "$PROJECTED" --scores "$SCORES" \
  --permutation "$PERM" --old "$OLD" --out "$OUT/build"
cpu_run "$H/evaluate_shapes.py" --build "$OUT/build" --projected "$PROJECTED" \
  --permutation "$PERM" --scores "$SCORES" --out "$OUT/eval"
cpu_run "$H/validate_g5.py" --data "$DATA" --projected "$PROJECTED" \
  --permutation "$PERM" --build "$OUT/build" --out "$OUT/g5"
python "$H/replay.py" --build "$OUT/build" --eval "$OUT/eval" \
  --bridge "$OUT/g5/bridge_vectors.npz"
```

Figure regeneration additionally needs installed Matplotlib and pypdf. The
portable native-style path does not require the optional external style helper:

```sh
python "$H/plot.py" --out "$OUT/figures"  # New directory; no overwrite.
```

Accepted-worker raw NPZs, full packed metadata, original-vector fixture and
attempts1/2 remain private and hash-manifested; public release is not a claim that
those restricted inputs can be reproduced without obtaining the pinned fixtures.
Public CSV line endings are normalized to LF without changing any cell; raw
worker CSV byte hashes remain unchanged in OUTPUT_MANIFEST, with the release
conversion recorded in `evidence/CURATION.json` and PUBLISH_MANIFEST.
PCA/basis/partition provenance remains in the preceding checked-in campaigns.
No changes to the paper/Overleaf, default branch, other campaigns or GPU jobs.

## Research decision

Keep P2/PCA8 AABB as the comparator. Do not start a GPU implementation of these
three replacements: neither pure geometry nor matched-budget promotion passes.
Reopen only for a mechanism that escapes this fixed projected-distance ceiling,
or a different clearly frozen projection/quality contract; do not rebrand known
ball/ellipsoid geometry as novelty. See `DECISION.md`, `LEDGER.md`, `PRIOR_ART.md`.
