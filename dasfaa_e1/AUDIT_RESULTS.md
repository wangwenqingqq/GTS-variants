# E1 continuation: independent, scope-limited prelaunch audit

## Verdict

**No fabrication or evaluator tampering was identified in the reviewed local
files. This is NOT a full-session CLEAN verdict and does not clear GPU launch.**
Two launch blockers remain: Linux process-tree teardown validation, and the
P/G executed-query-path decision. No CUDA build, sanitizer run, smoke result,
full-load evaluation, or performance claim is validated by this audit.

## Scope and checks

The auditor did not run the remote campaign and performed no SSH, NVML or GPU
actions. Review covered `gpu_guard.py`, `run_smoke.py`, `dynamic.cu`, `case.hpp`,
`prepare_native.py`, `prepare_inputs_v3.py`, the frozen contract/amendments,
related tests, and the locally retained partial inventory. Full session logs
were not exhaustively reviewed; remote state and process termination after the
reported SSH exit 255 were not independently verified.

- `CONTRACT.md` is byte-identical to the committed version. SHA-256:
  `36d1d270a5e536d20a3614206fd847d577491e7221bbd4fe6421548ca75ddd28`.
- The local test suite passed **22/22** during this audit. These include a real
  local C++ parser check but mock process teardown; they are not Linux/CUDA
  runtime proof. `git diff --check` passed.
- New P/G adapter outputs explicitly say `timing_eligible=false` and
  `native_static_knn_executed=false` (`dynamic.cu:155`). Prior P/G observations
  are explicitly invalidated in the append-only amendments.

## Remaining findings

### 1. WARNING — Linux teardown is not yet safe to promote

`gpu_guard.py:163-183` preserves the resource watchdog while discovering and
signaling its descendants, fixing the original watchdog-orphaning hazard.
However, it neither checks that SIGSTOP succeeded nor confirms all relevant
threads actually stopped before treating identical immediate descendant lists
as stable. A late fork can escape the final list. `p.wait()` proves the watchdog
exited, not that every descendant is absent. If cleanup returns false,
`run_smoke.py:78-83` records that fact but its outer `finally` releases device
and task locks even though a guarded task may remain alive.

Required before GPU admission: a bounded Linux test with a separate-session
sanitizer-like wrapper, absent `result.pid`, late child creation, and termination
failure. Demonstrate verified subtree completion and lock ownership for the
whole cleanup interval. Until then, enforce a hard pre-admission block rather
than representing mock tests as operational safety validation.

### 2. WARNING — patched static kNN is not the executed P/G path

`prepare_native.py:46-61` derives both mandated static `search_v2.cuh` patches
with exact source/patch hashes and explicitly marks them unexecuted. The actual
adapter calls `searchIndexRnnUpdate` (`dynamic.cu:78-98`), then exact delta scan
and host top-k selection. It retains the documented archived C1 range-update
contrast but does not exercise repaired native static kNN.

This boundary is disclosed, not concealed. Do not label these binaries as
having executed the corrected native kNN path or promote their diagnostic
results to the requested decision-grade comparison without resolving the user
choice. The range path separately needs an independent complete-output audit.

### 3. INFO — partial inventory is not a completed dataset audit

The retained inventory contains four SureChEMBL snapshot records with hashes,
then the owner reports SSH exit 255. It contains no completed ChEMBL37 or
protein200k hash/count record and no `inventory_complete` record. This does not
establish host failure, root cause, remote completion, or child termination.
The owner stopped without reconnecting; no new GPU/build launch is reported.
Retain these facts and uncertainties without upgrading file-size-derived counts
or old metadata into a freshly completed audit.

## Corrections verified during review

- Mandatory 3/97/98 exits are checked before optional/possibly truncated summary
  JSON parsing (`run_smoke.py:87-97`); no later NVML access precedes this latch.
- Header read-success and 10M/int32 limits now precede payload allocation
  (`case.hpp:23-33`).
- T-loc grid bounds now use the original corpus, not the query-excluded subset
  (`prepare_inputs_v3.py:67-76`), matching the frozen ordering definition.
- GIST/Deep native-query feature collisions remain explicit input-contract
  blockers; no unapproved collision removal was found.

## Claim boundary

Allowed wording: local implementation/static regressions improved, the original
contract is unchanged, and this continuation stopped after an unresolved SSH
failure before new GPU validation. All required measurement gates and paper
contribution decisions remain unvalidated or undecided, not failed by inference.

## Post-review: publication checkpoint (local only)

The updated runner now hard-blocks `main()` at `REMOTE_LAUNCH_READY=False`
before NVML/admission (`run_smoke.py:12-14,142-143`). Device/task lock FDs are
passed to the watchdog (`run_smoke.py:65,179-181`); therefore closing the parent
handles alone no longer proves lock release while that watchdog is alive.
This is a code-level mitigation, **not** validated Linux teardown/lock-lifetime
behavior. The two launch blockers above remain. The updated local suite passed
**23/23**, including the pre-admission launch-block check.

The proposed named publication set was reviewed: code/tests, archival/derived
sources, patches/provenance, curated summaries and partial inventory. No
credentials, raw-conversation records, private SSH configuration, or AI
attribution were found in that prospective set. The generic `ControlPath`
option name in the amendment is a protocol description, not a disclosed host
configuration. Raw logs, the local notebook, `.hillclimb/`, `legacy_oob.cu` and
`audit_legacy_trace.py` are excluded. No remote/GPU action was performed by this
auditor. This is not an anonymous-artifact or full-history-clean certification;
the corresponding repository is already public and nonanonymous. Publication
must preserve the explicit stopped/unvalidated status and may not turn this
checkpoint into a completed experimental result.


## 2026-10-26 resumed-session independent safety review

Verdict: **GPU hard block must stay enabled; no full CLEAN integrity verdict.**
Read-only reviewer identified standalone guard killpg session escape, outer
watchdog bypass, unbounded cleanup quarantine, post-Popen/PID-file cleanup
exceptions, and mandatory97/98/3 latch loss on simultaneous cleanup errors.
Later local code addresses the last exception/latch findings and attempts to resume the
watchdog in quarantine; these corrections are local-test-only and were not the
exact source in the earlier Linux fixture. Fundamental containment blockers
remain. The fixture pre-created its delayed orphan before cancellation, so it
is not proof of concurrent-fork teardown. Its positive verdict is restricted
to runner cancellation and inherited-lock composition.

The resource stop was observed as upload97, then the existing inventory SSH
returned98. No post-trigger remote action or retry, build or GPU launch occurred.
No frozen contract/oracle/threshold changed; missing results remain N/A.
Curated receipts and exact tested sources are in evidence/resume_20261026_0450.
Full inventory data and final outer guard receipts were not fetched after STOP.


Final local checkpoint-publication review found no publication blocker in the
named staged set. It verified unchanged contract, matching tested/source hashes,
truthful97/98 ordering boundaries and exclusion of legacy probes. This does not
clear GPU admission or issue a full CLEAN integrity verdict. Quarantine only
attempts SIGCONT; its success is not guaranteed, reinforcing the hard block.
