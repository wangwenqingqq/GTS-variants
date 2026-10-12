# Claim-evidence ledger

Task: `gtspp_20261012_update_stable_partition_gate0`; checked 2026-10-12.
Zero new GPU runs. Literature facts are source-backed; scientific conclusions
are marked inferred, not newly measured performance.

| ID | Claim | State | Evidence / exact scope | Counterevidence / allowed wording |
|---|---|---|---|---|
| G0-1 | Historical partition decisions can support exact metric retrieval under center deletion | theoretical | EGNAT Sections 3.1–3.2, author PDF hash in source manifest; documented and experimentally evaluated method | Current center changes and new insertions follow it. Say historical memberships/ranges, not immutable pivot identity. |
| G0-2 | Exact metric maintenance already uses thresholded deferred cleanup | theoretical | dsa-tree Sections 3.2–3.3.1 and Section 4 evaluates combined policy | Search cost rises with fake fraction; repairs may be broad. No reproduction here. |
| G0-3 | Radial-tree parent partition changes can propagate downward | theoretical | Dynamic VP-tree Section 5; Sections 5.1–5.3 specify/evaluate update policies | Does not measure this campaign's sparse-update leaf churn. |
| G0-4 | The current generic mechanism is insufficiently distinct | inferred | G0-1–3, full cards and conceptual substitution; KILL-2 | No direct GTS port was tested; verdict applies to recipe, not all possible GPU co-designs. |
| G0-5 | Prior algorithms port unchanged and meet packed-GTS targets | unknown | No evidence; no implementation, query or physical-work test | Forbidden claim. KILL-3 remains unknown. |
| G0-6 | Stability improves GTS maintenance latency or external gap | unknown | No evidence in this task | No speedup/latency wording; old gap numbers not remeasured. |
| G0-7 | Residual churn concentrates in changed-pivot L3 groups in R1/R2 | measured (inherited) | Baseline 9da7faa, existing result SHA-256 in CONTRACT; object shares90.027580%/92.268289%, leaf shares90.026889%/92.266542% | Association, not isolated causal fraction. R1 barely clears90%; same-pivot residual remains. |
| G0-8 | Stable partition identity alone is a new defendable mechanism | rejected | Scoped G0-4; exact generic candidate in CONTRACT | May reopen only for an independently specified non-incremental mechanism, not rebranding. |
| G0-9 | New traversal/physical-maintenance directions are novel or fast | unknown | No evidence; triage recommendation only | Run their own Gate0 before costly work. |

The evidence states describe this task's knowledge: `theoretical` rows document
prior mechanisms and correctness reasoning, not a reproduced benchmark. Prior
papers' reported experiments remain attributed to their authors in the cards.
There is no new GTS implementation lifecycle to promote.

Inherited source: [baseline L3 ledger](../../diagnostics/l3_residual_attribution_20261012/CLAIM_EVIDENCE.md)
and [baseline result](../../diagnostics/l3_residual_attribution_20261012/summary/RESULT.json).
