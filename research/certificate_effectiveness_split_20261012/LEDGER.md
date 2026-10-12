# Experiment and claim ledger

## Before measurement

| Experiment | Hypothesis | Frozen contract | Keeper / candidates | Expected delta | Invariants | Evidence | Decision |
|---|---|---|---|---|---|---|---|
| certificate-effectiveness-split-20261012 | Immediate certificate-effectiveness split selection rescues the six hard queries at ancestor levels | CONTRACT.json; base 6c0932f; full GIST 1M, same eight queries, K8, PCA8/64B | P0 / P2; local-greedy P3 / P4 | Symmetric: large gain supports further proxy diagnosis; small gain stops this greedy search direction | Same score, U*, basis, safety, balanced nested ownership; 12 query-independent proposals | No measurements yet | designed |

Gate 0: generic workload-aware greedy split selection is already established
(Qd-tree); this is a diagnostic attribution probe, not a novelty claim. No GPU
or production performance gates apply. Compilation and unit tests do not count
as full-data correctness. G4 independently enumerates cached coordinates, while
original-vector/domain receipts belong to the preceding campaign.

The oracles are local greedy constructions, NOT an exhaustive search over trees.
Their results cannot certify the best attainable hierarchy in this family.
Tie preference and duplicate proposals can inflate S0 selection frequency.

## Appended measured outcome

| Claim | Scope / denominator | Evidence state | Exact evidence | Counterevidence / allowed wording |
|---|---|---|---|---|
| Split choice materially rescues hard ancestors past the gate | Fixed hard6, 6M pairs, L3/L4 | rejected | aggregate_summary.json: P4 32.2424% / 39.1217%, gains 9.3565 / 9.3110 pp | Positive gains do not meet 60% + 25 pp; LOW is a greedy-path decision, not a global family upper bound |
| Every final partition has exact-safe bounds under inherited score contract | 12 cells, 3,552,000 bounds | measured | CERTIFICATE_VALIDATION.json; complete 64 B roundtrip | Original-vector re-projection was validated in the preceding immutable campaign, not repeated here |
| The implemented local greedy choice is the declared argmax | 712 independent parent pairs, plus all 22,222 logged score-table choices | measured | PARTITION_AUDIT.json; proposal_scores.csv.gz; public replay | Cached-coordinate geometric G4 and public accounting replay are different gates |
| The oracle is uniformly better on the full workload | Eight fixed queries | rejected | Query 90208 L3 P2 86.2312% -> P4 40.2820%; full per-query table | P4 optimizes only hard6 and can sacrifice excluded queries |
| Globally optimized PCA8 trees are limited to this alignment | All possible hierarchies | unknown | no evidence | Do not claim a global upper bound from immediate-child greedy selection |
| GPU execution or deployable build/query speed improves | End-to-end production | unknown | no GPU or latency experiment | CPU resource receipts are not performance admission |

Implementation: validated diagnostic. Mechanism: positive but insufficient under
the frozen greedy probe. Thesis: do not promote a proxy construction mainline.
Negative record retains keeper, proposals, all losing scores, resource costs,
contamination, exceptions and reopen condition in DECISION.md. No thresholds,
queries, candidates, or basis were changed after measurements.

## Audit interruption and second frozen attempt

A cancellation regression showed that the first G4 radial reference used builtin
float `sum`, whose Python 3.12+ compensated behavior does not implement the
frozen sequential fold. The first attempt is therefore **unvalidated at G4**,
despite matching score counts on its sampled real parents. It was not published.
`evidence/attempt1/STATUS.json` overrides those historical PASS receipts; old
sources and receipts remain immutable forensic snapshots. Only the reference
centroid fold and a regression test changed. A fresh freeze and complete second
construction/validation campaign are required before final admission. No keeper,
proposal definition, dataset, sampling, threshold, query or certificate changed.

The second frozen campaign is now **validated**: five regression tests, all 712
strict-reference G4 parents, complete candidate/final safety and full baseline
bridges pass. Four permutations, every metadata/truth/query/near array, full
parent/proposal tables and all final result/safety files byte-match attempt 1.
Only attempt 2 is admitted. REFERENCE_REPAIR_BRIDGE.json and CROSS_RUNTIME_REPLAY.json
retain exact identities and separate the repaired reference from unchanged
construction outcomes. Resource receipts and report times use attempt 2.
