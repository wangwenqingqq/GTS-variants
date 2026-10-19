# Decision: finite-chain opportunity, not index/GPU admission

Implementation: CPU input binding, finite-chain sharing schedules, bounded oracle
and complete witness checking are closed. No GPU or production path changed.

Mechanism: relative to the strongest frozen simple envelope (attained by the
single FANOUT heuristic here), B2/B4 have exact residual savings10.9277%/23.4217%.
B8 has a2.3489%–44.8385% interval; its material-gap question is UNRESOLVED.
No evaluated feasible B8 schedule beats the batched full-scan source model.

Frozen primary: LOOKAHEAD and its CONTRACT labels remain in results. It is not
the strongest control in this population, and its B8 MATERIAL label is not used
to promote the stronger comparison. No threshold or comparator is rewritten.

Thesis: NOT_ADMITTED. A DAG, compatibility signature or planlet cache is not a
new mechanism by name. The oracle knows future certificate trajectories; a
cheap online policy and stable reuse structure have not been demonstrated.

Reopen conditions:
- An independently motivated future-blind shared scheduler captures residual
  savings against all frozen simple controls and a one-pass full scan.
- The effect generalizes to fresh held-out queries/datasets and relevant batches.
- State/metadata/terminal costs fit an explicit implementation; GPU or service
  claims need a separately authorized same-contract campaign.

Do not revive the old arrival-model result by using these offline batches, claim
all GPU trees need a DAG, or claim that the B8 lower bound is an executed plan.
