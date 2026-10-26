# Native kNN execution adapter — unvalidated CUDA implementation

## Design card and scope

Target: one admitted RTX PRO 6000 (sm_120), FP32 payloads, native G/P
arithmetic, stable external integer IDs, and complete host-ready ID/distance
outputs. This is an API correctness adaptation, not a kernel optimization.
The existing CTA/warp schedules, barriers, native pivot bounds, key encoding,
and native distance arithmetic are retained. No new pipeline or persistent
GPU accumulator is introduced. The output ID buffer lives with one built tree;
native temporary search workspace and `res_dis` live for one query. Rebuild
invalidates the old physical-to-stable map and resets its tombstone count.

## Changes

- Both `search_v2.cuh` copies derive from the pinned original bytes and exact
  mandatory correctness patch, with zero fuzzy patching. Raw patched and final
  adapted hashes are retained separately in the provenance manifest.
- P's numeric queries call the external-vector `searchIndexKnnV2` overload with
  `res_ids`; edit queries use an appended external text row and the ID overload
  because the vector overload explicitly does not support edit distance.
  Every native `res_ids` and corresponding `res_dis` entry is copied back.
- G only changes its leaf **output payload** from temporary slot index to object
  ID, adds P's `mergeResKnnIds`, allocates qnum*k result distances, and calls that
  output kernel. Existing node pruning, pivot distance, threshold update, and
  leaf distance arithmetic remain unchanged. Tests compare their generated
  bodies exactly (apart from the already documented metric extension).
- Numeric P and text/P/G output physical IDs map through the current rebuild's
  stable-ID map. Results expose both complete raw native IDs/distances and the
  final live tree-plus-delta top-k IDs/distances.
- Native static kNN does not consult a deletion bitmap. The adapter requests
  `min(tree_rows, k + deleted_tree_rows)` ranks, filters those outputs using the
  authoritative bitmap, unions the exact device delta top-k, then selects k
  by the returned GPU distances. This is sufficient to retain live top k under
  the native rank contract without modifying pivot bounds or distance kernels.
  CPU oracle distances are not used in selection. Every overfetch, transfer and
  host merge cost remains in the operation interval.
- P's two optional residual predictions are fixed to zero and their absent
  optional headers are not included: C2 is removed and the original lower bound
  is unchanged. No gamma calibration or approximation path is introduced.
- The already documented Tanimoto interface branch also covers native kNN
  pivot and leaf kernels, including P's external vector variant.
- G's native half-free-memory workspace is capped at 4 GiB (like P), preventing
  signed `size_a` overflow on this GPU. This is a resource-safety cap, never an
  enlargement or a pruning change.
- Native range-update kernels are preserved. `range_tree` exposes complete
  tree output for the separate range correctness gate; it is not called by kNN.
  A full tree-plus-delta range/query-before-insert workload remains separate work.
- The existing worst-residual-child height recipe and full built-leaf audit
  remain active for both arms. No historical leaf insertion is compiled.

## Attribution and performance boundary

The selected static kNN APIs allocate their search workspace per call. Merely
using P here does **not** establish that the old range-update C1 persistent
workspace/single-query benefits are active, nor that a future P/(G+B*) ratio
isolates those benefits. Overfetch can grow with tree tombstones and may dominate
long deletion-heavy traces. These costs must be reported, not optimized away by
changing pruning or rebuilding more often. CPU-text oracle and range kernels
are unchanged. No timing, correctness or sanitizer pass is inferred from source
inspection.

## Local validation

Run:

```sh
python3 dasfaa_e1/prepare_native.py
python3 -m unittest discover -s dasfaa_e1/tests -p test_native_adapter.py -v
python3 dasfaa_e1/check_no_direct_insert.py
git diff --check
```

Six local static/unit checks pass: exact patches, deterministic derivation and
archive preservation, G computation/pruning body preservation, executed API and
full-distance output routing, exhaustive small tombstone-overfetch rank check,
and residual-height bounds. The insertion mutation check also passes.

**Not run by this worker:** SSH, CUDA compilation, GPU smoke, active-set oracle
execution, memcheck, synccheck, full-load correctness or timing. The campaign
owner must run those only after reviewed Linux cleanup/lock gates and guarded
GPU admission. Repeated Q=1 native invocations are naturally exercised by each
mixed smoke trace; larger Q=32/1024 static probing is not implemented here.
