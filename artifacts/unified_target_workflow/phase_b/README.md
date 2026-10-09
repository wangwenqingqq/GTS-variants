# Phase B: cloned warmup, fixed short workflow and static strong control

This separate overlay keeps phase A and every historical executable/evidence
unchanged. It changes the host executor, not any target GPU kernel. Read
`CONTRACT.json`, `ATTEMPTS.md` and the final result ledger separately: a frozen
pre-registration is not a completion receipt. A is staged GTS with common
numeric/safe-bound repairs, B adds PAR range execution, C changes FULL to BOUND.
No default, novelty, production or 10k-query claim is admitted by this folder.

## Prerequisites and private storage

Use existing Python/NumPy, a C++17/OpenMP compiler, CUDA/Thrust, compute-sanitizer,
numactl and the existing GPU guard. No installation is performed. Set `SCRATCH`
outside this publication checkout, `GIST_F32BIN` to the registered original
FP32 binary, and `GPU_UUID`/`NUMA_NODE` from a live idle-device/topology check.
Do not use a busy device, signal foreign processes or alter GPU settings.
All commands below start from the repository root. Never use Python `-O`.

```bash
B=artifacts/unified_target_workflow/phase_b
GUARD=diagnostics/native_knn_faiss_ivf_20261003/run_locked.py
python3 "$B/test_campaign.py"
python3 "$B/run.py" self-test
python3 "$B/run.py" prepare --work "$SCRATCH/build"
python3 "$B/run.py" build --work "$SCRATCH/build" --nvcc nvcc
python3 "$B/run.py" cases --work "$SCRATCH/cases" --data "$GIST_F32BIN"
python3 "$B/run.py" cpu-oracle --work "$SCRATCH/build" --data "$GIST_F32BIN" --cxx g++
```

The CPU oracle is an independent exhaustive row loop, not GPU/pruned reference
code. Its fixed compiler flags are `-std=c++17 -O3 -fPIC -shared -fopenmp
-ffp-contract=off -fno-fast-math -fno-associative-math -frounding-math`.
Each of eight threads requests FE_TONEAREST; IEEE FP64/53 bits are compile-time
requirements. Conformance compares full score bits with the pre-existing
sequential dimension-wise NumPy reference on nine GIST shape/query combinations
and extreme/nextafter/subnormal D128/D960 cases. `CPU_BUILD.json` binds compiler,
flags, source, library and `CPU_ORACLE.json`; the campaign refuses an unbound
library. This is reference qualification, not a GPU performance estimator.

## Qualification and observer admission

```bash
for STAGE in qualification observer; do
  python3 "$B/campaign.py" run --stage "$STAGE" --work "$SCRATCH/$STAGE" \
    --build "$SCRATCH/build" --cases "$SCRATCH/cases" --data "$GIST_F32BIN" \
    --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" --guard "$GUARD" || exit 1
  numactl --cpunodebind="$NUMA_NODE" --membind="$NUMA_NODE" \
    python3 "$B/campaign.py" check --work "$SCRATCH/$STAGE" \
    --cases "$SCRATCH/cases" --data "$GIST_F32BIN" --library "$SCRATCH/build/cpu_oracle.so" || exit 1
  python3 "$B/campaign.py" summarize --work "$SCRATCH/$STAGE" || exit 1
done
mkdir "$SCRATCH/admission"
cp "$SCRATCH/qualification/QUALIFICATION.json" "$SCRATCH/observer/OBSERVER.json" "$SCRATCH/admission/"
```

Qualification has 11 fresh processes: A/B/C restore, cold control, three 200 ms
scope injections, unsuppressed access memcheck/racecheck/synccheck and a million
clone/restore/rebuild memcheck. Warmup is an independent host/state clone with
19 events, eight queries and one actual occupancy-10 rebuild. All service owners
are released and reset before a fresh initial copy/build/epoch=1. Diagnostic
restore checks every original FP32 device byte; primary processes omit that
extra audit but use the same qualified restoration path. Final device service
release/sync is inside the continuous trace. File output, independent CPU oracle
and per-process CUDA-context teardown are outside. `cudaDeviceReset()` only
tears down this process's context; it is not a physical-GPU reset.

Observer admission is six fresh C processes, OFF/ON, ON/OFF, OFF/ON, on the exact
short events. Full payloads must match, each ON/OFF and the two-sided 95% paired
bootstrap upper bound must be <=1.05. Failure retains evidence and blocks
primary timing; it does not become a candidate performance loss.

Enhanced `--leak-check full` remains **unresolved, not clean**; preserve R1/R2,
the phase-A control and minimal one-managed-symbol reproduction. The supplied
access/synchronization sanitizer gate is a distinct scope. Do not suppress or
manually free managed symbols, call this a confirmed vendor bug, or promote a
long/production workload while this additional gap remains unresolved.

## Fixed primary budget, no rerun-to-win

