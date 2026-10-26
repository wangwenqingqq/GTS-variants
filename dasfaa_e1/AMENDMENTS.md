# Append-only E1 amendments

No task-owned GPU execution at contract freeze.

## 2026-10-25 UTC — E1a interface and bounded implementation gates (before GPU execution)

- Native archive update APIs are range-only. The prototype kNN adapter uses k
  arbitrary live objects to establish a safe query radius (including a small
  FP32 safety margin), runs the unchanged native range pruning, unions exact
  device delta top-k, and selects top-k on the host. Input, full native candidate
  return, merging, CPU seed/selection and synchronization are all operation
  costs. This is not an unchanged native dynamic kNN API and is not yet a
  decision-grade performance implementation. No oracle bound is supplied.
- New arrivals are copied from external host payloads into a persistent device
  store, never indexed until blocking rebuild. The original legacy insertion
  functions are excluded entirely from the executable, not merely disabled.
  A single stable-slot integer delete bitmap covers native tree and delta;
  native physical IDs are mapped to stable slots before bitmap reads. Rebuild
  gathers live objects device-to-device and retains external stable IDs.
- Add missing binary Tanimoto branches to the native tree/range/leaf functions;
  original G does not implement metric 8. This is metric/interface support,
  not a changed existing distance/pruning optimization. Thus ChEMBL G must be
  labelled "G + Tanimoto interface extension", never unchanged archival G.
- Set G's configurable maximum height conservatively. P's existing logarithmic
  height recipe is replaced by the same worst-child recurrence to guarantee
  native leaves fit MAX_SIZE. Existing residual-last-child splits can otherwise
  exceed the query stride. This is a structural safety fix, not a new pruning rule.
- Smoke B values are G=10 and P=300 to exercise reconstruction; an optional
  G/B=300 fixture is not a measured Proposition estimate and cannot be labelled
  the final G+B* arm. B* calibration and full timings remain blocked until their
  complete correctness/input gates pass. All prototype latencies are diagnostic.
- Read-only input audit found feature collisions also in GIST (17 corpus rows)
  and Deep (42), in addition to T-loc/Word/Protein/ChEMBL. Only SIFT passes
  the literal native-query disjointness condition. No input was repaired.

## 2026-10-25 UTC — smoke input pins and tool-path correction (before GPU execution)

All 21 real-data smoke cases were generated with byte-exact source-row maps,
feature-disjoint base/arrival/query sets and exact 2000/2000/1000 event counts.
Their hashes are frozen in evidence/SMOKE_PINS.json before the first run.
Initial PATH nvcc invocation could not locate CUDA headers through the extra
/usr/local/bin symlink; use the toolkit-owned CUDA_HOME/bin/nvcc instead.
The failed build log is retained as build_attempt_01. All three prototypes
compile with CUDA 13.1; compilation is not a correctness or timing pass.
The device guard is reused from the prior campaign's final runner, including
ownership checks and post-exit utilization settling. Candidate idle devices
are all eight existing devices, in preference order 6,7,0,4,5,1,2,3, subject
to the same exclusive advisory lock and fresh no-process admission.

## 2026-10-25 UTC — v2 bounded-to-smoke correction (no performance samples)

The first bounded correctness epoch is retained, including any externally
contaminated attempts. Before full smoke, correct the new wrapper's delta
threshold to count LIVE pending objects: native G removes a deleted pending
object from its buffer, so counting tombstoned physical slots would alter its
rebuild policy. G and P use the same live-delta threshold; scan still filters
all tombstoned physical rows. No tree metadata is changed on append/delete.
Materialize host merge distances once per candidate instead of recomputing
them in every comparison, and retain deterministic CPU oracle top-k IDs.
The diagnostic candidate-merge implementation remains shared between G and P;
no public timing estimator, decision or workload is changed. The first bounded
binaries and build logs are retained separately before rebuilding.
A separate expected-failure memcheck will run the unchanged archival naive scan
kernel on a compacted-array/original-ID boundary. It diagnoses the historical
failure class, not a literal full replay of the old SIFT-50K campaign.

## 2026-10-25 UTC — pre-launch trailing NVML utilization classification

The bounded runner retained three invalid epochs where a later pre-launch
snapshot showed 24–29% utilization but zero applications and only 14 MiB.
These are NOT established external-process contamination: they are trailing
NVML windows from the preceding task. Extend the same zero-application
settling check to pre-launch snapshots, retaining initial/settling/final states.
Actual external application presence still invalidates the epoch immediately.
No previous sample is relabelled as valid; no performance samples exist.

## 2026-10-26 01:45 UTC — explicit user authorizations and post-incident resumption

Reason: the user authorized these decisions in the continuation conversation on
2026-10-25 local time. This is an append-only supplement, not a rewrite of v1.
All preceding P/G repeated-query observations are invalidated and retained only
as historical diagnostics. The bounded_v1 run covered prefixes, not complete
5K-event smoke cases; full_v2 stopped on an NVML timeout. This conversation is an
explicit resumption after that incident, not an automatic campaign retry.

