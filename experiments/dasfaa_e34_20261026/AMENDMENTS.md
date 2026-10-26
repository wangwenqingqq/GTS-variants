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

## 2026-10-26 01:56 UTC — Word byte-semantic phase freeze

Reason: complete the predeclared Word adapter/input freeze before any Word GPU
result. Word source SHA256 is
`72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c`.
The actual corpus contains seven rows with non-ASCII bytes and no embedded NUL.
The first ASCII-only preparation failed before writing any artifact. The
approved interface now preserves native LF/getline and byte/strlen semantics;
no decoding substitution, Unicode normalization, filtering, or source mutation
is used. Seed/permutation remain 20261026. The exact manifest is retained at
`evidence/resume_20261026/WORD_MANIFEST.json`: base SHA256343ed61e…66d42,
query SHA256c355cca7…6100c; all61K/150K/300K prefixes have zero exact-string
query/index matches. Literal611K remains infeasible: only610756 base rows remain
after1000 held-out queries. Do not substitute610756 as the requested scale.

The new independent exhaustive CPU edit oracle uses byte equality and the same
Levenshtein distance, with <=32 threads, strict packed-format validation, and
atomic completed-output publication. Actual61K/150K/300K oracle generation has
completed under guard with16 threads; full output audits and all GPU gates are
still required. Its compilation initially encountered a missing optional
/usr/bin/time wrapper; no oracle child started in that attempt. The direct
bounded oracle succeeded; no prohibited guard/telemetry/SSH failure occurred.

Vector gate execution remains the corrected fixed epoch; none of these Word
files changes its frozen runner, scan, oracle, or workload identity. Word GPU
execution is a separately frozen phase after the vector plan, not a concurrent
GPU job or a retry of any failed vector configuration. C2/P-approx remain off.

## 2026-10-26 02:04 UTC — policy labels versus measured tree capacity

The mandatory N>10M exclusion is a user-imposed safety cap, not an empirical
measurement of the tree height of every excluded dataset. The prescribed
`infeasible: workspace chunking (tree_h=8)` label records the incident-driven
policy. Height8/zero-chunk was established by the incident's30M case; no20M Deep
or other excluded tree is launched to test capacity. Native order10/leaf20
height arithmetic alone does not authorize an exception to the10M cap. Reports
must not turn this policy exclusion into a measured height8 claim for20M Deep.

## 2026-10-26 02:24 UTC — intentional contract-output HOLD, not a safety-failure retry

Review found the carried-over P timer materializes kIDs but does not read back
native k-distance output before freeing it; S returns distances and IDs. The
full-result timing condition therefore needs explicit clarification. A control
STOP_CAMPAIGN record was created on2026-10-26 at02:12:55UTC; the current guarded
sanitizer finished normally, and the next step exited at the STOP check before
launch. No formal timing/full-scale gate ran. No guard97/98, fail-fast3, NVML
timeout or failed SSH was observed in sessionA. There is no automatic new epoch
or retry. Both contract questions (complete payload and deterministic Deep
value-disjoint queries) remain awaiting user direction; no authorization is
inferred from preselected UI choices. The current epoch is diagnostic only.

Completed bounded evidence: P memcheck/synccheck atQ1/32/1024 and S memcheck at
Q1/32, all N2000, zero errors and complete-ID tie-aware recall1. The other S
sanitizers, all full-scale correctness/count/timing, WordGPU and E3 remain not
run. Final read-only checks matched every frozen vector input/prefix/oracle hash.
Raw guard/receipt evidence is archived with the hash in RAW_ARCHIVE.json.

The Word phase preparation now covers exact byte-preserving inputs, guarded
CPU oracles, source/binary/build-log binding, exact interpreter/runtime hashes,
and per-S JIT cache-container/source hashes anchored to completed steps. These
are prelaunch integrity procedures, not a waiver of STOP, complete-result
semantics, or the vector-first order. No runtime/system skill or shared package
was changed. TanimotoS remains CPU-tested preparatory code, not a GPU result.
