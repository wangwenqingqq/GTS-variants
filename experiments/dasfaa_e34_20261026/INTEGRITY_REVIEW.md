# Pre-launch integrity and safety review

Reviewed 2026-10-26 UTC. Verdict: **CLEAN within this implementation-review scope; hardware and performance conclusions remain unvalidated.** This is not a complete forensic audit of every historical session log, nor approval to retry a failed campaign. No remote command, NVML query, signal, GPU task, sanitizer, or timing was run by this reviewer.

## Scope and immutable evidence

Read the supplied E4/E3 continuation, frozen contract, append-only amendments, safety helper, bounded campaign, approved source adapter/builder, vector harness, input verification, summarizer, and local regressions. Historical incident epochs are excluded from corrected results. The original files remain identical to the frozen commit:

| File | SHA256 |
|---|---|
| CONTRACT.md | `1a2ba4313b819807d54575868652b01ad47168220686f86dc361763e040bab30` |
| audit.py | `74f3a71b0309b675b1c78e35cdb0c98d5ce0d6cbc17ce23f0756ba2ebe65890c` |
| DATA_MANIFEST.json | `c8ad2cbedfc923054fcd1e7eeba5b2d067df029520a08a9bf38ad6dcdde807f8` |

The reviewed campaign/safety hashes are `cf35b5bcad2baa65e83a8879e78b5afe7d8a607e013cad598af7f2a250470c68` and `b759aa687e9d8f346333de9ee52e9627bd36bced58659656bfe58236a83769a8`. Any later changes require a new freeze/review before initialization.

## Findings and disposition

1. **INFO — approved P source boundary preserved.** `adapt.py:84–92` checks the exact archived P/G hashes and strictly applies every patch context. `test_patched_sources.py` removes only WORK statements from instrumented P and compares all other non-whitespace tokens with the approved patch. The prohibited `le=qe+1` change is absent. This establishes source provenance, not GPU correctness or complete counter attribution.

2. **INFO — terminal safety conditions no longer trigger a retry.** `campaign.py:298 onward` exposes only explicit init/step operations, latches FAILED/STOP on in-campaign exceptions, and rejects failed epochs/new corrected epochs. `lock_support.py:85–125` uses guarded `timeout 10 nvidia-smi`, records host meminfo first on telemetry failure, then blocks later telemetry in that process. All nonzero guarded job codes, including 3/97/98, are terminal. There is no automatic epoch/card replacement.

3. **INFO — locks, cadence, and scale boundaries preserved.** Each GPU step reacquires the same advisory device lock and task lock and checks the frozen UUID. Snapshot cadence is persisted between successful steps and is >=30 seconds; a snapshot contains the two necessary GPU/app queries. Infeasible P loads and isolation-blocked loads remain in the plan and do not acquire/launch GPU work. P/G N>10M cannot be searched. G is compile-only and unsupported by the execution planner; the native signed-int workspace risk is explicitly disclosed, not presented as a measured failure.

4. **WARNING, corrected before launch — complete-output loophole.** Frozen `audit.py` accepts either 1000 or 1024 rows independently of requested Q. The initial caller therefore could have accepted a truncated Q1024 result. `campaign.py` now requires exact output byte count (1024*8*4 for Q1024, 1000*8*4 otherwise) before the frozen auditor. No evaluator edit was made. This was found before a corrected GPU launch, not after selecting a favorable result.

5. **WARNING, corrected before launch — mutable oracle identity.** The initial runner froze the input-report hash but did not rehash each oracle at use. Current `verify_oracle` checks the exact independently recorded full-oracle hash or the newly generated bounded-oracle manifest before launch and again before auditing. The mutation regression covers both paths. Final closure should still reverify full data/prefix hashes; the per-step identity is not a continuous filesystem immutability guarantee.

6. **WARNING — bounded supervisor-failure behavior, not an absolute no-orphan guarantee.** Normal abort signals only PID/start-time-verified descendants and keeps the inner watchdog alive until it reaps its separately sessioned child. An unexpected outer-supervisor SIGKILL can leave that inner watchdog/child alive temporarily. The inner watchdog still enforces 16 GiB RSS, 48 GiB memory floor, and 600-second job budget; compiler children use 240 seconds, and the outer invocation is <=900 seconds. This independent watchdog is intentional containment, not evidence that all descendants vanish instantaneously under every host/kernel failure. After any outer guard97/98, failed SSH, or lost telemetry, the operator must stop and retain evidence, never launch another step/epoch. The documents disclose this limitation.

7. **INFO — matrix and negative evidence are not hidden.** The planner retains all requested vector N/Q and all six alternating process rounds. Exact-value-overlapping Deep loads remain isolation-failed; larger P loads remain workspace-infeasible; scan-only loads are retained. The summarizer excludes all timings from failed epochs and reports missing comparisons as unknown rather than story B. It labels real versus synthetic spatial populations and the native FAISS64 plus timed FP64 candidate-refinement adapter. No held-out-dependent parameter tuning, result replay, hardcoded winners, or fabricated timing was found in the reviewed code.

8. **INFO — Word parser failure handled without source mutation.** The real-source ASCII decode failed before artifacts. The revised parser matches native byte/LF/strlen object semantics rather than dropping/replacing non-ASCII bytes. Its fixed permutation remains unchanged. Word preparation/oracle code was edited by this reviewer, so its local smoke is not an independent second-agent implementation audit; the primary executor must review the exact diff and real-data manifest before use.

## Local checks rerun

- `python3 test_campaign_safety.py`: 12 tests passed, including terminal codes, no retry, 30-second persisted cadence, full plan/order, PID reuse, skipped-workload GPU exclusion, oracle mutation, and memory preflight.
- `python3 test_patched_sources.py`: 5 tests passed.
- `python3 test_local.py`: passed audit/statistics checks.
- `python3 verify_inputs.py --test`: passed overlap/signed-zero/nonfinite checks.
- `python3 test_word.py`: CPU oracle compiled and independent full-table checks passed, including non-ASCII bytes, native NUL prefix semantics, ties, complete outputs, and collision reporting.

These checks permit proceeding to a **bounded hardware smoke under the unchanged safety policy** after the primary executor freezes the reviewed files and verifies the actual host/build/input identities. They do not satisfy sanitizer, full-size correctness, six-process paired timing, final evaluation, or remote-publication gates.
