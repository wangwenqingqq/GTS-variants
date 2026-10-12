# Experiment record

| Experiment | Hypothesis | Contract | Evidence | Decision |
|---|---|---|---|---|
| gtspp_20261012_l3_residual_attribution_n1m_d960 | C3 residual churn concentrates in changed-pivot L3 subtrees | CONTRACT.json, frozen before group measurement | Four existing PRE/C3 replays and actual L3 sort/pivot evidence | Pending measurement at contract freeze |

This is CPU-only structural attribution, not a new implementation or performance
campaign. The comparator and snapshots are pinned to commit `955d020` and its
result, raw manifest and closure hashes. The previous ten GPU constructions are
reused; this task has a zero GPU-process budget. Query correctness, sanitizer,
stress, Graph, SASS, sustained throughput and production admission are not tested.
No source-of-truth snapshots or old scripts are modified.

The novelty gate is deferred because this task only diagnoses an existing measured
intervention. Any subsequent update-stable organization mechanism requires its
own nearest-prior-art kill test before implementation or expensive measurement.

## Measurement closure (2026-10-12)

- CPU v1: complete POST grouping, ranks, keys, boundaries and L4 survival;
  PIVOT_DOMINANT in both rebuilds. Raw v1 summaries and logs retained.
- Audit calibration: the tie-object metric now names subgroup ordinal-position
  changes rather than implying pair-inversion participation. It remains zero.
  Frozen input rehash/source bindings are now performed by the reproducible entry
  point, not only during preparation. No primary result or threshold changed.
- A supplementary hierarchy-local L4 group table was added after primary v1 to
  describe SAME-L3 residuals. It uses existing structure only, not new raw L4 keys,
  intervention, admission gate, dataset or GPU construction.
- Final CPU analysis recomputed complete structure and L3 evidence, all expected
  totals and group closure. Both primary gates pass; R1 only narrowly passes 90%.
- Independent read-only validation agrees on all primary counts, correspondence,
  migration, survival, rank, key and boundary fields without importing the analysis.
- Source/contract, exact bytes, structural validity and group attribution pass.
  Performance, novelty, query correctness, sanitizer/stress and production gates
  are not tested or admitted. Next action is a separate prior-art Gate 0.
