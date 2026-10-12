# Results

**PIVOT_DOMINANT in both captured rebuilds; zero new GPU constructions.**

Counts use exact full leaf signatures and immutable pivot occurrences, not fuzzy overlap.
Each rebuild has 999,990 common-live occurrences and 100,000 POST leaves. All 1000 L3
parents have unique mutual correspondence; UNKNOWN contributes zero parents/objects/leaves.

## A. Complete POST group attribution

| Rebuild | L3 group | Parents | Common objects | Changed objects | Descendant leaves | Changed leaves |
|---|---|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 734 | 733,997 | 28,927 | 73,400 | 2,893 |
| R1 | CHANGED_PIVOT | 266 | 265,993 | 261,143 | 26,600 | 26,115 |
| R2 | SAME_PIVOT | 721 | 720,994 | 23,124 | 72,100 | 2,313 |
| R2 | CHANGED_PIVOT | 279 | 278,996 | 275,956 | 27,900 | 27,596 |

## B. Residual share and within-group rates

| Rebuild | Metric | Total residual | In changed-pivot L3 | Residual share |
|---|---|---:|---:|---:|
| R1 | Common objects | 290,070 | 261,143 | 90.027580% |
| R1 | POST leaves | 29,008 | 26,115 | 90.026889% |
| R2 | Common objects | 299,080 | 275,956 | 92.268289% |
| R2 | POST leaves | 29,909 | 27,596 | 92.266542% |

| Rebuild | Group | Changed objects / group objects | Changed leaves / group leaves |
|---|---|---:|---:|
| R1 | SAME_PIVOT | 3.941024% | 3.941417% |
| R1 | CHANGED_PIVOT | 98.176644% | 98.176692% |
| R2 | SAME_PIVOT | 3.207239% | 3.208044% |
| R2 | CHANGED_PIVOT | 98.910379% | 98.910394% |

R1 clears the 90% residual-object threshold by 80 objects. The residual-leaf gate
requires at least 26,108 changed-pivot leaves; 26,115 are observed. This narrow
margin is preserved, not rounded into a robust cross-workload guarantee.

## C. Retained-parent mechanics and L4 survival

| Rebuild | Group | Unique segment crossing / retained objects | Crossing rate | L4 inventory survival / PRE pivots | Survival rate | L4 same pivot / corresponding pairs |
|---|---|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 260 / 733,912 | 0.035427% | 7,080 / 7,340 | 96.457766% | 7,080 / 7,340 |
| R1 | CHANGED_PIVOT | 220,297 / 265,696 | 82.913179% | 79 / 2,660 | 2.969925% | 53 / 1,350 |
| R2 | SAME_PIVOT | 204 / 720,939 | 0.028296% | 7,005 / 7,210 | 97.156727% | 7,005 / 7,210 |
| R2 | CHANGED_PIVOT | 234,819 / 278,701 | 84.254811% | 57 / 2,790 | 2.043011% | 33 / 1,408 |

Inventory survival is limited to the corresponding L3 subtree. It is not paired
pivot equality; both denominators are given above.

## D. Nine split boundaries

| Rebuild | Group | 10% | 20% | 30% | 40% | 50% | 60% | 70% | 80% | 90% | Unique >=1 | Unique >1 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 18 | 26 | 26 | 37 | 44 | 36 | 36 | 27 | 10 | 260 | 0 |
| R1 | CHANGED_PIVOT | 43,587 | 74,509 | 94,656 | 105,374 | 107,060 | 99,879 | 84,722 | 63,296 | 35,585 | 220,297 | 162,372 |
| R2 | SAME_PIVOT | 14 | 25 | 28 | 30 | 27 | 30 | 23 | 17 | 10 | 204 | 0 |
| R2 | CHANGED_PIVOT | 46,654 | 79,593 | 101,439 | 112,809 | 114,050 | 106,509 | 90,873 | 68,266 | 38,304 | 234,819 | 174,490 |

These compare only retained common objects within matched parents. Summed boundary
counts are not unique-object counts. SAME groups have no multiple-boundary crossings.

## E. Occurrence-level absolute sorted-rank drift

| Rebuild | Group | p50 | p90 | p95 | p99 | max |
|---|---|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 0 | 0 | 0 | 1 | 2 |
| R1 | CHANGED_PIVOT | 214 | 607 | 718 | 875 | 999 |
| R2 | SAME_PIVOT | 0 | 0 | 0 | 1 | 1 |
| R2 | CHANGED_PIVOT | 223 | 608 | 715 | 867 | 999 |

