# Focused traversal diagnosis

Preregistered after the primary campaign and before NCU collection on
2026-09-23. Primary timing is complete: F passes its bounded promotion rule;
P does not. This follow-up cannot change those measured observations.

Question: why does a 90% reduction in evaluated query-pivot distances fail to
improve completed-query time? Distinguish logical work from SIMD instruction
work, producer-lane parallelism, memory traffic and shared-publication overhead.
These are hypotheses, not conclusions before collection.

- Use the same byte-identical executable, fixture, radius 4 and admitted GPU 1.
  Verify the device is idle and acquire its existing nonblocking advisory lock.
  No foreign process, driver, clock or power change is authorized.
- Fixed order D, G, Q; profile first query only: original `findNextRnn` first
  two matching launches, F `fusedTraversal` first matching launch, P `dedupLevel`
  first two matching launches. These cover the same two-level traversal but not
  the initialization/parent-clear kernels retained in D/Q. All modes execute
  the complete 64-query set and must match the approved ordered-output hashes.
- NCU 2025.4.1, kernel replay, no clock control and no cache control. Identical
  sections: SpeedOfLight, LaunchStats, Occupancy, SchedulerStats, WarpStateStats,
  MemoryWorkloadAnalysis and InstructionStats. No warmup; one selected first
  query is diagnostic, not a representative 64-query average.
- Use the verified existing passwordless sudo path for counter access. Execute
  the inspected monitored harness under sudo so it can terminate only its own
  child group on timeout (180 seconds) or interference. Preserve the existing
  lock's ownership/permissions; open it with `r+`.
- Derive a separate NCU runner from the pinned primary runner. Do not modify
  the primary runner, kernels, executable, 133-run inventory or timing. Store
  all three NCU runs separately with reports, exports, receipts and hashes.
- NCU duration, warnings and metrics are mechanism evidence only. Do not use
  replay duration as the speedup denominator, infer source-PC causality without
  PC evidence, or interpret heuristic estimated speedups as achieved results.

Reproduce after the primary oracle/identity gates and live device admission:

```sh
sudo -n python3 diagnostics/traversal_ablation_20260923/profile_ncu.py \
  "$SCRATCH" --gpu "$ADMITTED_UUID"
```

The helper refuses to overwrite an existing `ncu` directory. Preserve failed
attempts rather than reusing labels. Results are recorded separately from this
pre-collection plan.
