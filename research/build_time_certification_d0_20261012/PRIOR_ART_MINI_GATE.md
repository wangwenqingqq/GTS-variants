# Retained Z: mechanism-specific mini prior-art gate

**Z is ordinary segment gather plus block/segmented extrema reduction, already permitted in strongest C2. This mini-gate does not reopen the previous broad build-bound novelty survey.** X/Y were not retained, so no three-direction literature campaign is conducted.

## Pinned primary sources

Use NVIDIA CCCL **v2.8.0**, peeled commit `6d02e11d914428000ec01625d765efa3a2d34ce7`, not a current unstable feature or a claim about the keeper's installed library version. Retrieval was byte-hashed in [PRIMARY_SOURCES.json](evidence/PRIMARY_SOURCES.json); originals stay private. The pin supplies an independently inspectable pre-existing ordinary primitive, not a performance comparator.

| Source | Exact locator | Established capability | Transfer to Z | Not established |
|---|---|---|---|---|
| [CUB DeviceSegmentedReduce](https://github.com/NVIDIA/cccl/blob/6d02e11d914428000ec01625d765efa3a2d34ce7/cub/cub/device/device_segmented_reduce.cuh#L133-L261) | lines 133-261 | Generic binary reduction over begin/end-offset iterators; input/output iterator types and caller storage | Child intervals are existing segments; gathered endpoint tuples can use a min/max combiner | This exact GTS bit contract, compiler/resource use or installed algorithm |
| [CUB BlockReduce](https://github.com/NVIDIA/cccl/blob/6d02e11d914428000ec01625d765efa3a2d34ce7/cub/cub/block/block_reduce.cuh#L283-L356) | TempStorage/constructor 283-304; custom Reduce 306-356 | A user kernel can use shared temporary storage and a custom block-wide combiner | Extrema can be placed in an ordinary split kernel rather than a separate ownership-map pass | Automatic native split compatibility, synchronization elision or a runtime win |

These capabilities subsume the **reduction/placement component** of Z; neither source claims this entire GTS pipeline. The inferential step is explicit: native child segments plus physical-row gathers plus these ordinary extrema mechanisms yield no graph operation beyond C2. Use exact `fmin/fmax` semantics and zero/empty/root handling when qualifying any implementation; do not assert that a default library comparator is automatically a bit-identical replacement.

## Architectural and numeric background, not additional novelty papers

[CUDA 13.1 Programming Guide, shared storage](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-c-programming-guide/index.html#shared) scopes ordinary shared storage to its block; [hardware multithreading](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-c-programming-guide/index.html#hardware-multithreading) describes a warp's register context. This supports the conditional cross-completed-kernel argument for X: ephemeral scoring state is not a retained certificate for a later unchanged native sort/split consumer. It is not a universal minimum-byte theorem.

[CUDA 13.1 directed double intrinsics](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html) defines the explicit rounding operations used by the frozen source. Those definitions support arithmetic dependency accounting, not measured SASS count, generated nominal pow behavior or throughput.

## Gate result

Mechanism overlap for Z: **direct/ordinary**. Strong C2 itself permits the same segment owner relation, gathered state, extrema and completion edges. No separate owner-map or standalone-reducer dependency must first be deleted. The graph test is sufficient to reject the retained mechanism; the mini-gate independently prevents dressing ordinary fusion as new ownership propagation. Unknown more elaborate X/Y algorithms need their own constructive graph and narrowly targeted gate, not more general tree-build citations.
