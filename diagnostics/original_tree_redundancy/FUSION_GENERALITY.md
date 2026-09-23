# Is fusion-addressable redundancy common to GPU tree indexes?

Date: 2026-09-23. **Source-confirmed recurrence, not a majority claim.**
This audit covers five repositories and six implementation paths. They are a
purposive sample across metric trees, buffered k-d trees, spatial BVHs, ordered
B-trees, and a Morton dual-tree implementation, not a representative statistical
sample. No new build, GPU run, profiler collection, or performance measurement
was performed. All inspected working trees were clean; exact revisions and
15 file hashes are in [FUSION_GENERALITY_PINS.json](FUSION_GENERALITY_PINS.json).

## Decision

1. **Not merely a GTS artifact:** repeated predicate evaluation and intermediate
   materialization occur at phase boundaries in other inspected implementations.
   The clearest cross-project match is count -> scan -> re-evaluate -> fill in
   ArborX spatial results and JZ-Tree node-interaction lists.
2. **Not a universal missing traversal/distance fusion:** GPU-Tree already walks
   a query-tree and computes leaf distances inside one kernel; MVGpuBTree performs
   a complete point lookup inside a device function. ArborX runs traversal and
   the leaf callback together. Buffer k-d trees and JZ-Tree already fuse leaf
   distance evaluation with local top-k maintenance.
3. **Not automatically removable by one kernel:** globally compact, variably
   sized outputs require offsets, storage, synchronization, or a changed ownership
   scheme. Fusion can exchange launches/recomputation for over-allocation,
   temporary writes, atomics, register pressure, or lost inter-CTA parallelism.
4. **Novelty gate:** reject generic traversal fusion, preallocation, and local
   distance-plus-top-k as standalone new contributions. The broader phase-state
   hypothesis remains a diagnostic direction, not an established novel thesis.

## Mechanism matrix

| Implementation / inspected path | Source-visible repetition or boundary | Already integrated / strongest caveat | Appropriate investigation |
|---|---|---|---|
| GTS original range path, with V2 cross-check | Per-level masks/selection/results; live siblings independently evaluate the same query-pivot distance | A node's distance, interval test, and pruning decision are already together. kNN already reuses parent-pivot distances | Fuse locally owned metadata/result stages; evaluate parent-pivot reuse separately from launch reduction |
| GPU-Tree in GTS repository | Initial kNN bound search retains a scalar, destroys queues, then final search starts from roots; work can overlap if the seed tree participates | The main query-tree traversal and leaf distances are already one kernel. The seed bound can save later work | Retain useful seed candidates/state with exact duplicate handling; not blanket traversal fusion |
| Buffer k-d tree, OpenCL | Gather queries/top-k -> leaf processing -> scatter; small-tail fallback rescans the full training interval and resets prior top-k on its first chunk | Leaf distance and top-k are already combined. Grouping/layout transformation and regular brute-force tail may be faster than irregular reuse | Remove only proven dead staging; compare retaining progress against the intended throughput tradeoff |
| ArborX v2.0 spatial CSR output | No preallocation: traverse/count -> offsets/allocation -> traverse/fill. Soft-buffer overflow can trigger whole-batch replay | Traversal and callback are already together. Sufficient preallocation avoids replay; raw callbacks bypass CSR; kNN has known k | Test bounded result retention and selective overflow replay against existing strong output paths |
| MVGpuBTree point lookup and its ordinary B-link reference | Same-key requests can repeat root-to-leaf work when they share a valid read-only/snapshot contract | Lookup is already device-contained; public device-side APIs support composition. Versions/side links/retries maintain correctness | Negative control for missing traversal fusion; duplicate-query sharing is a different, workload-dependent mechanism |
| JZ-Tree CUDA kNN interaction generation | At each processed level: find radius bound -> count interactions -> scan -> re-evaluate/insert -> segment sort -> later leaf evaluation | Distance plus top-k is already fused at leaves. Interaction lists share work across query groups; sorted lower bounds enable early exit | Measure repeated node-pair predicates and intermediate traffic; preserve grouping, ordering, capacity checks, and pruning |

GPU-Tree is the GTS authors' adaptation, **not** the original G-PICS artifact.
Buffer k-d uses OpenCL, not CUDA. The ordinary B-link tree is the reference in
the MVGpuBTree repository, not an independent audit of the 2019 artifact.
ArborX is pinned to v2.0, not a statement about current development HEAD.
An ordered key/value lookup is a mechanism control, not a same-task metric-search
throughput comparator. Implementations with unverified code are not counted.

## Exact source anchors

### GTS: reuse and fusion are different changes

[Sibling construction][gts-tree] assigns a common pivot to children (191-198).
[Original range traversal][gts-search] computes that distance per live child
(38-141), and uses it immediately for pruning. The V2 range implementation has
the same pattern (40-148); its kNN `getDisPQ`/`nodeProcessKnn` pair already shares
the distance (645-750 / 155-195 in [V2][gts-v2]). If b siblings are evaluated,
one shared distance plus b distinct interval tests can replace b distances;
this is not a b-fold completed-query speedup.