| Rebuild | Group | Normalized p50 | p90 | p95 | p99 | max |
|---|---|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 0.000 | 0.000 | 0.000 | 0.001 | 0.002 |
| R1 | CHANGED_PIVOT | 0.214 | 0.607 | 0.718 | 0.875 | 0.999 |
| R2 | SAME_PIVOT | 0.000 | 0.000 | 0.000 | 0.001 | 0.001 |
| R2 | CHANGED_PIVOT | 0.223 | 0.608 | 0.715 | 0.867 | 0.999 |

Ranks are within each corresponding parent, normalized by its PRE size 1000.
Both SAME groups have **zero compressed common-only rank drift at all quantiles**.
Their complete-parent ranks can move by 1–2 because parent membership changes,
without reordering retained common objects. Actual input-rank drift max is 3/2
for SAME groups and 3/2 for CHANGED groups.

## F. SAME-pivot encoded-key/tie diagnostics

| Rebuild | Retained objects | Exact encoded-key bit changes | Common-only rank changes | Retained-common tie objects | Persistent tie subgroups | Reordered subgroups | Changed subgroup ordinal positions | Non-tied full-rank changes | Non-tied common-rank changes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1 | 733,912 | 0 | 0 | 24,115 | 11,166 | 0 | 0 | 24,587 | 0 |
| R2 | 720,939 | 0 | 0 | 23,392 | 10,946 | 0 | 0 | 19,759 | 0 |

All SAME parent offsets are directly comparable (734/721); none is omitted.
Non-tied means no tie partner **among retained common objects in either build**,
not necessarily no tie in the complete original parent. Exact encoded-key equality
is not Euclidean-distance equality. No relative tie reordering is observed here;
the ordinal-position metric is not a count of all pair-inversion participants.

## G. Migration accounting and PRE-cohort sensitivity

| Rebuild | POST L3 group | Retained | Imported common | Exported common | Changed imported | PRE cohort objects | PRE cohort changed |
|---|---|---:|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 733,912 | 85 | 80 | 85 | 733,992 | 28,922 |
| R1 | CHANGED_PIVOT | 265,696 | 297 | 302 | 297 | 265,998 | 261,148 |
| R2 | SAME_PIVOT | 720,939 | 55 | 57 | 55 | 720,996 | 23,126 |
| R2 | CHANGED_PIVOT | 278,701 | 295 | 293 | 295 | 278,994 | 275,954 |

All 382/350 migrated common occurrences have changed full leaf membership. PRE-cohort
changed-pivot object shares remain above 90%; this sensitivity check does not replace
the frozen POST cohort estimator or the POST leaf denominator.

## H. Descriptive L4 regrouping within SAME-L3 parents

| Rebuild | L4 group | L4 parents | Common objects | Changed objects | Leaves | Changed leaves |
|---|---|---:|---:|---:|---:|---:|
| R1 | SAME_PIVOT | 7,080 | 708,000 | 3,580 | 70,800 | 358 |
| R1 | CHANGED_PIVOT | 260 | 25,997 | 25,347 | 2,600 | 2,535 |
| R2 | SAME_PIVOT | 7,005 | 700,497 | 2,657 | 70,050 | 266 |
| R2 | CHANGED_PIVOT | 205 | 20,497 | 20,467 | 2,050 | 2,047 |

This post-primary, CPU-only descriptive split covers all SAME-L3 residuals with
no UNKNOWN children. Changed-L4-pivot children contain 2535/2893 and 2047/2313 of
SAME-L3 changed leaves. **Even SAME-L3 and SAME-L4 children retain 358/266 changed
leaves.** Boundary/membership instability is not proven absent. No L4 key or new
L3 intervention measurement is invented.

## Scope and preserved exceptions

The diagnostic gate passes, but it establishes concentration, not an attributable
causal percentage. R2 C1 still changes one more leaf than C0; the previous strict
monotonic and <=20% strong gates remain unmet. C3 overall leaf churn stays 29.008%
/29.909%. No new mechanism, performance, query-quality, production, novelty or
universal GPU-tree claim follows. Next action: separate prior-art Gate 0 only.
