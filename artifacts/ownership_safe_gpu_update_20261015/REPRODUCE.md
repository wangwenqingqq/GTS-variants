# Reproduction and custody

## CPU-only public verification

From the repository root(with Python,NumPy and a C++17 compiler already available):

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 artifacts/ownership_safe_gpu_update_20261015/test_evidence.py
python3 artifacts/ownership_safe_gpu_update_20261015/verify.py
OUT=$(mktemp -d)
python3 artifacts/ownership_safe_gpu_update_20261015/model.py --out "$OUT/model.json"
c++ -std=c++17 -O2 artifacts/ownership_safe_gpu_update_20261015/test_plan.cpp -o "$OUT/test_plan"
"$OUT/test_plan"
```

These checks initialize no CUDA context. `verify.py` reconstructs the complete public process statistics,checks all source and manifest hashes,and regenerates the exact executed GPU adapter/client text. Aggregate floating-point reconstruction alone permits finite roundoff within1e-12 relative/absolute tolerance;structures,types,integers and hashes remain exact. This is not a change to any experiment decision or GPU quality tolerance. It does not rerun GPU queries or independently replace the private full-vector oracle.

## Inputs and frozen dependencies

- Parent source commit: `85b56c7607ec6fd65b3ab535bc9f90bf447e1073`. The unchanged query and native-update parents remain under `artifacts/dynamic_query_aware_exact_gpu_20261015/` and `artifacts/dynamic_update_critical_path_20261015_recovery_01/`;their manifests are pinned in CONTRACT.json.
- GIST1M FP32 container and inherited W2 victims,incoming vectors,means,query IDs and FP64 reference caches remain external. `evidence/INPUT_IDENTITY.json` supplies portable paths,byte sizes and SHA256 hashes. No restricted raw vectors,answers or checkpoints are in Git.
- `evidence/BUILD.json` contains every executed compiler flag and environment value with installation roots replaced by variables. Bind those variables to the matching CUDA13.1,cuVS,RMM,logger,NVTX and dependent runtime installations. `evidence/IDENTITY.json` records every resolved shared-library hash,both independent replay-library hashes,six GPU binary hashes and query SASS identities. Do not substitute a different library/toolchain while calling the result an exact replay.

## An explicitly authorized fresh GPU campaign

GPU commands are documentation,not an automatic continuation or permission to consume a shared card. Verify the device is idle,select its matched NUMA node,preserve other users' processes,and create a new work directory. Do not alter GPU settings.

```sh
python3 artifacts/ownership_safe_gpu_update_20261015/prepare.py \
  --parent "$PINNED_PARENT_WORK" --work "$NEW_WORK" \
  --gpu "$IDLE_GPU" --numa "$NUMA_NODE"
for stage in qualification screen primary shapes calibration profile; do
  python3 artifacts/ownership_safe_gpu_update_20261015/campaign.py \
    --work "$NEW_WORK" --stage "$stage" || break
done
python3 artifacts/ownership_safe_gpu_update_20261015/analyze.py \
  --work "$NEW_WORK" --out "$NEW_WORK/TIMING.json"
```

The clean schedule has340 target invocations. Source,quality and input checks are fail-closed;the screen must support expansion. The first failed source/isolation/runtime/quality gate stops execution. Do not automatically retry or copy this historical campaign's budget amendment into a new campaign. The strengthened public validator adds independent physical-ledger checks outside GPU timers;GPU source generation remains identical to the recorded binaries.

## Exact interrupted-history audit

The published result is the specific341-attempt history,not a silently relabelled clean run:

1. Original16 qualification targets were retained after a CPU callback-count false alarm. The original runtime validator is preserved as `evidence/INITIAL_VALIDATOR.py`;the single-line continuation validator is preserved as `evidence/CONTINUATION_VALIDATOR.py`.
2. The approved `resume.py` admitted those16 offline and ran only26 remaining qualification targets. No existing GPU sample was rerun.
3. The original primary stage retained44 passed samples plus one foreign-activity invalid attempt. The approved same-card `resume_primary.py` replaced only that invalid target,ran147 unexecuted primary targets and the remaining100 shape/calibration/profile targets. Its only frozen-contract override is the authorized launch budget340→341;the original file remains unchanged.
4. The historical curator must run from the **unmodified recorded `code_final` snapshot**,not the current public source tree. The recorded registration binds the INITIAL validator;`--validator` selects the approved continuation checker for output revalidation but does not bypass `prepared()` source hashes. The strengthened public checker therefore intentionally fails that historical preflight if substituted in place.

For the private custodian,on the preserved host with the original registered input/parent/library paths still available:

```sh
RECORDED_CODE="$RECORDED_ROOT/code_final"
RECORDED_WORK="$RECORDED_ROOT/work_final"
RECORDED_CONTINUATION_VALIDATOR="$RECORDED_ROOT/audit_code/artifacts/ownership_safe_gpu_update_20261015/quality.py"
python3 "$RECORDED_CODE/artifacts/ownership_safe_gpu_update_20261015/curate.py" \
  --work "$RECORDED_WORK" --validator "$RECORDED_CONTINUATION_VALIDATOR" \
  --out "$NEW_AUDIT_OUTPUT"
```

Use the closed final archive's `code_final` snapshot,which includes the registered execution sources and recorded postprocessing helpers,not only the earlier pre-GPU source archive. Check its files against ADMIN_MANIFEST before running;the historical `quality.py` hash must be `fc8cdfa387acc9ded06ef24d166955d9c3aee01fda2b138ea8429d0c2cb496fc` and the continuation checker hash must be `68019f5782d8e9341a7dd5921df53bcf9588e9343d6869da96c3a82c10eb9d2a`. Keep the output outside the preserved snapshot and do not overwrite any original record. An archive-only relocation also needs the original absolute registered data/parent/library paths restored in an isolated environment;rewriting the registration is not an exact-history replay.

The curator checks the complete start ledger,commands,guards,inputs,libraries,all full-query/final-state oracles,mutation-derived physical execution,profiler accounting and process statistics. It performs no GPU execution. A different/fresh history needs its own audit registration rather than pretending to be this one. `evidence/PUBLIC_SOURCE_BRIDGE.json` separately records publication-only verifier/narrative revisions;the recorded helpers remain intact in the private archive.

The original work tree and administrative/source snapshots are preserved privately. `evidence/RAW_MANIFEST.json` lists every raw work file except the explicitly empty advisory lock;`evidence/ADMIN_MANIFEST.json` binds the source archives,controllers,offline original-target reviews and logs. Private archive custody is separately checked against both manifests. Public receipts contain hashes/scalars only,not deployment addresses,physical GPU IDs,credentials or raw sessions.

## Limits that reproduction must retain

Keep events+release distinct from cold-start process wall time;keep primary call-return ACK distinct from synthetic submission+wait timing(which excludes local plan/set destruction). Keep profile and native observations separate. No total update DRAM,concurrent-reader,Graph,empty-index search,other-GPU,1B-vector or new-novelty admission follows from these scripts. See METHODS.md,NOVELTY_BOUNDARY.md and the claim-evidence ledger.