```bash
python3 "$B/campaign.py" run --stage primary --work "$SCRATCH/primary" \
  --build "$SCRATCH/build" --cases "$SCRATCH/cases" --data "$GIST_F32BIN" \
  --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" --guard "$GUARD" \
  --admission "$SCRATCH/admission" || exit 1
numactl --cpunodebind="$NUMA_NODE" --membind="$NUMA_NODE" \
  python3 "$B/campaign.py" check --work "$SCRATCH/primary" \
  --cases "$SCRATCH/cases" --data "$GIST_F32BIN" --library "$SCRATCH/build/cpu_oracle.so" || exit 1
python3 "$B/campaign.py" summarize --work "$SCRATCH/primary"
```

Six rounds are ABC/CBA/BCA/ACB/CAB/BAC, with three baseline-before and three
baseline-after observations per pair; all 18 fresh processes are retained.
The existing 1200-second guard is unchanged. An own-campaign lock spans six
sequential three-process guarded rounds, with shared GPU locks and foreign-process
monitoring inside every round. A new occupant or failed guard aborts the campaign;
no extra accepted samples replace it. This grouping avoids timing out an entire
18-process campaign and is not a different sampling/estimator contract.

The continuous trace includes all 336 events (128 range, 128 kNN, 40 insert,
40 delete), two real rebuilds, complete Host-ready answers, ACKs, maintenance,
update-buffer preparation and final release. Parse/context/clone warmup/fresh
setup and process-context teardown are distinct boundaries. Bootstrap uses
paired log ratios, 20,000 resamples, seed 202610090242. Ratios >1 favor the
candidate. CI crossing 1 or reversal between order strata is inconclusive.
Nested stage medians must not be added to fabricate a total.

Offline checking/summary binds exact registered jobs and raw rows, per-process
receipts, full outputs, all guard receipts/foreign checks and CPU qualification.
Mutated rows, failed guards and unregistered source identities are rejected.
For replay of an older recorded executor, preserve its exact source checkpoint
outside Git and explicitly pass `--executed-driver "$EXECUTED_DRIVER"` to both
`check` and `summarize`. A hardened analysis script is not retroactively called
the executed driver; no timing sample is rerun by offline gate hardening.

## Six static external diagnostics, separate denominator

Use the already installed native GPU Faiss 1.15.1 environment via `FAISS_PYTHON`.
No CPU fallback, cuVS substitution, ANN sweep or dependency installation.

```bash
python3 "$B/snapshots.py" prepare --work "$SCRATCH/static" --data "$GIST_F32BIN" \
  --events "$SCRATCH/cases/short1m/events.txt"
python3 "$B/snapshots.py" execute --work "$SCRATCH/static" --build "$SCRATCH/build" \
  --guard "$GUARD" --gpu "$GPU_UUID" --numa-node "$NUMA_NODE" \
  --admission "$SCRATCH/admission" --faiss-python "$FAISS_PYTHON"
numactl --cpunodebind="$NUMA_NODE" --membind="$NUMA_NODE" \
  python3 "$B/snapshots.py" check --work "$SCRATCH/static" \
  --library "$SCRATCH/build/cpu_oracle.so" --warm-events "$SCRATCH/cases/warmup/events.txt"
```

The initial snapshot uses the first 32 actual frozen workflow query coordinates,
mapped back by original row; only 29 queries occur before the first rebuild, so
using 32 pre-rebuild queries would be false. The rebuilt snapshot uses the first
32 queries after that rebuild. The latter all occur before the next update.
Coordinates are byte-checked against source lineage, duplicates remain separate
live occurrences and each snapshot has 1M rows. Data/lineage arrays stay outside
Git, with reproducible hashes and manifests. Snapshot IDs are current live ranks.

FULL/BOUND use the same qualified clone and restored snapshot. Flat builds a
static FP32 GpuIndexFlatL2 and warms eight fixed queries; no update state exists
to restore. All modes return 32 complete B1/K8 Host-ready answers and include
final index/resource release in their recorded static service pass. Setup is
separate. GTS also includes empty update-buffer preparation and common tree
capabilities; the service owners are therefore not identical to Flat. GTS's
query-ACK sum is nested operation timing, not an external continuous e2e ratio.
The native query pass is additionally retained with raw squared fields.

Internal IDs/fields/order must match exactly. External membership accepts genuine
exact-distance boundary ties; both delivered-field squared error and raw native
squared error use the inherited scale-1 tolerance 5e-5. NaN/Inf, invalid/repeated
occurrence IDs and all mismatches remain explicit; never remove native speed
because of a mismatch. Six single-process rows establish neither significance
nor an external dynamic end-to-end win. Optional IVF_ALL is not silently added.
Conditional 10k/12k-event workloads remain unadmitted until their separate gates.

The recorded delivery also retains two static launcher failures: a relative
`env` receipt error and a pre-GPU Faiss import failure caused by resolving a
virtual-environment Python symlink. The recipe now requires an absolute native
`env` executable and preserves the virtual-environment executable path. No new
package is installed. Read `ATTEMPTS.md`; six admitted GPU diagnostics plus those
two invocations use the plan's eight-process external ceiling, with no IVF_ALL.
The exceptional `--remaining-only --executed-driver "$ORIGINAL_STATIC_DRIVER"`
recovery is fail-closed to that specific import failure and keeps the already
valid initial FULL/BOUND rows; it is not a general benchmark resume/resampling mode.
