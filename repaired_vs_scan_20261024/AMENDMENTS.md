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

## v1.2 — user-authorized admission restart and native dependencies

2026-10-25 06:15 UTC, before new GPU execution. Reason: the user explicitly
requested completing the experiment rather than terminating on a transient
foreign process, authorized alternative idle cards, and authorized a user-local
Kokkos build. This supersedes only v1's GPU-0-only/terminal-stop rule and the
previous dependency-installation restriction; frozen radii, query IDs, data,
output/timing/statistical contracts and decision rules are unchanged.

- Eligible physical devices: 0, 1, 4, 5, 6, 7 on the existing measurement host.
  Recheck idle state and acquire the existing per-device advisory lock plus a
  task lock. All arms in a complete timing campaign use the same device UUID.
- Current live check found 0/1 occupied; those devices are not admitted. Device
  5 is the initial target, subject to a fresh lock-held idle admission.
- On foreign activity, invalidate and retain the current round; do not replace
  it or count it. Stop only the task-owned benchmark process group. Wait for
  idle or re-admit another eligible device, then restart the **entire six-round
  paired schedule** in a fresh epoch. Never combine epochs or GPU UUIDs.
- Earlier epochs/failed rounds remain archived with reason and telemetry.
  The pre-a9bc1c7 admission-stopped attempt remains intact; it has no samples.
- No foreign process signals or GPU-setting changes. Poll during GPU processes.
- User-local source/build/install of Kokkos >=4.5 with CUDA/sm_120 and native
  ArborX is now explicitly authorized in task-owned remote storage.
- Native four-arm timing schedule, saved before timing: ARSX, XSRA, RAXS, SXAR,
  ASRX, XRSA, where X is ArborX. Consecutive pairs are exact reversals; every
  arm pair has three executions in each relative order. Words retains v1's
  three-arm schedule. All other warmup/observation/CI rules remain v1.

## v1.3 — original empty-query launch legality adapter

2026-10-25 UTC, before formal timing. The bounded negative-radius original-A
probe emitted `leafProcess error: invalid argument`: the original host path
launches a zero-CTA leaf grid when no candidate exists. The generated scratch
copy now guards that original launch with `if(search_num[0]>0)`. No original
repository/source pin is edited. This is a disclosed legality adapter for empty
queries, not a pruning/distance/count optimization. All required positive-radius
workloads include self and remain on the original nonempty path. Frozen full-data
queries/radii and output/timing/decision rules remain unchanged. The failed probe
and its monitor receipts are retained. Monitor fixes also distinguish trailing
NVML utilization after task exit and sanitizer descendants from foreign work;
no formal timing samples existed when these fixes were made.
