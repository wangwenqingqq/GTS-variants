# Execution, recovery and publication audit

## Frozen intent and source

Plan: update critical-path attribution only; plan SHA256 is in CONTRACT.json.
Parent commit `d4e196f38aa8242e547e3dea3d9311650bb9ef10`. Original exact-search
operators, occurrence semantics, output/field authority, query IDs/radius and
mixed-service timing segmentation remain unchanged. No update optimizer,
statistics policy, new index, async execution or manuscript edit was introduced.
No product/concurrency/Graph/novelty admission is implied.

The new client isolates micro workloads and optional non-per-row NVTX scopes.
The fixed generator explicitly closes validation while leaving its std::set
alive until after synchronization, preserving native destruction order. TRACE0
eliminates NVTX calls; TRACE1 has the same control/ownership semantics. Selected
search SASS matches the immutable parent in both builds, with no added update
kernels. These are distinct static, correctness and measurement gates.

## Append-only recovery ledger

| Registration | Starts | Disposition |
|---|---:|---|
| R1 stopped checkpoint | 84 |29 qualification +54 primary passed;1 interrupted;40 unexecuted;source-lifetime deviation found;no headline reuse |
| First R2 admission | 1 |Guard refusal before CUDA;no outputs/no GPU measurements;preserved |
| Fresh idle-card R2 | 124 |29 qualification +84 primary +11 timeline,all passed |
| Preserved cumulative total | **209** |Exactly the authorized amended maximum;no automatic retries |

The original base contract keeps208. The append-only placement amendment binds
that exact contract hash and authorizes209. It does not change algorithm,
workload, timing, quality or estimator. The first CPU-only R2 build and a
subsequent controlled-SIGINT source revision are retained separately, with zero
CUDA target starts. R1's31-file checkpoint at
`8cb42ebb7de796bdc501f470d0fd4aa522ea831b` remains unchanged.

A stopped R1 observer initially survived controller interruption; an exact
UID/PID/starttime/argv/open-file ownership check identified and stopped only
that task-owned read-only monitor. The unstable first raw archive was retained
as rejected and replaced by a separately named stable archive, never silently
overwritten as valid. The R2 controller uses a separate guard session, forwards
one controlled SIGINT and waits for finally cleanup; CPU tests cover PID/group
signals and observer readiness. This is not an arbitrary-SIGKILL guarantee.
No foreign process was signaled or settings changed.

## Measurement and quality

Six balanced forward/reverse no-profiler process rounds retain all observations.
Median ratios and same-round geometric ratios are separate;20,000 process-level
bootstrap draws use frozen seed2026101511. Clean reverse results are retained,
as are slower bulk-reference rounds. R pair ACK is not doubled with nested
D/I ACKs. Small B and B512 finite p95 have different sample counts; neither is
an arrival SLA. Twelve full-W2 controls remeasure immutable parent binaries on
the same admitted device. The service interval crosses1 and is not promoted.

All124 targets passed two-sided ownership/isolation checks. All116 non-selftest
outputs were fully checked again offline;8 selftest/sanitizer invocations retain
100 iterations,2 stream slots and400 query checks each. Sanitizers cover the
bounded selftest, not every1M workload. Every admitted final vector byte and
full map was checked before/after the declared timing boundary, not silently
added to only one comparator. Public curation stores scalar/quality receipts
and hashes, not raw vectors, occurrence IDs or private environment files.

## Offline postprocessing corrections — no additional GPU starts

1. Initial complete curation retained all124 raw checks and scalars.
2. A derived-table assertion misread `update_batches` as per-kind rather than
   D+I ACKs. It stopped before output. The failed source/record are retained;
   the corrected2×per-kind interpretation was rechecked and bound by hash.
3. Read-only audit demonstrated that missing inner NVTX phases could fall into
   Other Host. The parser now requires the exact inner phase multiset, verifies
   INSERT_SUBMIT without adding it to bookkeeping, and binds chronological
   per-ACK API/bytes to independent native ledgers/replayed mutation witnesses.
   All11 existing captures passed; native TIMING and every prior Host/device
   total remained unchanged. Missing and duplicate phases were rejected in
   real-trace in-memory tests, alongside19 synthetic accounting negatives.
4. Public placement labels were generalized with an explicit documentation-only
   source bridge. Executable/contract bytes are unchanged; original executed
   snapshot remains in private custody. Historical-source matching must use it.
5. Four figures were exported using standalone Matplotlib after initial external
   style-assisted drafts; numeric CSVs are unchanged. No installation-owned
   skill or runtime code is redistributed.

NSYS warnings for CUDA/NVTX/OSRT completeness and absent scheduling remain in
all captures. Exact required operator/phase/API/payload counts passed, but full
OSRT/scheduler/internal-driver completeness was not established. Runtime API
spans can block; device activity overlays Host time. GPU percentages are
unsigned-byte quantized samples from first to last operator, not per-ACK or
ACK-weighted measurements. Raw signed clocks/scaled warp averages are not
interpreted. Exact DRAM/L2 bytes remain N/A, not invented zero counters.

## Delivery boundaries

The exact whitelist is PUBLIC_MANIFEST.json. Original raw archives remain
private with SHA/byte custody. No manuscript, credentials, raw conversations,
restricted vectors, private hostnames/paths or device configuration is intended
for upload. The existing repository visibility and branch policy are preserved;
no merge, history rewrite or unrelated workspace cleanup is authorized here.

Public CPU verification is deliberately narrower than author-side raw quality
revalidation. A containing Git commit and independently verified remote-file
read establish publication; this document alone does not claim a push succeeded.
