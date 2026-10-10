# Certificate-aware partitioning: CONDITIONAL, no GPU admission

**Conclusion:** grouping in pivot-distance space narrows bands and improves safe
block filtering, but the best shared S1/P2 configuration still retains
**68.8995% / 67.8749%** of physical blocks. This is not an end-to-end speedup.
See [the five-question decision](DECISION.md) and [claim boundaries](CLAIM_EVIDENCE.md).

GIST **N=1,000,000, D=960, FP32/L2, B1**, 32 original range queries per snapshot;
radius bits `0x3f34a3d8`. Initial and first-rebuilt snapshots retain duplicate
occurrences as separate instances. Baseline: `b89264e2af42639d8c27947f83ddf15d8f379c77`.

| Item | Scope |
|---|---|
| Pivot sets | S0 prior GTS sequence; S1 prior deterministic farthest-first; first four entries only |
| Main partitions | P0 fixed L3/DFS; P1 lexicographic signature; P2 widest-span recursive median; P3 normalized-span median |
| Main count | 2 snapshots × 2 pivot sets × 4 partitions × 32 queries = 512 rows |
| Trend count | Same partitions, first two certificate dimensions only: 512 rows |
| Physical blocks | P0/P1: 3,907 (256 except final 64); P2/P3: 4,096 (244/245) |
| D initialization | Selected S1/P2 only; capacity-aware, 4,167 blocks of 239/240; actual empty slots 6.257499% |
| D events | Independently initialized 10I10D and 20I20D intervals; 128 before/after query rows |
| Correctness | Zero false prune; full final occurrence, lineage, ownership, slots and bounds checked |
| Runtime | CPU only; no CUDA launch, timing, sanitizer or end-to-end performance claim |

## Evidence inventory

- [Frozen contract](CONTRACT.json): definitions, tie rules, gray-zone fallback,
  predeclared top-one ranking and authorized capacity-aware D initialization.
- [Partition table](partition/PARTITION_STATS.md), [balance/occupancy](partition/BALANCE.md),
  [full per-block statistics](partition/BLOCK_STATS.csv.gz) (64,024 scalar rows).
- [Query table](query/BLOCK_SELECTIVITY.md), [all query rows](query/BLOCK_SELECTIVITY.json),
  [P=2 trend](query/P2_TREND.md).
- [Update table](update/UPDATE_RECHECK.md), [complete update events/checks](update/UPDATE_RECHECK.json).
- [Static proof](evidence/STATIC_PROOF.json), [independent verification](evidence/STATIC_VERIFY.json),
  [update proof](evidence/UPDATE_PROOF.json), [byte-preserving curation](evidence/CURATION.json).

## Figure messages

All plots use P=4 and arithmetic means over each snapshot's fixed 32 queries.
They are exact descriptive aggregates of this query set; there are no timing
repetitions or inferential confidence intervals. Per-query distributions remain
in JSON. Dashed 50% lines mark the query GO target. No GPU time is plotted.

1. [Band tightness vs survival](figures/band_width_vs_survival.pdf): recursive
   grouping sharply narrows bands, but retains a large surviving-block fraction.
   P2/P3 can nearly coincide; the hollow P3 diamond preserves visibility.
2. [Partition comparison](figures/partition_comparison.pdf): S1 benefits from
   recursive grouping on both snapshots, without reaching GO.
3. [Oracle gap](figures/oracle_gap.pdf): thousands of blocks per query still
   survive unnecessarily. Absolute counts use each partition's actual block count.

PNG previews and the exact plotting CSVs accompany all three vector PDFs.
`report.py` uses the installed `paper-figures` helper; it is not redistributed.

## Reproduction

Run from a complete repository checkout, **not a copied script alone**. Python
3.12.3 and NumPy 1.26.4 produced the CPU evidence. Local tests also pass with
NumPy 2.0.2. Raw coordinate, reference and permutation files stay outside Git;
they require the existing qualified campaign evidence, not a fresh download
of merely the same nominal dataset. Every required input identity is pinned
in the contract or prior proof. Input mismatch aborts rather than silently
regenerating queries, pivots or snapshots.

```sh
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ART=artifacts/certificate_aware_partition_20261010
python3 "$ART/test_partition.py" -v
python3 "$ART/test_update_recheck.py" -v
python3 "$ART/audit.py"

# Resolve these external directories to retained evidence; do not put them in Git.
# PRIOR: prior block-certificate run directory (PROOF.json and score/layout arrays).
# VERIFY: prior verification/VERIFY.json (raw receipt, exact pinned hash).
# MAINT: maintenance directory (PREPARED.json, occurrence and lineage arrays).
# REFS: reference directory with initial/ and first_rebuilt/ subdirectories.
# OUT: a new external output directory; all three child directories must be absent.
: "${PRIOR:?}" "${VERIFY:?}" "${MAINT:?}" "${REFS:?}" "${OUT:?}"
mkdir -p "$OUT"
nice -n 15 python3 "$ART/experiment.py" --prior "$PRIOR" --verification "$VERIFY" \
  --maintenance "$MAINT" --references "$REFS" --output "$OUT/run"
nice -n 15 python3 "$ART/verify_partition.py" --prior "$PRIOR" --verification "$VERIFY" \
  --maintenance "$MAINT" --references "$REFS" --run "$OUT/run" --output "$OUT/verification"
nice -n 15 python3 "$ART/update_recheck.py" --prior "$PRIOR" --verification "$VERIFY" \
  --maintenance "$MAINT" --references "$REFS" --run "$OUT/run" \
  --static-verification "$OUT/verification/VERIFY.json" --output "$OUT/update"
python3 "$ART/report.py" --artifact "$ART"
```

`NUMERICS.md`, interval construction, raw IO and stable update operations are
reused from [the prior artifact](../block_certificate_headroom_20261010/README.md).
The signature uses ordinary FP64 square roots only to partition; rejection uses
the prior conservative envelope. Partition construction has no query/oracle input.
The independent verifier uses stable argsorts instead of lexsort, direct block
reductions instead of reduceat, and an object-owner oracle instead of permuted
block reduction. Prior distance caches were already freshly verified; this round
hash-binds and reuses them rather than claiming another distance recomputation.

## Mechanism, costs and stop boundary

Build phase: four global pivot signatures, deterministic sorting/recursion,
per-block min/max and stable block ownership. Query phase: four query-pivot
distances, all block interval checks, then an *unimplemented* exact GPU verifier.
Update phase: global scan over block means to choose a destination, local hole
insertion/deletion and the retained local split rule. The last two phases are
offline count simulations only. Live CPU arrays include four scores per object
and 32 reference scores per object; no GPU dispatch geometry is implemented.

Expected benefit is fewer full-block verification candidates; costs include
global initialization/sorting, certificate metadata/filtering, and global
insertion routing. Local changed-block counts measure writes, **not CPU locality**.
The two update intervals do not establish one sustained organization across epochs.

Novelty Gate 0: pivot-space mapping and triangle-inequality pruning are already
established; this work makes no novelty claim for them. See
[Pivot-based Metric Indexing (PVLDB 2017)](https://www.vldb.org/pvldb/vol10/p1058-gao.pdf).
The bounded diagnostic cannot rescue a subsumed thesis. A later GPU co-design
requires a distinct mechanism, nearest-prior-art review and decisive matched
end-to-end evidence. Current evidence is in the unassigned 65–70% region:
**CONDITIONAL / uncovered_interval**, not a positive conditional-band pass and
not a proof that every global-pivot certificate must fail. Do not extend P,
partitions, CUDA or long runs automatically.
