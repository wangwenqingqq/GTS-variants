# Claim-evidence ledger

Experiment: `GTSPP_20261010_block_certificate_global_pivots`. Frozen baseline
`db89d2f1aa66b934f3b99b5730efafa87cee5a71`; contracts and final closure accompany it.

| ID | Claim | State | Denominator / evidence | Allowed wording and counterevidence |
|---|---|---|---|---|
| BC1 | Current candidates are physically scattered | measured | 32 original queries/snapshot, exact candidate IDs; layout JSON/CSV and static proof | Offline tree-contiguous packing reaches 76.55% / 63.86% of block256 instead of ~99.5%; not GPU acceleration |
| BC2 | There is ideal block headroom | theoretical | Exhaustive hit-containing blocks for these fixed layouts; oracle JSON | Oracle lower bound is small; oracle is not a runnable filter |
| BC3 | <=4 global pivot bands meet cheap-query gate | rejected | All 48 main configurations/snapshot and block sensitivities; fresh 48M distance reconciliation | Best separately selected <=4 configurations retain 87.74% / 71.60%; no same-configuration GO |
| BC4 | Stable ownership permits bounded writes in these traces | partial | 288 offline simulations, exact 10I10D and 20I20D intervals; D proof/closure | <1.28% blocks altered; slack avoids existing-object moves. Independent initializations, global summary scan remains |
| BC5 | Proposed blocks reduce real GPU traffic / end-to-end time | unknown | No GPU implementation or traffic/timing evidence | No speedup claim; no prototype admitted |
| BC6 | Global pivot certificate is a new algorithm | rejected | Prior-art kill test: Pivot-based Metric Indexing, PVLDB 2017 | Triangle-inequality pivot filtering is established; this round claims no new algorithm |

Decision: **CONDITIONAL, not admitted for a GPU prototype**. Cheap-query gate
failed; explicit best-P8 >80% NO-GO did not fire. D continued only after the user
approved it as a diagnostic. Do not revive with 16/32/64 pivots. Reopen with a
meaningfully different tight partition/summary, first checking novelty and the
same cost/selectivity contract. Negative evidence does not establish that all
metric summaries, all layouts, all workloads or all GPU trees are incapable.
