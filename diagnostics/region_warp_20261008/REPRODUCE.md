# REGION_WARP reproduction

## Frozen dependencies

Use CUDA 13.1.115 / SM120 and Python with NumPy. Reuse the parent REGION_EXEC
external U10 input/source/runner snapshot: original GTS
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639` and lean adapter
`ab742e274037bb77e772c6add19ba93d9c62c05d`. The public repository does not carry
raw inputs or full binary outputs; this is **not a data-free one-command
fresh-clone reproduction**. Check `evidence/v2/REGISTERED.json` input hashes.

```sh
export CODE="$REPO_ROOT/diagnostics/region_warp_20261008"
export RAW="$CAMPAIGN_ROOT/gts_10k_recovery_20261004"
export WORKFLOW="$CAMPAIGN_ROOT/gts_10k_workflow_20261004"
export U0="$CAMPAIGN_ROOT/gts_claim_closure_20261003"
export HELPERS="$CAMPAIGN_ROOT/controllers/attribution_20261008"
export DEST="$NEW_TASK_OWNED_RUN_DIRECTORY"
export GPU="$VERIFIED_IDLE_GPU_UUID"
```

Inspect users/processes and lock the selected device. The retained runner binds
NUMA3 for the measured GPU; verify the mapping before choosing another GPU.
Never signal foreign processes or change clocks/compute mode. Every phase
refuses changed or existing run identities instead of replacing failed runs.

## Build and qualification

```sh
python "$CODE/test_warp_cpu.py"
python "$REPO_ROOT/diagnostics/region_exec_20261008/test_closure.py"
for phase in prepare qualify micro; do
  python "$CODE/run_warp.py" "$phase" --raw "$RAW" --workflow "$WORKFLOW" \
    --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
done
```

`prepare` builds one five-mode primary executable, a separate counter executable,
the retained structure test, the direct ownership test and the bounded micro.
`qualify` runs SERIAL/WARP structural tests and direct ragged cases normally and
with memcheck/racecheck/synccheck; it also checks mixed update traces and five
full counter streams. Diagnostic times never enter the primary estimator.

The opportunity parser needs the missing epoch/region/physical-object map.
Use the retained independent diagnostic counter log and its exact parent work
log, rather than selecting new queries or changing the radius:

```sh
python "$CODE/leaf_distribution.py" --log "$OPPORTUNITY_LOG" \
  --parent-work "$PARENT_WORK_LOG" --output "$DEST/LEAF_DISTRIBUTION.json"
```

After inspecting inventory, repaired micro and qualification, create
`$DEST/ADMISSION.json` with the explicit decision (`continue` or `stop`), reason,
scope caveats and `evidence_sha256` entries for `SOURCE.json`, `VALIDATION.json`,
`LEAF_DISTRIBUTION.json`, `MICRO.json`. The campaign checks all four hashes and
binds the admission receipt in registration. The published receipt is an example
of a **decision**, not transferable qualification for a new binary or dataset.

## Fixed campaign, audit and publication

```sh
python "$CODE/run_warp.py" campaign --raw "$RAW" --workflow "$WORKFLOW" \
  --dest "$DEST" --u0 "$U0" --helpers "$HELPERS" --gpu "$GPU"
```

The controller performs six alternating observer on/off pairs per mode and
admits observation only if every mode has identical outputs and paired upper95
overhead <=1.03. If rejected, all formal processes use observation OFF and tails
are unavailable; rejection is retained. It then runs exactly the six registered
orders (30 processes), validating complete outputs after every process.

For independent auditing, copy (do not replace) the three frozen input files
into the private evidence root beside SOURCE/REGISTERED and retained output,
registration and guard directories. Then:

```sh
python "$CODE/audit_warp.py" --qualification --raw "$PRIVATE_EVIDENCE" \
  --output "$PRIVATE_EVIDENCE/QUALIFICATION_AUDIT.json"
python "$CODE/audit_warp.py" --raw "$PRIVATE_EVIDENCE" \
  --output "$PRIVATE_EVIDENCE/INDEPENDENT_AUDIT.json"
python "$CODE/curate_warp.py" --raw "$PRIVATE_EVIDENCE" \
  --output "$PUBLIC_EVIDENCE" --phase qualification
python "$CODE/curate_warp.py" --raw "$PRIVATE_EVIDENCE" \
  --output "$PUBLIC_EVIDENCE" --phase results
```

Every ordered ID/FP32 output is independently checked against an integer
squared-L2 live-multiset replay; order, guard receipts and paired statistics are
recomputed. Whitelist curation records both raw and portable hashes. Review the
exact staged files and full outgoing history before uploading. Preserve negative
results and stop this mapping trial without automatically increasing budgets,
changing seeds or expanding the matrix. Rollback means selecting PAR_STRONG or
SERIAL, not deleting evidence.
