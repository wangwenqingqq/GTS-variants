# Nearest-prior-art matrix

Mechanism order, not publication chronology. Refits refer to initial build bounds/certification, not later scene updates.

| Work | Metric tree | Build distances → bounds | Bounds in build | Separate bound/refit pass | Directed safe certificate | Risk |
|---|---|---|---|---|---|---|
| [vp_mvp](https://www.cs.cmu.edu/~eugene/refs/f-series/Bozkaya-ozsoyoglu-99.pdf) | YES | YES | YES | NO | UNKNOWN | HIGH |
| [gnat](https://www.vldb.org/conf/1995/P574.PDF) | YES | YES | YES | NO | UNKNOWN | HIGH |
| [ompl_gnat](https://raw.githubusercontent.com/ompl/ompl/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/NearestNeighborsGNAT.h) | YES | YES | YES | NO | NO | HIGH |
| [pmtree](https://ceur-ws.org/Vol-98/paper3.pdf) | YES | YES | YES | NO | UNKNOWN | HIGH |
| [mtree_bulk](https://www-db.disi.unibo.it/research/papers/ADC98.pdf) | YES | PARTIAL | PARTIAL | CONDITIONAL | UNKNOWN | HIGH |
| [slim](https://www.cs.cmu.edu/~christos/PUBLICATIONS/EDBT_SlimTree.pdf) | YES | PARTIAL | PARTIAL | CONDITIONAL | UNKNOWN | MEDIUM |
| [karras2012](https://research.nvidia.com/sites/default/files/pubs/2012-06_Maximizing-Parallelism-in/karras2012hpg_paper.pdf) | NO | NO | PARTIAL | YES | UNKNOWN | HIGH |
| [gpu_kdtree](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2008-52.pdf) | NO | NO | PARTIAL | NO | UNKNOWN | HIGH |
| [str](https://ia600900.us.archive.org/27/items/nasa_techdoc_19970016975/19970016975.pdf) | NO | NO | YES | NO | UNKNOWN | MEDIUM |
| [robust_bvh](https://jcgt.org/published/0002/02/02/paper.pdf) | NO | NO | NO | UNKNOWN | PARTIAL | MEDIUM |
| [cgal_filtered](https://doc.cgal.org/Manual/3.3.1/doc_html/cgal_manual/Kernel_23_ref/Class_Filtered_kernel.html) | NO | NO | NO | UNKNOWN | PARTIAL | MEDIUM |
| [cuda_double](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html) | NO | NO | NO | UNKNOWN | YES | MEDIUM |
| GTSPP proposed dual producer | YES | TARGET | TARGET | TARGET: remove D960 distance sweep | TARGET: frozen bit-exact FP64 lo/hi | UNPROVEN |

**Reading rule:** ranges in VP/GNAT/PM-tree are mathematical pruning intervals, not proof of floating-point enclosure. CUDA YES is arithmetic capability only; CGAL/Ize PARTIAL are different numerical controls. M-tree retains upper-region radius update; Slim-down changes membership; Karras retains bottom-up AABB propagation. See [cards](EVIDENCE_CARDS.md) for the exact scope and unknowns.
