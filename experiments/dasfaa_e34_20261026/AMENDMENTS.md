# Append-only amendments

No GPU execution or measured GPU result existed when this file was created on
2026-10-25 UTC. See CONTRACT.md for the predeclared source-interface repair,
precision refinement, Q1024 wrapping and stage-specific freeze requirements.

## 2026-10-25 14:43 UTC — telemetry-loss fail-closed restart

During the 30M spatial P correctness process, nvidia-smi exceeded its unchanged
10-second timeout; the PID-safe monitor terminated only the verified owned
process. The connection also briefly stopped accepting new SSH banners. No
formal timing existed. Preserve the failed epoch, its 1/3/10M correctness
outputs and the timeout traceback. Treat telemetry loss as an invalid epoch,
just like lost isolation, and re-admit a fresh idle UUID before rerunning the
entire frozen schedule. No kernel, workload, tolerance, estimator or decision
rule changes. Earlier correctness failures are not relabeled as passes or
replaced; the new epoch repeats the exact same artifacts, not repaired variants.

## 2026-10-25 14:43 UTC — Word cardinality clarification (before Word runs)

The actual archived corpus has 611,756 rows. Reserving 1,000 disjoint query rows
leaves 610,756, fewer than the literal frozen N=611,000. The contract's sentence
that the 611K point "fits" was incorrect. Keep the 611,000 load in the matrix as
infeasible: insufficient distinct source rows after holdout. Do not duplicate
objects, index queries or replace that load with a different N. The 61K,150K,
300K loads are unchanged. This is a data-capacity correction, not a change to
the crossover rule.

## 2026-10-26 01:36 UTC — mandatory post-incident restart authorization

Reason: user authorized in conversation on 2026-10-25 (用户在对话中授权).
This entry supersedes the unsafe telemetry-loss restart policy above and the
incorrect leaf-endpoint-repair statements in the frozen contract. The original
contract remains immutable so its history is inspectable.

- P starts from archived search_v2.cuh SHA256
  `2268650537923903819c84245ca0b05050636cab59508d114a4033e952cce278`,
  applies the supplied gtspp_search_v2_fixes.patch, then WORK instrumentation
  macros only. Restore every native `le = qe`; never use `le = qe + 1`.
- G starts from archived SHA256
  `b7a9c719c9fcd67ffdda8e4583da02341d0bbaa0038121f418873629466cddaf`,
  applies gts_original_search_v2_fixes.patch. Native height must be configured
  for each N and verified against complete CPU-oracle output. Any additional
  G input/output-only adapter is disclosed before GPU execution; inability to
  establish this gate leaves G incomplete.
- Both patches are correctness repairs, not pruning-rule or distance-computation
  optimizations (正确性修复，不改剪枝规则和距离计算).
- P/G never run N > 10,000,000 or a tree requiring height >=8. Retain the
  requested larger loads as `infeasible: workspace chunking (tree_h=8)`;
  do not enlarge workspace or widen indexing. S retains every requested N.
- Every remote command/computational child is guarded: RSS <=16 GiB,
  MemAvailable minimum >=48 GiB, process timeout <=900 seconds, unique JSONL
  evidence log. Admission additionally requires MemAvailable >=64 GiB.
- Guard97/98, fail-fast3, NVML timeout, or failed new SSH connection stops the
  whole campaign permanently pending new user direction. No automatic retry,
  replacement epoch, or GPU change. NVML calls use `timeout 10`, polling >=30s;
  read /proc/meminfo first after a telemetry timeout and issue no more NVML.
- One GPU child at a time for session A; preserve other sessions/users/locks.
  Reuse SSH ControlMaster auto with 10-minute persistence.
- Old epochs epoch_1792938926876776595, epoch_1792939414418914187,
  epoch_1792940063917913387 are incident evidence only. None contributes
  correctness, timings, crossover, or slope claims. Fresh independent gates
  are mandatory even where the external repair report already passed.
- C2 and P-approx are removed; no approximation experiments run.
- Preserve query identities/splits; verify exact feature-value disjointness for
  every indexed prefix. Do not repair a collision by changing frozen queries.

Read-only recovery on 2026-10-26 found Word oracle logs containing only
`bin/edit_oracle: No such file or directory`; no word*.oracle or word*.strb
exists. The oracle is incomplete, not a valid recovered result. Generate the
frozen Word split/oracle only under guard, <=32 CPU threads.

## 2026-10-26 01:41 UTC — fresh source/output-only adapters and build gates

Reason: implementing the authorized correctness fixes before any new GPU result.
P search is the approved archived file + exact supplied patch + WORK macros only.
All other copied P headers remain byte-identical to the archive. Timed WORK
statements compile to no-ops. Compile P, instrumented P, and G in a fresh builds
namespace; retain every source/binary hash. Native G lacks full top-k IDs, so its
proposed output-only observer maps existing sorted leaf slots to original IDs;
external query rows remain outside indexed N. Native G height is set through
MAX_H using the existing order=10 and leaf capacity=20. No G distance expression,
pruning, or sorting rule is changed. These are input/output/configuration
adaptations, not optimizations. The harness checks leaf sizes, ID permutation,
and coverage before search. Both vector harnesses disable old, unkeyed index
caches; each process rebuilds outside the query timer and reports build time.
This changes preparation cost, not timed query residency or scope.

Static inspection additionally found original G's signed `int size_a` receives
half the available GPU bytes divided by sizeof(double). More than approximately
32 GiB free VRAM exceeds its signed-int slot capacity. On the intended near-idle
96 GiB device this cannot be assumed safe. Compile G for provenance but do not
launch it; mark G incomplete (native workspace int32 bound) unless a separately
authorized safe native configuration is established. Do not cap/enlarge its
workspace, widen indexing, or manufacture memory pressure to work around this.
This is source-derived safety evidence, not a measured G runtime result.

The bounded runner executes init once and one explicit step per invocation,
retaining the same epoch and UUID across successful checkpoints. It re-acquires
both locks and rechecks isolation every step; any failure latches a terminal
STOP_CAMPAIGN record. Computational children have <=600s budgets and compile
children <=240s, leaving safety margin below the outer <=900s guard. This is
orchestration only; six rounds, process pairing, workloads and estimator do not
change. One successful step never authorizes retrying a failed step.

## 2026-10-26 01:41 UTC — Deep feature-value isolation failure

Guarded read-only provenance verification passed all frozen input/prefix hashes.
Every recovered vector oracle has a complete 120000-byte payload, sorted finite
distances, valid distinct IDs, and candidate distances matching explicit FP64
recomputation. This validates structure, not a new exhaustive oracle computation.
T-loc (real 1/3/10M and synthetic 30/100M) has zero query/base value matches.
Deep 1/3/10/20M has respectively 16/63/201/379 matching base rows with the frozen
first1000 public queries (two queries have zero nearest distance in each prefix).
The newest user condition requires exact feature-value separation, not merely
source-row identity separation. Keep the Deep workload rows visible as
query-isolation-failed, do not run or time them, and do not silently replace the
queries or oracle. A deterministic public-query filtering amendment has been
requested from the user; no authorization is presumed.