The existing [result-fusion campaign](../fused_result_20260923/README.md) is the
only measured fusion result referenced here: 24 -> 17 kernels and 108.71 ->
60.38 us (1.800x ratio of medians) against a freshly measured unfused Graph
control. It covers Words N=2000, batch one, radius 4, immutable height-3 tree,
complete ordered host IDs/distances/count, and hot-query completion, excluding
tree construction. It fuses result selection/projection, **not** traversal with
leaf distance, and establishes neither cross-index speedup nor released CPU
cores. CPU time per query falls while utilization remains about one core.

### GPU-Tree: lost state across phases, not an unfused core walk

[Search source][gpu-tree], 414-576, contains both the queue-driven tree walk and
leaf distance/answer updates in `searchKnnD`. The bound initializer at 576-743
retains the kth distance at 736-737; its queues are freed at 968-984. Final queues
are allocated and searched at 1055-1064. Overlap is conditional on seed-tree
participation. Retaining results must prevent double counting and retain the
pruning benefit; removing the initializer without a control is not justified.

### Buffer k-d: staging plus a deliberate tail restart

[Host orchestration][buffer-host], 392-412, selects the tail fallback; 480-516
sets its full training interval. Query/top-k gathering at 715-765 includes
explicit waits. The [leaf kernel][buffer-leaf], 64-78, resets top-k for the
first brute-force chunk, then computes distance and updates top-k together at
90-143. Later chunks accumulate rather than reset. An already partly processed
tail query can repeat point distances; retaining only top-k while rescanning
without ID deduplication is not sufficient. Source-level logical traffic is not
measured DRAM traffic, and waits are not evidence of CPU arithmetic saturation.

### ArborX: output representation causes replay

[CSR wrapper][arbor-crs], 178-190 and 203-247, implements the unbuffered count,
scan/allocate, fill sequence. With soft preallocation, any per-query overflow
sets a batch-wide flag (144-165) and the second pass uses the whole predicate
batch (243-247). Empty output exits at 213-222. The [policy][arbor-policy],
21-39, already exposes preallocation. The [traversal functor][arbor-traversal],
62-118, evaluates the node predicates and invokes the leaf callback in one
`parallel_for`; it does not launch a kernel per tree level. Nearest queries
allocate from known k in the CSR wrapper (313-329).

This is source-confirmed repeated predicate work for unchanged data/predicates,
not a measured 2x penalty. A callback comparison must still produce the same
required materialized output, including packing and delivery; a count-only
callback is not an equivalent faster comparator.

### MVGpuBTree: an explicit negative control

[Batched lookup][mv-kernel], 481-519, calls `cooperative_find` from the kernel and
writes the returned value. [Versioned lookup][mv-find], 439-472, traverses from
the root to the answer entirely on device. The ordinary reference has the same
structure at `gpu_blink_tree.hpp:278-301`. The [artifact API][mv-api] explicitly
supports device-side composition. This disproves a universal need for
host-mediated per-level traversal, not the existence of other overheads.
Same-key deduplication is only valid under compatible visibility semantics;
required historical versions and structural synchronization are not redundant.

### JZ-Tree: a second concrete count/scan/recompute/fill example

The [Python call path][jz-python], 164-193, processes tree levels through
`_knn_node2node_ilist`; leaf evaluation follows at 280-305. In [CUDA][jz-cuda]:

- `KnnNode2Node`, 629-690, submits radius-bound generation, count pass, CUB scan,
  insert pass, and segmented sorting. Outputs already have fixed capacities
  supplied through FFI (`knn.py:86-107`); this is **not** proof of host allocation
  between those CUDA passes or an opportunity solved by allocating once.
- `KnnNode2NodeCountInsert<0>` and `<1>` share the loop at 545-590. Both evaluate
  `mindist2` at 567 against the same unchanged node bounds. With sufficient
  output capacity, the count/fill passes repeat these node-pair tests. The
  radius-bound pass uses `maxdist2` instead: it is **not** the same predicate.
- `KnnLeaf2LeafKernel`, 241-288, consumes sorted interactions, computes point
  distances, maintains top-k, and writes output in one kernel. It does not
  materialize all point-pair distances for a later top-k kernel.
- For k > 32, 331-351 runs multiple leaf passes with radius/tie state; overlapping
  point distances can be reevaluated. This trades recomputation for bounded
  top-k state. A larger fused state is not automatically faster.

Do not remove the sort or interaction list just because it is intermediate:
sorted lower bounds enable early exit (246-251), and grouping shares target
loads through shared memory. Benefits of retained predicates must exceed their
storage/movement and synchronization costs. The [JZ-Tree paper][jz-paper] also
establishes GPU-oriented grouped dual-tree traversal as prior art; its reported
speedups are not independently validated or borrowed for this audit.

