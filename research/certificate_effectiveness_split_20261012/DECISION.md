# Decision: local-greedy split-objective headroom is below the gate

**Measured decision: `LINEAR_SPLIT_OBJECTIVE_HEADROOM_LOW`.** P4 does improve
all six frozen hard queries, but its best ancestor pooled alignment is below
40%, and its L3/L4 gains over P2 are both below 10 percentage points. This fails
the predeclared 60% plus 25 pp promotion gate; no proxy sweep or GPU work follows.

**Material caveat:** these are immediate-child, local-greedy oracles. They are
NOT globally optimized hierarchy upper bounds, so this result does not prove
that every PCA8 balanced tree or globally coordinated split sequence fails.
All results below concern the eight frozen queries only.

## Fixed workload result

Alignment = safe-pruned objects / truth-prunable objects, with truth recomputed
for each partition's membership. The all-query universe is 8M pairs; the hard
universe is 6M. Complete exact integer numerators and denominators are retained
in `evidence/per_level_summary.csv`, not inferred from rounded percentages.

| Partition | L3 all (%) | L4 all (%) | L5 all (%) | L3 hard (%) | L4 hard (%) | L5 hard (%) |
|---|---:|---:|---:|---:|---:|---:|
| GTS_ORIGINAL | 13.1900 | 22.0410 | 35.6207 | 2.1987 | 5.9778 | 17.1711 |
| PCA_BALANCED | 39.8440 | 45.8014 | 54.4858 | 22.8859 | 29.8107 | 40.4884 |
| ORACLE_ALL8 | 45.7028 | 53.1791 | 59.3777 | 30.5742 | 39.1233 | 46.6734 |
| ORACLE_HARD6 | 41.1350 | 51.4029 | 58.8805 | 32.2424 | 39.1217 | 46.3707 |

| P4 minus P2 | L3 | L4 | L5 |
|---|---:|---:|---:|
| All-query gain (pp) | 1.2910 | 5.6015 | 4.3947 |
| Hard-query gain (pp) | 9.3565 | 9.3110 | 5.8823 |

The K1 maximum P4 hard ancestor alignment is 39.1217%; K2 also fires (both gains
below 10 pp). P3 all-query ancestors remain below 60%, so EASY_QUERY_ONLY does
not apply. No promotion or strong-promotion ancestor qualifies. Gates are
computed from exact rational integer-count ratios, not rounded table values.

P4 is not even guaranteed to dominate P3 on final hard alignment: at L4 P3 is
39.1233% versus P4 39.1217%. Greedy ancestor choices change later parent
memberships; optimization on one parent is not a global dominance guarantee.

## Every hard query and both easy-query exceptions

Cells show P2 -> P4 alignment (%). Query selection predates this experiment.

| Query | Cohort | L3 | L4 | L5 |
|---|---|---:|---:|---:|
| 660835 | exception 660835 | 94.9799 -> 95.1807 | 95.5878 -> 96.3578 | 97.2088 -> 97.5869 |
| 90208 | other easy; not P4-scored | 86.2312 -> 40.2820 | 91.9444 -> 80.1261 | 95.7467 -> 95.2317 |
| 359924 | hard | 4.2339 -> 9.6774 | 7.0556 -> 11.1589 | 10.8649 -> 12.9500 |
| 374533 | hard | 18.8318 -> 29.2757 | 24.1693 -> 34.6978 | 34.5778 -> 41.8233 |
| 96985 | hard | 23.8911 -> 34.0726 | 33.5368 -> 45.1161 | 46.5307 -> 53.9093 |
| 702545 | hard | 12.4498 -> 15.4930 | 17.9225 -> 23.7242 | 28.2790 -> 32.2899 |
| 55715 | hard | 28.0967 -> 42.2961 | 36.7057 -> 53.5228 | 55.7745 -> 66.1673 |
| 470632 | hard | 49.7988 -> 62.6385 | 59.4716 -> 66.5132 | 66.9037 -> 71.0847 |

The hardest query 359924 remains at 9.6774% / 11.1589% / 12.9500%. Meanwhile,
P4 sacrifices the unscored easy query 90208: L3 falls from 86.2312% to 40.2820%.
Thus hard-query gain must not be narrated as workload-wide dominance. Exception
660835 remains easy; leave-one-out counts are also retained.

## Parent-level mechanism evidence

On each oracle's own parents, regret is best immediate objective minus S0, not
P3/P4 versus a different P2 parent. All 22,222 parents and all 266,664 proposal
rows are retained; zero-regret and rejected proposals are not dropped.

| P4 child level | Parents | Mean regret (query-object pairs) | Median | p90 | Zero-regret (%) |
|---|---:|---:|---:|---:|---:|
| L3 | 100 | 2180.000 | 1000 | 6000 | 34.00 |
| L4 | 1000 | 156.300 | 100 | 400 | 48.50 |
| L5 | 10000 | 11.971 | 0 | 40 | 56.19 |

All tested parent levels have nine unique proposal orderings on average, despite
twelve retained IDs: max-spread, cyclic, and lexicographic proposals duplicate
axis orderings in these continuous-coordinate parents. Lowest-ID ties favor
S0. Its selected frequency must not be treated as proof of intrinsic superiority.
P4 selects no radial proposal at L3/L4/L5; P3 selects radial for one L5 parent.
The full table, including ties and every losing proposal, supports this narrow
frequency statement, not a new universal geometric rule.

