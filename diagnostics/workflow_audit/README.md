# GTSPP full-workflow memory-access audit

**Conclusion: there are actionable memory-access defects beyond the previously
studied static RNN/kNN leaf kernels, but insert/delete also expose host/device
round trips and correctness blockers that a warp rewrite alone cannot fix.**
This delivery audits and instruments an isolated copy; it does not replace any
native kernel, promote an update implementation, or claim a new speedup.

## Coverage and evidence boundary

- Pinned target: `archive/GTS_incremental`, revision `2c92590`, all17 files in
  [source pins](../cpu_io/SOURCE_PINS.json). It is the legacy unsafe direct-insert
  baseline, **not Safe-C1, original GTS, or every GPU-tree implementation**.
- [Kernel ledger](kernels.csv): all **69 definitions**, with access geometry,
  candidate/no-change decision, correctness constraint and reachability;55 in
  selected headers plus14 in two unselected alternatives.
- [Call-site ledger](sites.csv): all **1,014** syntactic launch/Thrust/CUDA sites,
  including legacy and conditional paths. These are not execution counts.
- [Host/library ledger](HOST_OPERATORS.md): loading, build, all static query
  overloads, update query, insert, three delete branches, buffer, rebuild,
  calibration, serialization, cleanup and runtime/managed-memory control.
- New representative evidence: **60 process records, eight NSYS traces and35
  selected NCU launches**, observing35 of55 selected-header kernel definitions.
  [Runtime coverage](runtime_coverage.csv) names every unobserved definition;
  unobserved is not zero cost or a failed mechanism.

GPU0, RTX PRO6000 Blackwell Server Edition,188 SMs; CUDA13.1.115, driver590.48.01,
NCU2025.4.1, NSYS2025.5.2. Runs serialized under the existing GPU0 lock, with
fresh idle admission and post-run checks. Other users' GPU work was untouched;
shared-host isolation was not available. No clock or driver changes. Static
comparators are the freshly hash-reverified original A binaries from the prior
RNN/kNN campaigns; these are not their optimized B/D variants.

Dynamic scope is deliberately narrower than source coverage: native N2000,
128D integer FP32 L2, update queries at row0/r200 (r10000 for all-include); static
N65536/Q128, RNN r500 and kNN k100. NCU captures the first matching kernel, not
all levels or active-lane distributions. Static RP mode0 is exact, not calibrated
ANN. Other metrics, true arrivals, mixed-update distributions, qnum>1 update
fallback and alternative headers remain unmeasured. No new paired latency,
stress/sustained, Graph, synccheck or production-admission campaign was run.

## Workflow: paths that must not be conflated

```text
load → build: init → pivot distance → sort → split/reduce → CPU repair/padding
  ├─ static RNN V2: node distances → flags/transpose/scan → leaves → reduction
  ├─ static kNN V2: pivot distance → prune/sort/threshold → leaves/sort → kth or IDs
  └─ update replay
       ├─ insert: CPU metric route → direct leaf ID/metadata copies
       │                         └─ full leaf → buffer → threshold-triggered rebuild
       ├─ delete: base tombstone | buffer scan/compact | direct leaf D2H/CPU/H2D
       └─ range query: legacy traversal → atomic leaf compact → update leaf kernel
                    → atomic result compact + buffer scan → logical-ID merge
rebuild: alive prefix + tracked IDs → getNewData → complete build/padding/mirrors
```

Static query and update query do not use the same leaf/aggregation kernels.
The native update entry performs range queries only and fixes qnum=1; no native
update-kNN workflow is supplied by this archive. Static kNN after direct insertion
would be an additional API experiment and cannot inherit static-index correctness.
The four static kNN overloads are audited; three API modes were invoked in these
representative captures (vector-kth was not separately invoked).

## Correctness comes before update speed comparisons

Independent oracle: multiset of original rows, self included, integer squared
L2 distances, logical-row deletion, count comparison. Replay inserts existing
row IDs, not new data. Passing counts are **not** full result-ID/distance/identity
validation. The base-delete probe removes a row outside the selected radius;
the buffer-delete probe deliberately has no subsequent query.

| Scenario | Clean observed / expected | Memcheck | Decision |
|---|---:|---|---|
| Query-only,8 queries | 3/3 each | 0 reported errors | Count-only pass |
| All-include r10000 | **1999/2000** | 0 reported errors | Reject as self-included exact baseline |
| Base delete | 3/3 | 0 reported errors | Weak count-only pass |
| Direct insert | 4/4 | 0 reported errors | Count-only pass |
| Direct insert/delete | 3/3 | 0 reported errors | Count-only pass; occurrence identity unknown |
| 65 inserts + buffer query | 68/68 | 0 reported errors | Count-only pass; not a sizing proof |
| Buffer + direct delete | No final query | 0 reported errors | Branch/memory diagnostic only |
| 66 inserts → rebuild → query | **68/69** | 0 reported errors | Reject as exact baseline; root cause unresolved |

