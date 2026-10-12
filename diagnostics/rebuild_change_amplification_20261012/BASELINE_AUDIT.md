# Baseline and observer audit

## Frozen keeper

Parent: `db821b904b04576ab329dafbea6c7eae382e3323`, external mixed closure.
Production P2 SHA256:
`771f7cf42a23a8e2081f2d2da47d02e747799e9b06dcd4c6e9c0eba093ee0d3c`.
The original binary and 25-file source tree are not overwritten.
Arity 10, leaf size threshold 20, insertion buffer rebuild threshold 10.
Same GIST N1M D960 trace and Host-ready request vectors.

## Actual source flow

Deletion marks native base tombstones, or removes an insertion-buffer entry.
The triggering insertion becomes logically visible before compaction. Rebuild
copies the complete old base-plus-request allocation into a temporary buffer;
getNewData writes every surviving base and pending insertion coordinate.
Construction initializes physical order and repeatedly selects the middle
**order-array occurrence**, computes pivot distances, globally sorts N keys,
and splits each active parent into ten children. Selection is deterministic
source logic, not random pivot sampling (the RNG calls are commented out).
Compaction can therefore change selected pivot occurrences; whether that causes
wide structural churn must be established by the snapshots, not assumed.

After construction, numeric refit scans the membership of every valid
non-root pivot node; PAR make_plan rebuilds all persistent vector payloads;
KNN pack32 rewrites every base coordinate. These calls are unchanged.

## Observer boundary

A separate observer binary adds Host-only hooks in tree.cuh and update.cuh,
with two new observer headers. Source audit preserves 89 lexical CUDA
`__global__`/`__device__` definitions exactly across the 25 keeper files.
No new GPU kernel, atomics, algorithm, threshold, query ordering or state update
is introduced. Read-only D2H capture follows synchronization. Occurrence mapping
is maintained in private Host observer vectors and checked against native
is_delete and the exact live Fenwick map at every snapshot.

The observer binary differs from the production keeper, intentionally; its
latency is not comparable. Equality of ordered payloads, event state and rebuild
triggers is the behavior gate. Source equality is not a sanitizer result or a
claim of identical compiler-generated SASS. No observer sanitizer, new timing,
Graph, stress or external baseline process is admitted by this diagnostic budget.
The keeper's earlier qualification remains historical, not a new observer test.

## Resource admission

The authorized GPU 1 UUID digest, driver/toolkit and NUMA placement were checked
live; the GPU was idle before the lock. GPU 0's foreign service was not touched.
Both preserved GPU locks and before/during/after foreign-process rejection were
reused. Settings remained unchanged. Large snapshots stay on the experiment
host, not in Git and not transferred through the client.

This is an existing-path diagnostic kill screen, not a new-mechanism novelty
claim. Any later organization/maintenance mechanism needs its own prior-art
Gate 0 and same-contract performance experiment.
