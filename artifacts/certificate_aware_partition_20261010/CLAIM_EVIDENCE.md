# Claim–evidence ledger

Last verified: 2026-10-11. Baseline `b89264e`. Contract: `CONTRACT.json`.
CPU host class: Xeon Gold 6530; runtime details in `evidence/ENVIRONMENT.json`.
All claims concern GIST N1M/D960, original 32 range queries on each of two
snapshots. Raw identities and executed source hashes are in the static/update
proofs and registrations; published numerical records preserve raw bytes.

| ID | Exact claim and denominator | State | Evidence / quality gate | Counterevidence / allowed wording |
|---|---|---|---|---|
| C1 | S1/P2 mean normalized band width is 82.24% / 80.22% lower than S1/P0 | measured | `partition/PARTITION_STATS.json`, 64,024 direct-reconstructed per-block rows | P1 has wider mean bands than P0 for all snapshot/strategy pairs. Geometric norm-width diagnostic, not GPU speed or statistical significance. |
| C2 | Same S1/P2 lowers mean surviving physical blocks from 90.6698% / 88.8061% to 68.8995% / 67.8749% | measured | `query/BLOCK_SELECTIVITY.json`, 512 P4 rows, conservative envelope and zero false prune | Different physical block counts: 3907 vs 4096. Active-object retention also falls to 68.8981% / 67.8736%; not purely denominator dilution. No latency claim. |
| C3 | None of eight shared configurations passes <=50% on both snapshots | rejected | `evidence/DECISION.json`, joint configuration gate | Does not trigger explicit family NO-GO either. `CONDITIONAL / uncovered_interval`; do not claim specified <=65% conditional band passed. |
| C4 | Selected capacity-aware organization changes 0.4800% / 0.7199% of initial blocks, moves zero existing objects, and performs zero splits | measured | `update/UPDATE_RECHECK.json`, actual 10I10D / 20I20D; full final occurrence/lineage/slot/bound checks | Two independent initializations, not sustained epochs. Initial global packing costs excluded from event-time counters and explicitly disclosed. Insertion scans all block centroids. |
| C5 | D initialization preserves query survival at 68.8775% / 67.8418% before and after the respective update intervals | measured | 128 exact before/after query rows; zero false prune | Distinct 4167-block layout; cannot substitute the 4096-block static rates. Tiny actual intervals only. |
| C6 | Tighter partitioning materially helps, but a substantial safe-certificate gap remains | inferred | C1–C3; S1/P2 oracle means 0.3654% / 0.3746% | Does not uniquely attribute the residual to certificate expressiveness or prove a family-wide impossibility. |
| C7 | CPU wait, GPU traffic, throughput or workflow time improve | unknown | No new GPU implementation, profiler, or matched timing | No performance or end-to-end benefit is established. Never multiply structural reductions by previous speedups. |
| C8 | Pivot mapping, recursive splits and interval pruning are novel | rejected | Established metric-indexing prior art, linked in README | Do not frame these established ingredients as the new contribution. Any later GPU ownership co-design needs a separate novelty and same-contract performance gate. |

## Preserved negative result

- Target: safe block filtering at at most four query-pivot distances.
- Keeper: fixed L3/DFS P0; candidates: P1/P2/P3, with the same S0/S1 pivots.
- Added costs: global sorting/initialization; 4096 rather than 3907 certificates
  for recursive static layouts; all-block centroid scans for insert placement.
- Effect: substantial but insufficient block rejection; GO and stated positive
  conditional band both fail. P1's broader bands and P3's non-monotonic width vs
  survival relationship remain in the complete record.
- Diagnosis: tightness is one cause, not a complete explanation of the residual gap.
- Reopen condition: a separately approved, genuinely distinct cheap safe-summary
  hypothesis and prior-art kill test; no automatic additional partition or pivot
  search. No CUDA admission follows from local-write success.
