# Fixed GLOBAL4 pruning granularity diagnostic

**NO_GO_GRANULARITY: finer whole tiles hardly reduce exact object work.**
The one-variable CPU test independently builds maximum leaf capacities
512/256/128/64/32 under the same S1/P2 rule. GIST N1M/D960 FP32 L2 B1; two
frozen snapshots,32 original queries each, same FP32 radius bits0x3f34a3d8.
The256 permutations, starts and full64 count rows match the qualified anchor.

The primary denominator is surviving_objects/1,000,000, not surviving tile
percent. Capacity256 leaves hold244/245 objects; capacity32 leaves hold30/31.
GLOBAL4 four-pivot scores and complete ordered-FP64 references are hash-bound
reused inputs, not new query-pivot timings. No pivot/summary/query/radius changes.

## Results and closure

- [Granularity and occupancy](granularity/GRANULARITY_RESULTS.md)
- [Oracle by tile](oracle/ORACLE_BY_TILE.md)
- [Endpoint/filter cost and prescribed lambda sensitivity](cost/COST_PROXY.md)
- [Five-question decision](DECISION.md)
- [Claim boundaries](CLAIM_EVIDENCE.md), [numerics](NUMERICS.md)
- Three CSV/PDF/PNG curves in `figures/`
- Raw run/verification identities in `evidence/`; exact publish whitelist in
  `DELIVERY_MANIFEST.json`

Smaller leaves are nested subsets, verified independently; each main target
restarts construction, rather than reusing a query-selected partition. Stops
preserve recursive boundaries. All320 queries have zero false prune. A fresh
verifier stable-sorts each partition, directly reduces each tile's member
endpoints and constructs an object-owner oracle; its row/summary/cost/decision
serialization helpers and numerical envelope are shared, not a second independent
numerical proof or independent PCA/distance campaign. The scalar audit separately
checks stored counts/CSV/receipt consistency; it does not reread unpublished
arrays or prove execution merely from a manifest.

## Portable checks and exact retained-input reproduction

```sh
ART=artifacts/pruning_granularity_20261011
python3 "$ART/test_tiles.py" -v
python3 "$ART/audit.py"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
# PRIOR: qualified pivot raw run; PRIOR_VERIFY: its exact VERIFY.json.
# PART: qualified partition raw run; PART_VERIFY: its exact VERIFY.json.
# MAINT: immutable occurrence/lineage arrays + PREPARED.json.
# REFS: complete ordered-FP64 reference folders for each snapshot.
# OUT: external fresh parent; run/ and verification/ absent.
: "${PRIOR:?}" "${PRIOR_VERIFY:?}" "${PART:?}" "${PART_VERIFY:?}"
: "${MAINT:?}" "${REFS:?}" "${OUT:?}"
mkdir -p "$OUT"
nice -n 15 python3 "$ART/experiment.py" --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" \
 --partition "$PART" --partition-verify "$PART_VERIFY" --maintenance "$MAINT" \
 --references "$REFS" --output "$OUT/run"
nice -n 15 python3 "$ART/verify_tiles.py" --prior "$PRIOR" --prior-verify "$PRIOR_VERIFY" \
 --partition "$PART" --partition-verify "$PART_VERIFY" --maintenance "$MAINT" \
 --references "$REFS" --run "$OUT/run" --output "$OUT/verification"
python3 "$ART/curate.py" --run "$OUT/run" --verify "$OUT/verification/VERIFY.json" --output "$OUT/curated"
# In a disposable complete checkout, regenerate tables/plots before resealing a new delivery.
python3 "$ART/report.py"
```

Only Python/NumPy are needed for checks; plots additionally require matplotlib
and the installed `paper-figures` helper (`AGENTS_SKILLS_HOME`), not vendored
runtime/skill code. Assertions and IEEE round-to-nearest remain enabled. Raw
scores, coordinates/references, permutations and per-tile endpoint arrays stay
external and require qualified preceding campaigns. An equivalent dataset
download alone does not reconstruct these exact snapshot/query identities.
The compressed per-tile CSV retains occupancy without publishing object IDs.

## Frozen interpretation

GO/strong require the same tested target to pass both snapshots, object-work
gain and metadata conditions. A gap in the written bands is explicitly
`CONDITIONAL_GRANULARITY / uncovered_interval`, not positive update admission.
NO-GO uses the two-snapshot32 tests, not one failing sample. No update recheck
is performed after this NO-GO; no tile16/8, extra pivots/summaries, hierarchy,
CUDA or long runs follow. The planned coarse-ownership/fine-execution concept
is not implemented or qualified by this negative diagnostic.

Smaller blocks, filtering and vector-vs-block selectivity tradeoffs are classic;
see [Weber/Schek/Blott, VLDB1998](https://www.vldb.org/conf/1998/p194.pdf).
No novelty claim follows from leaf-size changes. Any future ownership/execution
co-design needs its own nearest-prior-art kill test and matched system evidence.
Previous formal end-to-end results and the private manuscript remain unchanged.
