# Initial-only PCA4 projected box: NO_GO_PROJECTED_BOX

**Stop this PCA-4 box route.** It keeps **74.4102% / 75.1266%** of blocks,
worse than GLOBAL4 **68.8995% / 67.8749%** despite being better than single
LOCAL_BALL. Independent scalar reconstruction passes with zero false prune.
This is an offline CPU selectivity test, **not an end-to-end speed result**.

- GIST **N=1,000,000 / D=960 / FP32 L2 / B1**, two fixed snapshots.
- Original 32 queries/snapshot, radius bits `0x3f34a3d8`, duplicate occurrences independent.
- Fixed **4096 S1/P2 blocks of 244/245 objects**; not the old 4167-block update layout.
- One centered full-initial PCA4 fit; same stored FP64 axes for both snapshots; uncentered linear projections for boxes.
- Baseline `b3ac5ed66e81152a021c9692b4e57ee5cbc16953`; no direction variants.
- Linux x86-64, Python3.12.3/NumPy1.26.4/GCC13.3.0/OpenBLAS0.3.26, actual backend hashes and four BLAS threads retained.
- CPU OpenMP maximum4 and nice15 (sampled in registration); no GPU/clock/power/service operations or dependency install.

## Inspect the evidence

[Five-question decision](DECISION.md) | [claim boundaries](CLAIM_EVIDENCE.md) |
[frozen contract](CONTRACT.json) | [numerical safety](NUMERICS.md).

- [Summary comparison and per-query wins](query/SUMMARY_COMPARISON.md), [all 64 rows](query/SUMMARY_COMPARISON.json), [tails](query/ROBUSTNESS.md).
- [Cost class and survivor work](query/COST_PROXY.md): four dots plus one max reduction, FP64 directions and endpoint reads are fully distinguished from pivot distances.
- [PCA resource accounting](directions/PCA_RESOURCES.md), [frozen directions](directions/PCA_DIRECTIONS.json), [exact represented-Gram proof](directions/DIRECTION_PROOF.json).
- [Box statistics](summary/PROJECTED_BOX_STATS.md) and [8192 scalar block records](summary/PROJECTED_BOX_STATS.json).
- [Immutable execution proof](evidence/PROOF.json), [fresh O0 scalar verification](evidence/VERIFY.json), [byte-preserved curation](evidence/CURATION.json).

## Figure messages

1. [Summary survival](figures/summary_survival.pdf): PCA4 box improves on the failed ball but still misses GLOBAL4 and the 50% mean target (dashed).
2. [Per-query box vs GLOBAL4](figures/projected_vs_global.pdf): most queries regress, with ten exceptions; diagonal is equal survival.
3. [Oracle gap](figures/oracle_gap.pdf): many queries still retain thousands of unnecessary blocks.

Each plot has vector PDF, 300-DPI PNG and exact CSV. Means and linear quantiles
are descriptive over the fixed query set, without fabricated timing confidence
intervals. Every summary uses the same 4096-block denominator. Overlapping
scatter points are retained individually in CSV. ORACLE is not online available.

## Reproduction and non-standalone inputs

Use a full repository checkout; sibling artifacts supply interval/reference
semantics, partition checks and prior input/receipt bindings. CPU experiments
need existing g++/OpenMP/Python/NumPy; no installer is run. PCA training requires
the pinned Linux/OpenBLAS backend; arbitrary-backend direction bit equality is
not promised. The stored direction matrix round-trips exact FP64 values.

```sh
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
ART=artifacts/projected_box_certificate_20261011
python3 "$ART/audit.py"
: "${PROJECTION_LIB:?fresh external .so path}"
g++ -std=c++17 -O3 -fno-fast-math -ffp-contract=off -fopenmp -shared -fPIC \
  "$ART/project.cpp" -o "$PROJECTION_LIB"
python3 "$ART/test_box.py" --library "$PROJECTION_LIB" -v

# PART/PART_VERIFY: retained frozen S1/P2 raw run and its VERIFY.json.
# PRIOR/PRIOR_VERIFY: retained pivot-score raw run and its VERIFY.json.
# INPUTS: qualified resolver records with physical data paths and original qids.
# MAINT: occurrence arrays; REFS: complete ordered-FP64 references/snapshot.
# BALL: a flat external receipt dir containing raw PROOF.json, VERIFY.json,
#       SUMMARY_COMPARISON.json from the prior ball campaign (exact pinned hashes).
# OUT: fresh external parent, run/ and verification/ absent.
: "${PART:?}" "${PART_VERIFY:?}" "${PRIOR:?}" "${PRIOR_VERIFY:?}"
: "${INPUTS:?}" "${MAINT:?}" "${REFS:?}" "${BALL:?}" "${OUT:?}"
mkdir -p "$OUT"
nice -n 15 python3 "$ART/experiment.py" --partition "$PART" --partition-verify "$PART_VERIFY" \
 --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" --inputs "$INPUTS" \
 --maintenance "$MAINT" --references "$REFS" --ball "$BALL" --output "$OUT/run"
nice -n 15 python3 "$ART/verify_box.py" --partition "$PART" --partition-verify "$PART_VERIFY" \
 --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" --inputs "$INPUTS" \
 --maintenance "$MAINT" --references "$REFS" --ball "$BALL" --run "$OUT/run" --output "$OUT/verification"
python3 "$ART/curate.py" --run "$OUT/run" --verify "$OUT/verification/VERIFY.json" --output "$OUT/curated"
# Regenerate plots/tables in a disposable complete checkout before resealing a new delivery.
python3 "$ART/report.py"
```

Raw coordinates, references, frozen permutations, projection/covariance arrays
and binaries stay outside Git, with hashes in PROOF. They require the preceding
qualified campaigns; the artifact does not promise rebuilding these exact
snapshots/queries from merely an equivalent dataset download. Public audits
verify scalar counts, directions and receipt chains without those large arrays.
Reports additionally need matplotlib and the installed `paper-figures` helper
under `AGENTS_SKILLS_HOME` (default user skill root), which is not vendored.
Assertions, IEEE round-to-nearest and gradual underflow must remain enabled.

O3 main dots accumulate four direction lanes per coordinate, then NumPy bounds
and filtering are vectorized. A new O0 scalar-direction implementation recomputes
all dots left-to-right, direct block reductions and scalar query lower bounds.
An owner-array oracle reconstructs every result. Both builds pass17 tests.
Covariance/eigh signs, represented exact Gram and PCA qualification are verified
from the retained frozen covariance; **covariance formation is not independently
recomputed from all data**. This distinction is explicit rather than turning
source/receipt audit into a second independent PCA fit.

## Scope and Gate 0

PCA/projections/boxes are established mechanisms, including
[PCA bounding-box analysis](https://page.mi.fu-berlin.de/~rote/Papers/pdf/Bounds%2Bon%2Bthe%2Bquality%2Bof%2Bthe%2BPCA%2Bbounding%2Bboxes.pdf)
and [VA-file (VLDB1998)](https://www.vldb.org/conf/1998/p194.pdf). This test makes
no novelty claim. Failure of global PCA4 axes does not establish a universal
limit on anisotropy or projections; no additional variants follow automatically.
K8, refits, adaptive directions, multi-box, repartition, update, hierarchy and
CUDA remain stopped. Existing end-to-end measurements and private Overleaf
manuscript are unchanged.