## Near-object contamination persists

At d <= U*, P2 truth-retained L3/L4 regions contain 48,936 / 5,636 far objects;
P4 contains 52,936 / 5,836. Thus the oracle did not reduce that pooled ancestor
contamination. At L5 P4 improves it slightly (546 -> 526 far objects). Each
partition still has exactly 64 near query-object pairs. The 1.05U* and 1.10U*
diagnostics are included in the CSVs but never enter the pruning rule.

## Correctness and resource receipt

- G1: all four full permutations, exact ten-way balancing, nested ownership pass.
- G2: **21,333,120 candidate query-child bounds** checked against cached original
  truth; separately **3,552,000 final query-region bounds**, zero above truth and
  zero false top-K prunes. All twelve final layouts roundtrip at 64 B/region.
- G3: reconstructed P2 permutation and every box, truth, near-count and query
  field match the prior metadata bytes. P0 has the same byte bridge. All six
  baseline pooled rows and 48 per-query rows match prior PCA8 counts/residuals.
- G4: 712 unique parent/oracle pairs, independently generated proposals and
  scalar boxes/bounds; all twelve eight-query score vectors, lowest-ID argmax,
  and selected child memberships match. Per oracle: all 100 L3 parents, plus
  128 unique L4 and 128 unique L5 parents frozen before construction.
- Original-vector/domain/projection validation is inherited via immutable
  6c0932f input hashes and receipts; this round independently enumerates cached
  coordinates, not a newly claimed full original-vector re-projection.
- Full final evaluation replayed on Python 3.13.12 / NumPy 2.4.3 and the
  construction runtime: all 12 primary cells, 96 query rows, safety records and
  decision are byte-identical. One supplementary mean-normalized-regret
  reduction differs by 3.47e-18; it is disclosed, not used by any gate.
- CPU-only, one bound core, threads=1, nice=10, owned lock, 900 s timeout;
  foreign processes untouched. Python 3.12.3, NumPy 1.26.4, Xeon Gold 6530.
- Each oracle: 133,332 proposals, 60M candidate-sorted object occurrences,
  10,666,560 actual all-eight query-child bound evaluations. P4's six-query
  objective uses 7,999,920 of these, while all-eight diagnostics/safety remain.
- Construction CPU time is 35.7825 s / 35.6586 s for P3/P4, including every
  candidate's truth safety audit; G4 separately takes 17.1246 s / 17.1255 s.
  P2 reconstruction is 1.2054 s. These are resource receipts, NOT production
  build comparisons, speedups, or query latency. Whole-worker RSS high-water is
  696,332 KiB, including caches, tables, metadata and G4. The 256,053,760 B
  explicit-array proxy excludes allocator/sort internals and retained tables.
- `BUILD_RECEIPT.sort_operations` counts proposal-order sorts only. Complete
  accounting in `COST_ACCOUNTING.json` additionally counts centroid ID sorts
  and spread-axis sorts: 155,554 calls per oracle, with 65,088,888 sorted key
  occurrences (including dimension keys). No hidden sort is treated as free.

## Decision and reopen condition

**Implementation:** validated offline diagnostic, no deployable index admitted.
**Mechanism:** useful but insufficient gain in this tested greedy path.
**Thesis impact:** do not launch a certificate-effectiveness proxy construction
mainline or expensive GPU campaign from this result. Preserve the negative
record; do not relabel 39.12% as meeting a 40% gate or a 60% promotion threshold.

A global-search upper bound has NOT been established. Reopen only with a
clearly distinct, prior-art-screened mechanism and a cheap decisive test under
a newly frozen contract; broader representation or globally coordinated choices
would be new directions, not retroactive rescue of this experiment. No new
projection, proxy sweep, ANN, nonlinear split or GPU work was run.

Allowed wording: "On eight frozen GIST queries with an unchanged exact-safe
64 B PCA8 certificate, local-greedy selection among twelve legal proposals raises
hard ancestor alignment to 32.24% / 39.12%, below the declared admission gate."
Disallowed: "linear tree construction is globally capped at 39%", "PCA8 cannot
work", "this is a novel workload-aware split algorithm", or a latency claim.


## Reference-audit interruption and accepted attempt

The first G4 radial reference used builtin float `sum`, which does not implement
our frozen sequential FP64 fold on the measured Python versions. A 100-object
cancellation fixture exposes a different centroid and 97 differing radial order
positions. [Python 3.12 documentation](https://docs.python.org/3.12/library/functions.html#sum)
also records the float summation algorithm change. The original sources and
receipts are preserved under `evidence/attempt1/`, explicitly unvalidated at G4.

Only the reference fold and a cancellation regression were corrected. A new
frozen full campaign (attempt 2) passed five tests and all 712 independent G4
parents. All four permutations, all metadata/truth/near/query arrays, complete
parent/proposal tables and every final result/safety record byte-match the first
attempt. `REFERENCE_REPAIR_BRIDGE.json` records the source and result bridge.
Thus the negative outcome is unchanged, but only the repaired second attempt
is admitted as validated. Historical PASS receipts are not retroactively edited.
