# Append-only protocol amendments

## v1.1 — strong-baseline batching, before any GPU execution

2026-10-25 UTC. Zero GPU benchmark processes and zero samples exist.

The v1 serial-bundling paragraph is too weak for a decisive strong-baseline
comparison. It must not be used to force a scan or ArborX implementation to
serialize merely because R is batch-one. The execution contract remains complete
host-ready output, not an identical internal schedule.

- S must use its native batch execution where supported. Serial S is only a
  labeled diagnostic and cannot replace the strong S column for Q=32/1024.
- Native ArborX, if buildable, may use its native batched predicates.
- Record A's native API and actual complete-output batching support separately.
  Its `qnum` parameter alone is not proof of correct Q1024 result delivery.
- R may retain the existing serial Graph-query bundling if no native repaired
  batch path exists; label that restriction explicitly. Do not relabel it native.
- Report native and serial modes separately. If the strong required S cannot be
  built/validated, the corresponding required workload remains incomplete.

No radius, query ID, target, confidence rule, sample, or decision was changed.
The frozen CPU-oracle manifest binds the original v1 CONTRACT.md hash; the active
GPU protocol is CONTRACT.md plus this amendment. No GPU runner implementing
these requirements has been delivered or executed in this checkpoint.
