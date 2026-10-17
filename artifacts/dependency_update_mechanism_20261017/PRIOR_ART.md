# Gate0 and novelty boundary

Checked on2026-10-17,using primary sources and the installed toolkit headers.

- [EnTT sparse-set source](https://github.com/skypjack/entt/blob/main/src/entt/entity/sparse_set.hpp)
  establishes ordinary sequential swap-and-pop ownership. It does not establish
  the complete allocated-byte GPU exact-range service measured here.
- [LLVM MemorySSA](https://llvm.org/docs/MemorySSA.html) explicitly connects
  memory def/use analysis with optimization,including dead-store elimination.
  Propagating sources and removing overwritten stores is not a new general idea.
  We do not run LLVM or claim that its compiler pass implements this service.
- [NVIDIA Thrust for_each](https://github.com/NVIDIA/cccl/blob/main/thrust/thrust/for_each.h),
  [gather](https://github.com/NVIDIA/cccl/blob/main/thrust/thrust/gather.h) and
  [scatter](https://github.com/NVIDIA/cccl/blob/main/thrust/thrust/scatter.h)
  provide standard GPU bulk indexed execution. The benchmark uses the installed
  CUDA13.1 CCCL headers,whose exact hashes belong to the execution identity;
  the moving online main branch is a reference,not the binary identity.
- [CUDA13.1 batch-copy API](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/group__CUDART__MEMORY.html)
  does not guarantee ordering of copies within a batch. Our WAVES baseline
  preserves the physical dependency order rather than submitting unsafe batches.

## Concrete cheap kill test

The generic planner accepts arbitrary copy sequences,not only descending tail
sources. It resolves each destination to its original source and retains only
final nonidentity assignments. Exhaustive N≤8 deletion sequences,random cases,
and every batch of the16 registered logical traces produce exactly the same
assignment set as Tail-Provenance. This is concrete equivalence evidence,not
rejection merely because two ideas belong to a similar family.

The bounded GPU study remains useful for attribution:compare identical plans
on different executors,then different plans on the same executor. A timing win
can establish a planner specialization or engineering result;it cannot by itself
restore exclusive assignment-elimination novelty. No same-setting prior work
was found in this bounded audit that establishes the entire strict service
contract,but that absence is uncertainty,not a novelty certificate.

This gate therefore does not admit a new ownership-algorithm thesis. A later
nonincremental mechanism would need a specific prior-art difference and a new
cheap falsification experiment before a new expensive campaign.
