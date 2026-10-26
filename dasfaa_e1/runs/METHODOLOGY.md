# E1 mechanism and evidence boundary

The frozen hypothesis separates C1 execution reuse from B* reconstruction
amortization under true, unique new arrivals and strict query visibility.
G fixes B=10; G+B* isolates the buffer controller; P combines it with archived
C1; D is a resident append/delete exact-scan comparator. No approximation arm
is admitted. Changing the buffer threshold without the G+B* arm would not
attribute a C1 benefit.

`Store::append/erase` and `NativeTree::rebuild` in `dynamic.cu` implement the
stable-ID/delta boundary. `check_no_direct_insert.py` limits append's call graph
and excludes historical tree-insert functions. Rebuild gathers the live tree
and live delta while preserving external IDs. The separate CPU Myers/FP64/
Tanimoto oracle checks the event-specific active set; this has not yet produced
new GPU correctness evidence in this continuation.

The current diagnostic top-k adapter calls native dynamic range search from a
safe radius established by k arbitrary live objects, unions exact delta top-k
and selects top-k on the host. It retains the archived C1 range-update contrast
but is NOT repaired native static kNN execution. Full host selection and
transfers belong in the declared operation time. The static-kNN source patches
are retained as explicit unexecuted provenance, not a surrogate validation gate.

The experiment does not establish novelty or an end-to-end speedup. It is a
corrective evaluation of a frozen thesis; no new paper prose or expanded
contribution is justified. All claims require the exact full-load correctness,
separate final timing/evaluation and audit gates in CONTRACT.md.


## 2026-10-26 native-path amendment (implementation only)

The user-selected native searchIndexKnnV2 path replaces range-candidate top-k
for dynamic kNN. See CHANGES_native.md and prepare_native.py. G's adaptation
changes output ID payload/merge only; mandatory fixes and dataset tree height
apply to both. Native queries overfetch k+tree tombstones, then filter stable IDs
and merge exact delta based on returned GPU distances. This may be expensive
and is an explicit operation cost. Static kNN allocation does not by itself
exercise original C1 update workspace reuse, so isolated C1 attribution is
unvalidated. Range kernels remain unchanged and require their own complete
oracle gate. No native CUDA build or runtime validation occurred before the
mandatory cgroup97/98 stop. All prior range-adapter timings remain ineligible.
