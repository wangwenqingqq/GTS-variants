# REGION_WARP

One bounded intervention on REGION_EXEC parent `a7b16a6`: warp-per-leaf,
lane-per-object verification, shared by SPLIT and FUSED. SERIAL controls and the
strong parallel baseline remain in the same new executable.

This is established CUDA engineering, not a new tree or a novelty claim.
The experiment asks whether improved leaf ownership translates to complete
mixed-workflow speed, and separates mapping improvement from fusion.

## Completed result

All 30 formal and 60 separate observer processes completed. Independent integer
live-multiset replay checked all 900000 query outputs and exact FP32 fields.
WARP reduces complete-trace latency by 3.53% for SPLIT and 3.21% for FUSED versus
their SERIAL controls. The incremental fusion ratio is 1.00295x on this fixed
trace; PAR_STRONG/FUSED_WARP is 1.00104x with CI95 [0.99612, 1.00575].
There is no demonstrated win over the strong baseline. Keep PAR_STRONG and stop
this mapping trial without expanding seeds/budgets. Maintenance tails are not
uniformly improved. See [full results and all rounds](RESULTS.md).

## Qualification checkpoint

- Frozen N1000/D128/B1/radius0 trace: 10000 queries, 1000 insertions, 1000
  deletions, 50 rebuilds, seed2026100431.
- Actual multi-leaf regions account for 25203/104515 = 24.1142% of base-tree
  non-self distance evaluations. This is **not an elapsed-time fraction**.
- Repaired 8-leaf x20-object microcheck: geometric SERIAL/WARP 3.66548x.
  One process, six balanced batch pairs, 512 launches/batch; **not end-to-end**.
- All retained structural/direct/mixed-update correctness and sanitizer gates
  pass. Five independent full counter trajectories have identical node, pivot,
  leaf and object streams; ordered outputs and FP32 fields match.
- An initial periodic fixture is retained and excluded; see
  `evidence/v2/PRELIMINARY_ATTEMPT.json`. No primary processes used it.

The preregistered primary campaign requires five modes, six balanced rounds and
30 fresh formal processes; an interrupted matrix remains incomplete.
Observer admission uses 60 separate on/off
processes for this new binary; old admission is not inherited. Final performance
claims are scoped to the completed result and independent audit, not the microcheck.

See [design](DESIGN.md), [reproduction](REPRODUCE.md), and the curated
`evidence/v2/` receipts. Raw input/output/guard files remain in external
task-owned storage; their hashes differ from sanitized portable receipts.