The two count failures also reproduce in NSYS; the corrected NCU rebuild probe
reproduces68/69. Memcheck used leak-check off:0 detected accesses is not semantic
correctness, race freedom, leak freedom or an exhaustive memory-safety proof.

**Retained failed collection:** the first `ncu_rebuild_getNewData` process omitted
the threshold2 setting across sudo, did not rebuild and profiled zero kernels.
Its69/69 output is **not a post-rebuild pass or evidence of nondeterminism**.
The separate `_envfix` run passes the setting explicitly, selects getNewData and
fails68/69. Both records remain in [EVIDENCE](EVIDENCE.json). The fixed watchdog
runs inside sudo; all original runs exited without timeout and left GPU0 clear.

Source-confirmed risks, not all experimentally localized:

1. **Capacity mismatch:** inserts allow64 extra IDs/leaf, while update leaf output
   uses `bid*MAX_SIZE+i` with MAX_SIZE20. Adjacent segments can overlap; scanning
   only `search_num*20` can miss writes. Static V2 leaf loops also assume20 slots.
2. **Pruning bounds:** direct inserts update at most the leaf maximum, not all
   ancestor/min bounds. Routing outside an existing interval can invalidate
   conservative pruning. No full proof follows from duplicate-row probes.
3. **Self/output contract:** native all-include skips `data_id==qid` and writes
   distance -1, while the ordinary distance branch includes self at0. This
   explains the all-include contract inconsistency, not yet the rebuild failure.
4. **Identity:** tombstones indexed by physical row can suppress duplicates;
   direct delete finds the first matching physical ID, not a distinct occurrence.
   Original/current row identity after rebuild needs a full oracle.
5. **Conditional workspace growth:** qnode_idx capacity is checked after shared
   cap variables have already been updated. A growing qnum>1 fallback can retain
   too-small storage. Native main's qnum1 path does not read that array.

## Measured access evidence and priority

Numbers below are selected-kernel **NCU diagnostic** values, not clean latency
or speedups. Useful bytes/sector has a32-byte ceiling; neither its reciprocal nor
profiler duration predicts an end-to-end gain. Scalar broadcasts and short tails
can legitimately show low values. Different row shapes must not be added.

| Operator / representative scope | Load / store useful B per32B sector | Interpretation and smallest candidate |
|---|---:|---|
| Static kNN leaf, N65536/Q128/k100 | **4.08 /32.00** | Strided coordinate loads, already coalesced output; preserve store ownership when cooperating on reads |
| Static RNN leaf, N65536/Q128/r500 | **4.02 /18.82** | Coordinate cooperation; output/selectivity differs from kNN |
| getQCount / getQCountKnn | **32.00/4.00**, **28.89/8.00** | Node/query layout transpose; tiled transpose or consistent producer-consumer layout |
| mergeLNode / mergeLNodeKnn | **6.81/4.00**, **12.11/8.00** | Traverse in per-query prefix order; optimize both producer and consumer, not one side |
| mergeResRnn | **4.00 /32.00** | Long per-query device-Thrust reduction; cooperative reduction, unlike O(1) kth gather |
| getPivotDis, N2000 initial build | **4.03 /31.94** | Same AoS coordinate stride in build; warp-cooperative distances |
| nodeSplit, N2000 initial build | **4.00 /8.10** | Few active child threads compute endpoint distances; reuse/cooperate only with conservative-bound proof |
| getNewData, N2000→2066 rebuild | **4.16 /4.00** | Both serial per-point reads and writes stride128 across lanes; flatten coordinates / warp-per-row copy |
| update leaf, N2000/r200 | **4.03 /4.00** | Strided reads; output sparsity and unsafe sizing prevent a simple store-efficiency diagnosis |

The transposes' representative store sector totals are1,280,000 each; getNewData
has266,618 load and264,448 store sectors. These support the access mechanism;
they are not DRAM byte savings. Full metrics, registers/shared resources and
scheduler values are in [ncu_summary.csv](ncu_summary.csv).

**Engineering order:**

1. **P0:** establish correct update semantics/sizing/identity and localize the
   post-rebuild mismatch. Do not benchmark an incorrect fast path as a keeper.
2. **Query:** retain prior bounded leaf/reduction evidence; next test the
   `getQCount → scan → mergeLNode` layout pair and pivot-distance family. Do not
   assume the largest access inefficiency is the largest query time component.
3. **Rebuild:** prototype coalesced getNewData once output equality is checked
   independently; then price full rebuild including sorting and CPU padding.
4. **Insert/delete/buffer:** reduce host-device transactions and CPU scan/lookup
   round trips. These are boundary/lifetime changes, not solely coalescing.
