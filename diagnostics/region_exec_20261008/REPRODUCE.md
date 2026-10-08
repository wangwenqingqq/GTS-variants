# REGION_EXEC reproduction

## Dependencies and frozen inputs

Use a CUDA 13.1 SM120 Linux host with Python/NumPy, the original GTS
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639` source and the already-qualified lean
U10 adapter from `ab742e274037bb77e772c6add19ba93d9c62c05d`.
No new benchmark framework or library installation is required.

The public snapshot retains code, all process summaries and hashes, not raw
input/binary-output/profiler files. Supply the existing external frozen U10
snapshot (native integer-valued fixture, events, oracle and baseline source).
This is therefore **not a data-free one-command fresh-clone reproduction**.
Verify the three input hashes in `evidence/v2/REGISTERED.json` before running.

Set portable paths:

```sh
export REGION_CODE="$REPO_ROOT/diagnostics/region_exec_20261008"
export RAW="$CAMPAIGN_ROOT/gts_10k_recovery_20261004"
export WORKFLOW="$CAMPAIGN_ROOT/gts_10k_workflow_20261004"
export U0="$CAMPAIGN_ROOT/gts_claim_closure_20261003"
export HELPERS="$CAMPAIGN_ROOT/controllers/attribution_20261008"
export DEST="$NEW_TASK_OWNED_RUN_DIRECTORY"
export GPU="$VERIFIED_IDLE_GPU_UUID"
```

The guard binds NUMA3, matching the measured GPU. Verify/reconfigure the guard's
NUMA mapping for another GPU; do not assume any idle device has that topology.
Inspect active users/processes, preserve other jobs, and keep the existing dual
GPU locks. Do not change clocks, shared service state or compute mode.

## Build and validate

```sh
python "$REGION_CODE/run_region.py" prepare --raw "$RAW" --workflow "$WORKFLOW" \
  --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
python "$REGION_CODE/run_region.py" qualify --raw "$RAW" --workflow "$WORKFLOW" \
  --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
python "$REGION_CODE/qualify_structural.py" --raw "$RAW" --dest "$DEST" --gpu "$GPU"
```

The structural controller runs `"$DEST/native_timed/test_region"` normally and
under memcheck/racecheck/synccheck through the locked runner, recording all four
results in `STRUCTURAL.json`. It is not legitimate to set `passed=true` without
those receipts.

The handoff's frozen clean rebuild checks identical source hashes against
`evidence/v2/SOURCE.json`. New build-path/container hashes may differ because of
embedded paths/line information; do not reuse the old measured binary hash for
a new build. Matching source hashes and smoke outputs do not establish exact
selected-kernel SASS identity.

## Primary campaign and append-only diagnostics

Run `campaign` only in a fresh qualified namespace. It registers the six orders,
does 48 observer qualification processes and then exactly 24 primary processes.
It rejects existing campaign registration rather than overwriting evidence.

```sh
python "$REGION_CODE/run_region.py" campaign --raw "$RAW" --workflow "$WORKFLOW" \
  --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
```

`finish_closure.py` appends three PAR sanitizer checks and three full-trace
counter controls after completion. `profile_closure.py` appends four small
diagnostic profiles using the absolute profiler launcher. These programs use
one-time fresh labels and must not be blindly rerun in the same namespace.
Their times never enter the primary estimator.

```sh
python "$REGION_CODE/finish_closure.py" --raw "$RAW" --workflow "$WORKFLOW" \
  --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
python "$REGION_CODE/profile_closure.py" --raw "$RAW" --dest "$DEST" \
  --helpers "$HELPERS" --gpu "$GPU"
python "$REGION_CODE/test_closure.py"
c++ -std=c++17 -O2 -I "$REGION_CODE" "$REGION_CODE/test_plan.cpp" -o "$TMPDIR/test_plan"
"$TMPDIR/test_plan"
```

The publication auditor consumes a private evidence directory containing the
frozen data/events/expected files plus original outputs, registrations and
receipts. `--output` must name a new curated directory. Inspect its exact file
set and history before uploading; keep raw/curated hashes distinct.

## Stop and rollback

Never signal a foreign process. A guard stops only its own process group on
timeout/foreign activity and retains the failed receipt. Stop expansion when
the region execution does not improve the strong baseline, as in this first
campaign. Preserve both rejected candidates and all measured rows; reverting
dispatch means selecting NATIVE/PAR_STRONG, not deleting evidence or rewriting
history.
