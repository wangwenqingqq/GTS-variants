# Nearest mechanisms, ordered by overlap

## 1. VP/MVP: scoring becomes partition metadata

The [VP/MVP primary paper](https://www.cs.cmu.edu/~eugene/refs/f-series/Bozkaya-ozsoyoglu-99.pdf) describes distance ordering, partition cutoffs, shell min/max radii, and reuse for search. Exact read locations are recorded in [the manifest](evidence/SOURCES.json). This establishes the mathematical construction-distance-to-pruning-metadata recipe; it does not specify the candidate's two floating-point contracts.

## 2. GNAT and pinned OMPL: assignment and bounds share a producer

[GNAT §4.1](https://www.vldb.org/conf/1995/P574.PDF) associates points with centers and builds cross-region ranges. In [OMPL split](https://github.com/ompl/ompl/blob/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/NearestNeighborsGNAT.h#L494-L541), a single computed matrix supplies membership, radius, and range updates. [GreedyKCenters](https://github.com/ompl/ompl/blob/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/GreedyKCenters.h#L82-L119) identifies its producer. Query consumers use those ranges/radii. This is the strongest implementation control, not merely a conceptual cache analogy.

The matrix is split-local but survives child recursion. Thus it is wrong to claim OMPL already proves a globally one-level peak-memory policy. Conversely, shortening a familiar temporary's lifetime alone is not an independent algorithmic contribution.

## 3. PM-tree and bulk-loader boundaries

[PM-tree §§3.2–3.3](https://ceur-ws.org/Vol-98/paper3.pdf) generates hyper-rings from pivot distances and unions child metadata on split. These are mathematical ranges, not automatically directed arithmetic intervals. [M-tree bulk loading](https://www-db.disi.unibo.it/research/papers/ADC98.pdf) reuses distances for construction decisions but explicitly updates upper-region radii after attachment. [Slim-tree](https://www.cs.cmu.edu/~christos/PUBLICATIONS/EDBT_SlimTree.pdf) retains optional membership-changing Slim-down. Neither should be overclaimed as eliminating every independent certificate pass.

## 4. Spatial build controls

[Karras §4](https://research.nvidia.com/sites/default/files/pubs/2012-06_Maximizing-Parallelism-in/karras2012hpg_paper.pdf) incorporates bounds in the GPU build pipeline but retains separate bottom-up AABB propagation after topology. [GPU kd-tree construction](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2008-52.pdf) uses in-build reductions or sorted extrema; [STR](https://ia600900.us.archive.org/27/items/nasa_techdoc_19970016975/19970016975.pdf) supplies bounding rectangles through packing. Integrated bounds are established; literal single-kernel fusion is a separate claim.

## 5. Numerical controls do not fill the whole joint mechanism

[CGAL filtering](https://doc.cgal.org/Manual/3.3.1/doc_html/cgal_manual/Kernel_23_ref/Class_Filtered_kernel.html) separates underlying constructions from certified predicates. [CUDA directed doubles](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html) provide the arithmetic primitives. [Ize](https://jcgt.org/published/0002/02/02/paper.pdf) studies robust traversal and origin-dependent construction padding. These defeat broad claims that dual numeric roles or GPU directed arithmetic are new, but are not a published metric-tree producer preserving the exact legacy order and exact GTSPP endpoint bits.

**Inference:** the straightforward composition is a strong competing explanation. Exact 5M overlap is a workload-specific opportunity, not by itself a novel dependency. An implementation win over the redundant two-pass baseline would establish usefulness, not novelty over this composition.