5. **Conditional:** warp-aggregate atomic reservations when enough lanes pass;
   test final top-k copy if its end-to-end share warrants it. Keep already-linear
   initialization, flags and mergeTotalResult writes unless eliminating a pass.

Direct evidence for boundaries from NSYS:
- One direct insertion: **2 H2D calls,24 bytes**;64 successful direct inserts:
  **128 calls,1536 bytes**. A radius-update copy is an untaken optional third call.
- One direct deletion: **1 D2H call,84 bytes;2 H2D calls,104 bytes** in its leaf scope.
- One-item buffer query: **4 bytes D2H and4 bytes H2D** around the CPU prefix scan.

These tiny transfers are not a bulk-bandwidth problem. The first direct insert's
host route measured2.1067ms wall/2.1060ms main-thread CPU in a single diagnostic
process, while65 routes totaled2.1620ms wall. This is strong reason **not** to
classify all route time as distance arithmetic: cold managed-memory/runtime
behavior and warm amortization are included; CPU/GPU wait attribution remains
incomplete. No CPU utilization reduction is claimed from this audit.

Prior [RNN](../gtspp_coalescing/README.md) and [kNN](../gtspp_knn/README.md)
optimizations remain separate evidence. The prior kNN D64 overlay has Q128 gains
but failed both Q32 short-query promotion gates; no default dispatch is changed.
Do not reuse its GPU5 timings as this round's GPU0 measurements.

## Reproduce and inspect

The scripts use only Python standard library and the installed CUDA tools.
A separate reconstruction build also compiled successfully using the command
below. Its binary hash differs from the measured executable; it is a compile
check, not a bit-identical rebuild or a new timing result. Its optional smoke
attempt stopped at the occupied GPU0 lock before launching a workload. The
completed60-record campaign is unaffected; see [BUILD_CHECK.json](BUILD_CHECK.json).
`catalog.py` fails on changed source pins or missing kernel classifications.
`test_audit.py` regenerates all traces, compares69 unchanged kernel bodies,
checks the measured generated-source manifest and exercises the CPU oracle's
boundary/self/duplicate and fail-exit behavior.

```sh
python3 diagnostics/workflow_audit/catalog.py
python3 diagnostics/workflow_audit/test_audit.py
python3 diagnostics/workflow_audit/prepare.py "$SCRATCH/native"
python3 diagnostics/workflow_audit/traces.py "$SCRATCH/traces"
# Generate the pinned fixtures, as in the prior leaf campaigns; keep data outside Git.
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n2000" --n 2000
python3 diagnostics/tc_leaf_probe/prepare.py fixture "$SIFT_BASE_TEXT" "$SCRATCH/fixtures/n65536" --n 65536
# Verified reconstruction command (installed NVTX headers must be visible).
mkdir -p "$SCRATCH/bin" "$SCRATCH/logs"
"$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
  -DGTS_DIAG_NVTX -Xptxas=-v -Xnvlink=--ignore-host-info \
  -I"$SCRATCH/native/include" "$SCRATCH/native/src/main.cu" -ldl \
  -o "$SCRATCH/bin/native" > "$SCRATCH/logs/build.log" 2>&1
# Never replace the original source/binary.
for stage in check sanitizer nsys ncu; do
  python3 diagnostics/workflow_audit/run.py "$SCRATCH" --gpu "$ADMITTED_GPU0_UUID" --stage "$stage"
done
# Optional static capture: checked original A binaries at bin/rnn and bin/knn,
# built/prepared by the linked prior campaigns, with their recorded hashes.
python3 diagnostics/workflow_audit/static_profile.py "$SCRATCH" --gpu "$ADMITTED_GPU0_UUID"
```

Recheck current GPU0 allocation before running; these commands are not a future
GPU reservation. Existing output directories are rejected. Native failures are
retained as diagnostics, not treated as speed-gate passes. `analyze.py RAW OUT`
is the frozen historical export validator: it intentionally requires all60
records, including the original missing-profile attempt and its envfix retry;
a fresh collection must get a new contract/manifest rather than forge that history.

Raw reports, addresses, machine paths, binaries and dataset stay outside Git.
[EVIDENCE.json](EVIDENCE.json) retains their per-file hashes, binary/source hashes,
all outcomes and provenance. Original receipts are immutable; the analyzer
recovers GTS_DIAG phases and memcheck summaries from original logs (early receipt
parsers omitted them). Failed oracle exits do not unwind active NVTX/RAII ranges;
NSYS may auto-close their ranges at process exit, so the analyzer explicitly
marks main.total, update.total and the failed op.query incomplete and omits their
durations. Missing/incomplete phases are unknown, not zero latency. Scope times are nested
and inclusive; CUDA API durations overlap GPU execution. Copy migration records
are retained as such; no UM page-fault counters were collected. Runtime kernel
rows include selected library functions, not just user kernels. No SASS dynamic
instruction or exact library-code-generation claim is made.