- Both archival arms receive the mandatory correctness fixes: P original
  search_v2 SHA-256 `2268650537923903819c84245ca0b05050636cab59508d114a4033e952cce278`,
  G original `b7a9c719c9fcd67ffdda8e4583da02341d0bbaa0038121f418873629466cddaf`.
  The two authoritative patch SHA-256 values are respectively
  `ccb0b634e06b0c4d2ab302144f0fd3fe17eef8b75ba9d2da90a5cb3af418100d` and
  `1e129c1539df9c9180dbb76603f7db9ade7aa27d0a0bda9e09e46a9ad2e04a40`.
  These are correctness repairs, not changes to the pruning rules or distance
  computation. No `int le = qe + 1` modification is admitted. All original,
  derived, executed-source and binary hashes must be recorded separately.
- Every remote computation (including CPU preparation/oracles and compilation
  in this continuation) runs under the authoritative resource guard. E1 uses
  RSS <=16 GiB, MemAvailable minimum >=48 GiB, prelaunch available >=64 GiB,
  per-gate/per-run deadline <=900 s, individual campaign processes <=1800 s.
  CPU numerical-library thread counts are explicitly capped (default 1).
- N <=10,000,000 for both trees, additionally constrained by actual int32
  indexing and workspace representation. Larger input availability is not
  permission to run it. No workspace enlargement.
- Guard return 97/98, fail-fast return 3, NVML timeout, or new SSH failure
  stops the entire campaign. No automatic retry, new epoch, or GPU switch.
  On NVML timeout read /proc/meminfo first; do not call NVML again. This
  continuation removes the legacy runner's broad exception swallowing,
  subsecond NVML polling and automatic invalid-epoch restarts. Existing v4
  device locks, process-identity ownership and pidfd termination are reused.
  NVML calls use `timeout 10`, snapshots are >=30 s apart; SSH uses the
  mandated ControlMaster/ControlPath/ControlPersist options.
- At most one E1 GPU task runs at once. Session A may be running E4; do not
  touch its directories, locks, GPU settings or processes. The shared global
  limit remains two GPU tasks, at most one with RSS >8 GiB.
- T-loc, Word, Protein and ChEMBL use 1,000 uniformly sampled corpus queries
  (PCG64 seed 20261026). Remove every corpus feature match of those queries,
  then permute the remainder using the same fixed seed and split 90/10.
  Freeze actual counts and hashes before execution. Preserve byte-exact text
  and feature equality including +0/-0. No arrival ID is recycled and no
  payload is fabricated. SIFT/GIST/Deep retain ANN-Benchmarks queries and
  require verified zero feature matches. Existing GIST=17/Deep=42 corpus
  collisions remain input-contract-blocked pending an explicit user decision;
  asking for a decision does not itself authorize removal.
- Inventory larger ChEMBL37, SureChEMBL release artifacts and protein_200k
  read-only, including format, provenance, counts and hashes. Do not replace
  frozen datasets before the user's decision. Capacity-short combinations
  remain `contract-infeasible` in the complete matrix.
- Add sequential query-before-insert duplicate-detection workloads: kNN k=1
  and k=8, and full-output range search with a calibration-selected/frozen
  quantile radius targeting median cardinality about one. Batch is one.
  Include the complete query+insert operation in p50/p95/p99/throughput;
  record rebuild count/stall and validate visibility of every preceding
  acknowledged insertion. Exact range calibration artifacts and workload
  lengths must be frozen before this added workload runs; they are pending,
  not silently invented or represented by mixed traces.
- C2 is removed. P-approx is not run.

### Executed-path boundary identified before any new GPU launch

The prior frozen adapter uses native dynamic RANGE search to enumerate a safe
kNN candidate set, followed by exact delta top-k and host selection. The seed
radius uses k live objects, never oracle answers; all seed/merge/copy costs are
operation costs. This exercises archived C1 range-update paths, not static
search_v2 kNN. Merely patching an unused static header is NOT a proof that a
binary executed the repaired kNN path. The actual range path independently
requires complete-output validation. Until the user resolves whether to retain
this documented adapter or require a native dynamic kNN extension, new adapter
runs are explicitly diagnostic correctness/sanitizer evidence only, never
paper-facing performance results or validation of the repaired native kNN.
Native G lacks a full-ID kNN output API and live-only pivot bounds; adapting it
must not silently change pruning or erase the original C1 contrast.

## 2026-10-26 UTC — mandatory conservative stop before GPU validation

The guarded read-only CPU inventory SSH client returned 255 after four complete
SureChEMBL snapshot records; stderr was empty and no final guard receipt or
inventory completion record was received. Cause and remote child termination
are unknown. Conservatively apply the user's SSH fail-stop rule: zero further
8p connections, retries, epochs, GPU switches or launches. This continuation
performed no CUDA build or GPU execution. Local review, evidence preservation
and publication of an explicitly incomplete state do not resume the campaign.

Independent local review additionally found an unvalidated race/lock-lifetime
boundary in guarded process-subtree teardown. A non-overridable hard block now
precedes GPU admission in run_smoke.py. Mock tests are not Linux proof. Device
and task lock descriptors are forwarded to the resource watchdog, but this is
not yet a validated teardown guarantee. Do not clear the launch block without
bounded Linux race/termination-failure/lock-lifetime regression evidence.
The native range-vs-kNN decision and GIST/Deep collision decision remain pending.
No old or new diagnostic observation is promoted to a paper result.
