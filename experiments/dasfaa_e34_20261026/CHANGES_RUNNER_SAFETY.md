# Corrected E4 runner safety adaptation

## Changes and reasons

- Reuse the prior runner's advisory locks, GPU idle predicate, trailing-NVML-window
  settling, parent/start-time ownership checks, and pidfd-bound signaling.
- Replace its unsafe automatic epoch retry and subsecond NVML loops. All errors
  latch `STOP_CAMPAIGN.json`; telemetry failure reads `/proc/meminfo` before
  recording evidence and prevents any later NVML call in that process.
- Every telemetry and benchmark/oracle child is wrapped in the shared, read-only
  resource guard, with RSS 16 GiB, minimum available memory 48 GiB, and bounded
  timeout. Admission additionally requires 64 GiB available host memory.
- NVML uses `timeout 10`; complete two-query snapshots are spaced at least 30 s.
  Admission and settling share the same cadence, rather than resetting it. The latest monotonic snapshot timestamp
  persists across successful step invocations.
- Reuse the guard module's descendant enumeration and the existing runner's
  pidfd signaling, so aborting a guard does not abandon its separately sessioned
  benchmark child. No process is selected by name, and no foreign PID is signaled.
- Require `E34_BUILD_DIR` and its corrected build manifest. Old binaries and old
  tree caches cannot enter a corrected epoch. The corrected builder disables
  cache loading and writing entirely; the legacy cache CLI argument is inert.
- N>10M and declared tree height >=8 are recorded as infeasible for P and never
  executed. Scan-only scale points remain in the complete matrix.

## Bounded execution protocol

Set `GTSPP_GUARD` to the verified host-local shared guard path; no device
configuration is embedded in this portable runner.

Use an outer resource guard with timeout at most 900 seconds for each invocation:

```text
E34_BUILD_DIR=<corrected-build> python campaign.py <root> init
E34_BUILD_DIR=<corrected-build> python campaign.py <root> step <explicit-epoch>
```

`init` creates exactly one corrected epoch, admits one GPU, and freezes the full
plan plus source/build/input-verification identities. Each successful `step` executes at most one
benchmark/oracle child, with an inner timeout of 600 seconds, and writes one
append-only checkpoint. It reacquires the same device lock and checks the same
UUID. It never chooses a different card or replaces a failed observation.

The 600-second inner limit reserves time for admission/settling under the
900-second outer limit. If the outer supervisor is killed unexpectedly, its
separately sessioned inner resource guard remains alive to enforce the original
RSS/memory/time bounds; normal abort explicitly terminates verified children
and waits for the still-live guard to reap them; it never disables the watchdog
before cleanup. A stopped epoch is not automatically resumable.

Before each step, runner, safety helper, resource guard, scan, audit, data manifest,
input-verification report, boot ID, build manifest, plan, and corrected binary hashes must match the initialization freeze.
Full-load oracle payload hashes are verified against the frozen input report before
every use. Each newly generated bounded oracle freezes its payload hash immediately
and verifies it before every subsequent use. Oracle mutation is a terminal error.
Commit/freeze all implementation changes before `init`.

## Validation

`python3 experiments/dasfaa_e34_20261026/test_campaign_safety.py` passes twelve
CPU-only tests: guard limits, scale exclusion, telemetry timeout/latch ordering,
30-second cadence and timeout invocation, terminal exit codes 3/97/98, no epoch
retry, full matrix/order retention, PID reuse/watchdog-preserving termination, CPU guard,
available-memory preflight, cross-process polling cadence, and query-isolation exclusion. `py_compile` also passes.

A complete `resume_20261026/INPUT_CHECK.json` is required before initialization.
Cases whose exact-feature held-out check fails remain visible but neither arm
(nor their bounded-family sanitizer) is GPU-run. Completing the plan does not
claim these loads were measured.

No SSH, NVML, real signal, GPU program, sanitizer, or performance run was executed
by these tests. Hardware validation remains required. The planner currently
covers vector E4 P/S; optional G, Word and E3 need their separately frozen phase
adapters and are not reported as completed.
