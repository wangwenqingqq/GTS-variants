# Gate 0: established baseline, not a new thesis

The core mechanism (dimensionality reduction, low-dimensional rectangles and
lower-bound filter/refine exact search) is established. This bounded experiment
is a representation diagnosis on the frozen GTS tree, not a novelty claim or a
GPU performance campaign. Engineering a safer numerical implementation does not
rescue the mechanism as a novel paper thesis.

| Nearest primary source | Established mechanism | Consequence |
|---|---|---|
| [Seidl and Kriegel, VLDB 1997](https://www.vldb.org/conf/1997/P506.PDF), Sections 3–4 | Database PCA/KLT, linear reduction, spatial bounding rectangles and lower-bounding filter/refine search | PCA plus a projected box is prior art; do not name it a new index contribution |
| [Roussopoulos et al., SIGMOD 1995](https://www.cs.umd.edu/~nick/papers/nnpaper.pdf) | Rectangle MINDIST in nearest-neighbor traversal | Joint squared coordinate gaps are classical rectangle geometry |
| [Weber et al., VLDB 1998](https://www.vldb.org/conf/1998/p194.pdf) | VA-file approximation/filtering and high-dimensional selectivity tradeoffs | Small summaries and scan/refinement tradeoffs need a strong same-contract comparator |
| [G-PICS technical report](https://cse.usf.edu/~tuy/pub/tech09-002.pdf) | GPU similarity search with exact refinement/filtering context | A GPU implementation alone does not establish novelty |
| [GTS, 2024](https://arxiv.org/html/2404.00966v1) | GPU metric-tree execution | This experiment tests an additional certificate on its existing ownership; it does not rebuild or benchmark another GPU index |

A norm-at-most-one linear operator is contractive by the definition of operator
norm. The exact-rational check below validates the stored matrix, not a new
mathematical theorem. Random orthogonal directions are the non-adaptive control;
PCA is the classic database-adaptive baseline. No approximate-search recall
contract is substituted for exact safety. A positive offline result would only
justify a separate novelty test for an execution/co-design mechanism; a negative
result would reject these two frozen projected-AABB families on this slice, not
all linear summaries, all partitions, or all GPU trees.
