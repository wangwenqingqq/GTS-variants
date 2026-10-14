# PDX/BOND GPU realizability — Gate4 checkpoint

**CPU admission passed; GPU realization remains untested.** On GIST1M
(1,000,000 vectors ×960 FP32 dimensions, B1,32 fixed exact-range queries),
the approved PDX-BOND-ZONE32 adaptation required105.977753125 coordinates/pair
and captured49.7383118161% of the inherited original→query-global-oracle gap.
The fixed-stage coordinate model is711,680,776B/query, **not measured DRAM**.

| Complete-population logical diagnostic | Mean required coordinates |
|---|---:|
| Original order, inherited |167.291614750|
| Query-global restricted oracle, inherited |44.018710250|
| PDX-BOND-ZONE32, measured this campaign |105.977753125|

All32M original ordered-FP64 scores were checked bitwise; zero mismatches and
zero safe-certificate false rejections. Nominal and guarded crossing arrays
were identical. Four fixtures and32×4096 bounded qualification also passed.
Raw vectors/scores/per-pair arrays stay private; identities and scalar evidence
are included. This is a known-mechanism adversarial baseline, **no novelty claim**.

GPU source generation is drafted, but preparation stopped on mismatching old
dependency snapshots **before compilation or CUDA initialization**. No GPU/NCU
process ran. Recovery permission and GPU-label precedence/gray-zone clarification
were requested; neither is inferred from CPU success. No final Gate4 label yet.

Start with [the exact source specification](PDX_BASELINE_SPEC.md),
[the checkpoint decision](DECISION.md), [the claim ledger](CLAIM_EVIDENCE.md),
and [reproduction](REPRODUCE.md). Existing campaigns and manuscript are unchanged.
