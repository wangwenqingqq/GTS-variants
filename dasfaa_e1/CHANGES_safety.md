# E1 Linux supervision candidate — not GPU-admitted

## Changes

- Keep the GPU hard block enabled.
- Require the serialized runner to become a Linux child subreaper before launching
  work. This keeps orphaned and separate-session descendants visible to the runner.
- Bind signals to verified process identities using the existing pidfd path.
  Freeze the watchdog and verify every thread is stopped before traversing,
  freezing and killing its task subtree. Resume the watchdog only after all
  owned task parents are stopped, then reap and verify complete process absence.
- Treat failed STOP/KILL, unreadable ownership or an unverified surviving process
  as incomplete cleanup. A watchdog exit alone is not a cleanup pass.
- Inspect adopted survivors after normal watchdog exit before returning to the
  lock-releasing path. Retain incomplete-cleanup evidence and do not report a
  correctness or performance pass.
- Add CPU-only integration fixtures for separate-session and delayed/orphaned
  forks, an absent result.pid, inherited device/task lock lifetime, and injected
  signal failure. These fixtures never intentionally trigger resource guard
  refusal/kill, experiment fail-fast, GPU work or NVML.

## Local validation

`python3 -m unittest discover -s dasfaa_e1/tests -p test_safety.py -v`
passed 11/11 tests on the local host. These are static/mock/parser tests, not
Linux runtime proof. The Linux integration test was authored locally and must
be executed under the authoritative resource guard by the campaign owner.

## Linux command

Run from the copied E1 directory, under the authoritative resource guard with
RSS <=1 GiB, minimum available memory >=48 GiB and timeout <=120 seconds:

```text
python3 test_linux_guard.py --resource-guard <authoritative-guard.py> --out <new-evidence-directory>
```

Internal payloads self-expire after 12 seconds. Their ordinary cancellation is
expected to make the inner watchdog return a killed-child status, not 97/98/3.
Every inner watchdog must retain an `end` receipt. A failure is a failed safety
gate, not authorization to launch GPU work or automatically retry experiments.

## Material unresolved boundary

The authoritative standalone resource guard uses killpg on its original child
process group; it does not contain descendants that create separate sessions.
An outer guard timeout/SIGKILL can bypass Python runner cleanup. Successful
runner-cancellation tests therefore do **not** establish standalone timeout,
RSS, daemon-escape or runner-death containment.

`hold_failed_cleanup` deliberately does not unwind through the lock-releasing
finally while ownership/termination is uncertain. This can hold indefinitely
and is not a bounded production solution under an outer watchdog deadline.
The candidate is consequently **not production-cleared**. Keep the GPU launch
block until the campaign owner obtains and validates a sound containment design
(or explicit user-authorized E1-only hardened guard); do not edit the shared
resource guard or claim this candidate solves that boundary.


## Follow-up local corrections after the narrow Linux composition test

The following source changes were made after the campaign owner's Linux test
and are **not Linux-runtime-validated** by that earlier receipt:

- Move all post-Popen ownership inspection inside the cleanup-protected scope.
- Remove dependence on optional result.pid parsing for runner ownership/cleanup.
- Latch mandatory 3/97/98 exits even if a simultaneous cleanup/identity error
  was recorded; cleanup does not erase the original guard exit.
- Attempt to resume the resource watchdog when entering incomplete-cleanup quarantine;
  logging/proc/interrupt exceptions cannot unwind through the unlocking finally.

The quarantine remains an unbounded fallback, not an approved production path.
The standalone/outer-watchdog containment boundary and GPU launch block remain.
The campaign owner's narrow fixture pre-created the delayed/orphaned child
before cancellation; it does not prove a fork concurrent with teardown.
The campaign subsequently reached a mandatory guard-97 stop; no new remote
validation or automatic retry is authorized by these local corrections.

Latest local safety validation: **13/13 tests passed** after these corrections;
`git diff --check` passed. No SSH/GPU/NVML action was performed by this worker.
