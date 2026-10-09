# Same-semantics build-distance tiling

**Submission B plus the conditional internal part of C**, not a new tree
algorithm, an external dynamic ranking or a production/default promotion.
The frozen contract is in `CONTRACT.json`; the mechanism, added costs and Gate0
are in `DESIGN.md`. The measured delivery is in `REBUILD_E2E_RESULTS.md`.

Only scoring ownership changes: a large node gets multiple512-object CTAs.
The original node_slot, midpoint pivot, per-object arithmetic, sort/ties,
partition, query implementation and occupancy10 maintenance policy remain.
The flat grid needs no task array, GPU allocation, copy or new primary fence.
Diagnostic audit copies are disabled in all primary processes.

## Scope and gate boundaries

- Original FP32 GIST N1M/D960, B1/K8, radius bits0x3f34a3d8.
- Nine fixed paired qualification cases and four sanitizer processes:22 fresh
  processes, including root leaf, tail, repeated keys, mixed leaf/split, D128,
  GIST4096, bounded two-rebuild stress and N1M actual rebuild.
- Full defined keys/pids/sort/topology/refit identity and complete ordered
  answers precede the six fixed alternating B0B1/B1B0 primary pairs.
- Main denominator: continuous Host-ready/ACK336-event service,256 complete
  queries,40I/40D,2 rebuilds, all maintenance and final owned service release.
  Setup, warmup, parsing, context and disk serialization are separately scoped.
- Ordinary memcheck/racecheck/synccheck passes do **not** close the inherited
  unresolved96B/seven managed context-symbol full-leak diagnostic.
- No old18-process matrix rerun, threshold tuning, Tensor Core change, new
  profiler capture, external formal matrix, long workflow or default promotion.

## Reproduce with the existing environment

Use a clean checkout of the delivered commit and pinned upstream
`ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
The installed Python/NumPy, C++17/OpenMP, CUDA13.1/Thrust, cuobjdump,
compute-sanitizer and numactl suffice. No installation or shared setting change.
Choose an actually idle single GPU, verify its device-local NUMA node, and keep
all other users' processes untouched. The existing guard holds both GPU lock
aliases, watches descendants/foreign activity and stops only its own process
on timeout or interference. Its1200s budget is per pair, not a long-run budget.

Use fresh private scratch **outside this repository**. The original input is
3840000012 bytes including the12-byte header (D960/N1M/metric2), SHA256
`f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7`.
No raw dataset, audit arrays or input vectors are included in Git.

```sh
set -e
# Set absolute SCRATCH, UPSTREAM, DATA, NVCC, GPU and NUMA for this machine.
mkdir "$SCRATCH"
TOOLS="$PWD/artifacts/build_distance_tiles"
PARENT="$PWD/artifacts/unified_target_workflow/phase_b"
GUARD="$PWD/diagnostics/native_knn_faiss_ivf_20261003/run_locked.py"
python3 "$TOOLS/test_tiles.py"
python3 "$TOOLS/test_checks.py"
python3 "$PARENT/run.py" prepare --work "$SCRATCH/parent_build" --upstream "$UPSTREAM"
python3 "$TOOLS/run.py" prepare --work "$SCRATCH/build" --upstream "$UPSTREAM"
python3 "$TOOLS/run.py" build --work "$SCRATCH/build" --nvcc "$NVCC"
python3 "$TOOLS/run.py" cases --work "$SCRATCH/cases" --data "$DATA"
cuobjdump --dump-sass "$SCRATCH/build/bin/target" >"$SCRATCH/target.sass"
mkdir "$SCRATCH/oracle_build"
python3 "$PARENT/run.py" cpu-oracle --work "$SCRATCH/oracle_build" --data "$DATA"
cp "$TOOLS/campaign.py" "$SCRATCH/campaign_qualification.py"
cp "$TOOLS/verify.py" "$SCRATCH/verify_qualification.py"
python3 "$TOOLS/campaign.py" run --stage qualification \
  --work "$SCRATCH/qualification" --build "$SCRATCH/build" \
  --cases "$SCRATCH/cases" --data "$DATA" --gpu "$GPU" \
  --numa-node "$NUMA" --guard "$GUARD"
python3 "$TOOLS/verify.py" qualification --work "$SCRATCH/qualification" \
  --build "$SCRATCH/build" --parent-build "$SCRATCH/parent_build" \
  --cases "$SCRATCH/cases" --data "$DATA" \
  --library "$SCRATCH/oracle_build/cpu_oracle.so" --sass "$SCRATCH/target.sass"
# Only a passed, raw-evidence-bound proof admits these12 primary processes.
python3 "$TOOLS/campaign.py" run --stage primary \
  --work "$SCRATCH/primary" --build "$SCRATCH/build" --cases "$SCRATCH/cases" \
  --data "$DATA" --gpu "$GPU" --numa-node "$NUMA" --guard "$GUARD" \
  --admission "$SCRATCH/qualification/QUALIFICATION.json" \
  --qualification-driver "$SCRATCH/campaign_qualification.py" \
  --qualification-analysis "$SCRATCH/verify_qualification.py"
python3 "$TOOLS/verify.py" primary --work "$SCRATCH/primary" \
  --build "$SCRATCH/build" --cases "$SCRATCH/cases" --data "$DATA" \
  --library "$SCRATCH/oracle_build/cpu_oracle.so" \
  --admission "$SCRATCH/qualification/QUALIFICATION.json" \
  --qualification-driver "$SCRATCH/campaign_qualification.py" \
  --qualification-analysis "$SCRATCH/verify_qualification.py"
```

The fresh recipe uses the independent ordered-FP64 CPU oracle for N1M answers.
The recorded campaign instead reused the already exhaustive-qualified phase-B
parent **after checking its locked quality, registration, rows, round1 guard
and actual full payload hashes**; the51-event prefix and complete warmup match
that parent's actual outputs. To revalidate those exact recorded receipts,
provide the archived parent primary as `--parent`, archived qualified parent
build as `--parent-build`, its qualified CPU library, and the original
qualification runner via `--executed-driver`. Their identities, including the
original qualification analysis, are retained in curated proofs; older raw
scripts/receipts are private evidence, not silently replaced by hardened code.

A clean source prepare must reproduce all candidate source hashes. Whole
binary hashes include Host/container/build-path effects; all112 original GPU
functions are separately identical under the frozen SASS normalization. The
only added GPU function is getPivotDisTiled. Static code/resource identity is
not measured occupancy, traffic, dynamic instructions or workflow speed.

## Evidence, failure and publication

`verify.py` checks exact jobs/order, guards, actual execution modes, scopes,
source/binary, case hashes, full ordered payload sizes, operation states,
releases and sanitizer summaries. Layer checking compares all defined binary
state and validates original node slots plus disjoint owned intervals. Empty
unowned TN storage and unwritten pivots are explicitly masked; masking never
changes GPU state. Primary output identity is checked for every process.

All raw observations and unfavorable results are retained. Failed execution
stops; a failed build or pre-GPU launcher failure is not counted as a successful
process or replaced timing sample. `ATTEMPTS.md` records those repairs.
`curate.py` publishes a whitelisted hash/statistics package, not raw vectors,
credentials, device configuration, private paths or manuscript. Recorded
metadata and hardened delivery/replay code are distinct states.