## What to test next, and what would falsify the direction

**Priority:** GTS remains the implementation target; use ArborX and JZ-Tree as
the first external mechanism checks, and the already-integrated B-tree/GPU-Tree
walks as negative controls. Do not start by building a universal fusion layer.

| Check | Frozen comparison and falsifier |
|---|---|
| GTS extension | Separate parent-pivot reuse from traversal-stage fusion and result fusion. Keep leaf parallelism, exact outputs, and memory budget. A launch reduction without completed-query gain rejects the performance hypothesis for that workload |
| ArborX output | Sweep zero/uniform/skewed matches and isolated overflow; compare default CSR, adequately preallocated CSR, and an equivalent-output callback path. If existing preallocation solves the cost within the same budget, generic replay removal is not a research contribution |
| JZ-Tree interaction | First count repeated `(level, query_node, target_node)` min-distance tests and time count/scan/insert. Compare against the existing fixed-capacity, grouped, sorted path. If repeat work is cheap or retention loses to recomputation, stop that mechanism |
| Cross-index control | Never compare B-tree point QPS directly to general-metric range/kNN. Run original versus candidate within each index, holding snapshot, ties, batch, output residency/order, memory cap, data and GPU/software state fixed |

NSYS should separate host submission/waits, GPU gaps, copies, allocation and
kernel phases. NCU should attribute instruction and device-memory costs to
selected kernels; instrumented/profiled durations are mechanism evidence, not
the speedup denominator. Use unprofiled completed-query timing, charge packing,
allocation, sorting and required host delivery, and retain negative cases.

### Allowed wording / excluded claims

- Allowed: **Several inspected GPU tree implementations repeat computation or
  materialize reusable state across query-phase boundaries; the mechanisms and
  conditions differ.**
- Not established: most GPU tree indexes have the same fusion deficiency, high
  CPU utilization, low useful GPU occupancy, or a common achievable speedup.
- Keep three boundaries separate: host control/API overhead, device global-memory
  intermediate traffic, and actual host-device transfers/migration. None is a
  synonym for the others. Low VRAM allocation alone is not inefficient GPU use.
- No new kernel, external-index correctness claim, paper text, or expensive
  experiment is delivered by this source-only extension.

[gts-tree]: https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GTS/include/tree.cuh#L191-L198
[gts-search]: https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GTS/include/search.cuh#L38-L141
[gts-v2]: https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GTS/include/search_v2.cuh
[gpu-tree]: https://github.com/ZJU-DAILY/GTS/blob/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GPU-Tree/include/search.cuh#L414-L576
[buffer-host]: https://github.com/gieseke/bufferkdtree/blob/fcba7edef2710a6e8bffa00aff2564504655182a/bufferkdtree/src/neighbors/buffer_kdtree/gpu_opencl.c
[buffer-leaf]: https://github.com/gieseke/bufferkdtree/blob/fcba7edef2710a6e8bffa00aff2564504655182a/bufferkdtree/src/neighbors/buffer_kdtree/kernels/brute_all_leaves_nearest_neighbors.cl#L64-L143
[arbor-crs]: https://github.com/arborx/ArborX/blob/041bf18e0bea7ab57f21dc0ee793389738c8cf11/src/spatial/detail/ArborX_CrsGraphWrapperImpl.hpp#L144-L247
[arbor-policy]: https://github.com/arborx/ArborX/blob/041bf18e0bea7ab57f21dc0ee793389738c8cf11/src/spatial/detail/ArborX_TraversalPolicy.hpp#L21-L39
[arbor-traversal]: https://github.com/arborx/ArborX/blob/041bf18e0bea7ab57f21dc0ee793389738c8cf11/src/spatial/detail/ArborX_TreeTraversal.hpp#L62-L118
[mv-kernel]: https://github.com/owensgroup/MVGpuBTree/blob/f755006d78ccca565f97cda053727d4d48b82d46/include/btree_kernels.hpp#L481-L519
[mv-find]: https://github.com/owensgroup/MVGpuBTree/blob/f755006d78ccca565f97cda053727d4d48b82d46/include/gpu_versioned_blink_tree.hpp#L439-L472
[mv-api]: https://github.com/owensgroup/MVGpuBTree/blob/f755006d78ccca565f97cda053727d4d48b82d46/README.md#our-vision
[jz-python]: https://github.com/jstuecker/jztree/blob/049c581e4f5d6343dd756669ec7019500c8da9e8/src/jztree/knn.py#L164-L193
[jz-cuda]: https://github.com/jstuecker/jztree/blob/049c581e4f5d6343dd756669ec7019500c8da9e8/src/jztree_cuda/knn.cuh#L512-L690
[jz-paper]: https://arxiv.org/abs/2604.05885
