# Fixed block-local ball: NO_GO_LOCAL_BALL

**Stop the tested single-ball route.** LOCAL_BALL retains **92.2501% / 93.4250%**
of the same blocks, worse than GLOBAL4's **68.8995% / 67.8749%**. All 64 queries
are correct, and independent verification confirms the result. This is a
CPU structural diagnostic, **not an end-to-end timing comparison**.

- Dataset: **GIST N=1,000,000, D=960, FP32 L2, B1**; initial and first-rebuilt snapshots.
- Queries: original 32/snapshot; radius bits `0x3f34a3d8`; duplicate occurrences remain independent.
- Layout: frozen S1/P2, **4096 blocks of 244/245** members; no repartition or capacity-240 initialization.
- One rule: nearest real member to four-dimensional signature mean, exact ties by immutable occurrence ID.
- Baseline commit: `a85360852d3b44b03a885d1ad03fda5e945ad7e0`.
- Runtime: Linux x86-64 CPU, GCC 13.3.0, Python 3.12.3, NumPy 1.26.4; no new dependencies or GPU launches.
- Launch policy: OpenMP 4, BLAS 1, requested `nice -n 15`; registration fields declare policy, not independently sampled scheduler priority.

## Evidence

[Decision: five questions and stop boundary](DECISION.md) |
[claim boundaries](CLAIM_EVIDENCE.md) | [frozen contract](CONTRACT.json) |
[numerical proof](NUMERICS.md).

- [Comparison](query/SUMMARY_COMPARISON.md) and [64 complete rows](query/SUMMARY_COMPARISON.json).
- [Per-query robustness](query/ROBUSTNESS.md): the local-ball p90 is 99.8486% / 99.6973%.
- [Fully charged cost proxy](query/COST_PROXY.md): 4096 center distances, radius/optional-ID reads, 15.72864 MB center coordinates, and remaining exact-verification work.
- [Block statistics](summary/LOCAL_BALL_STATS.md) and [all 8192 scalar records](summary/LOCAL_BALL_STATS.json).
- [Execution proof](evidence/PROOF.json), [independent verification](evidence/VERIFY.json), [byte-preserving curation](evidence/CURATION.json).

## Three figure messages

1. [Summary survival](figures/summary_survival.pdf): the single ball keeps more blocks than GLOBAL4 and misses the 50% mean target (dashed line).
2. [Per-query comparison](figures/local_vs_global.pdf): 63/64 queries lie above the equal-survival diagonal; overlapping points remain in the CSV.
3. [Oracle gap](figures/oracle_gap.pdf): most queries still retain thousands of blocks without any reference hits.

Each figure includes a vector PDF, 300-DPI PNG and exact plotting CSV. Means
and quantiles describe these fixed query sets, not timing repetitions; no CI
is inferred. Each snapshot has the same 4096-block denominator. ORACLE is a
structural lower bound, not an executable competitor.

## Reproduce without silently changing input identities

Run from a complete repository checkout; sibling artifacts supply the proven
interval, partition validation and input bindings. CPU experiments need g++
with OpenMP plus Python/NumPy. Reports additionally use matplotlib and the
installed `paper-figures/scripts/paper_style.py` helper, located through
`AGENTS_SKILLS_HOME` (default user skill directory); that managed helper is
not vendored. No packages are installed by these scripts. Assertions must stay on.

```sh
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ART=artifacts/block_local_ball_20261011
python3 "$ART/audit.py"
# A small standalone boundary qualification; use an external fresh path.
: "${PAIR_LIB:?external .so path}"
g++ -std=c++17 -O3 -fno-fast-math -ffp-contract=off -fopenmp -shared -fPIC \
  "$ART/pairs.cpp" -o "$PAIR_LIB"
python3 "$ART/test_ball.py" --library "$PAIR_LIB" -v

# Resolve the retained campaign inputs, not merely an equivalent nominal dataset.
# PART: frozen partition run; PART_VERIFY: its raw verification/VERIFY.json.
# PRIOR: original pivot-score run; PRIOR_VERIFY: its raw verification/VERIFY.json.
# INPUTS: resolver JSON with records[snapshot].data and original qids.
# MAINT: immutable occurrence arrays; REFS: exhaustive ordered-FP64 reference dirs.
# OUT: external parent; child run/ and verification/ must not exist.
: "${PART:?}" "${PART_VERIFY:?}" "${PRIOR:?}" "${PRIOR_VERIFY:?}"
: "${INPUTS:?}" "${MAINT:?}" "${REFS:?}" "${OUT:?}"
mkdir -p "$OUT"
nice -n 15 python3 "$ART/experiment.py" --partition "$PART" --partition-verify "$PART_VERIFY" \
  --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" --inputs "$INPUTS" \
  --maintenance "$MAINT" --references "$REFS" --output "$OUT/run"
nice -n 15 python3 "$ART/verify_ball.py" --partition "$PART" --partition-verify "$PART_VERIFY" \
  --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" --inputs "$INPUTS" \
  --maintenance "$MAINT" --references "$REFS" --run "$OUT/run" --output "$OUT/verification"
python3 "$ART/curate.py" --run "$OUT/run" --verify "$OUT/verification/VERIFY.json" --output "$OUT/curated"
# Regenerate reports in a disposable complete checkout before resealing a new delivery.
python3 "$ART/report.py"
```

The raw data, 32 exhaustive references/snapshot, pivot caches, occurrence and
partition arrays require the preceding qualified campaigns. All are pinned by
contract/proof hashes; coordinate and raw certificate arrays stay outside Git.
The public scalar artifact supports count/receipt audits without those large
inputs. It does not claim a fresh-download standalone data reconstruction.

O3 produced the measurement. A new O0 binary reconstructed every distance in
reverse pair orientation; a scalar implementation reconstructed all C0 means
and selections. An owner-array oracle independently reproduced every row and
GLOBAL4 count. Both builds passed 11 numerical/gate tests. All center-query
scores also match retained exhaustive references bitwise. The verifier shares
the conservative-envelope helper, whose argument is documented separately.

## Scope, novelty and costs

[The full decision](DECISION.md) preserves negative evidence and the exact
reopen condition. Metric balls, covering radii and triangle inequality are
already established in [M-tree (VLDB 1997)](https://www.vldb.org/conf/1997/P426.PDF).
This bounded test makes no novelty claim. No updates, hierarchy, multi-center
variant, new pivots, CUDA, kNN, 10K/100K workflow or long timing run was added.
The old end-to-end matrix and private Overleaf manuscript remain unchanged.
