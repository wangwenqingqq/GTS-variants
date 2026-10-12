# Gate 0: known geometry, diagnostic experiment only

Reviewed primary sources on 2026-10-12. Ball and ellipsoid enclosures are NOT a
novel contribution. This inexpensive frozen-input test is a diagnosis of the
current GTS certificate gap, not an attempt to revive a subsumed indexing thesis.

| Requested family | Primary source | Established mechanism / implication |
|---|---|---|
| Ball trees / covering radii | [Omohundro, Five Balltree Construction Algorithms, 1989](https://steveomohundro.com/wp-content/uploads/2009/03/omohundro89_five_balltree_construction_algorithms.pdf) | Nearest-neighbor branch-and-bound using distances to bounding balls is established. |
| Smallest enclosing balls | [Gaertner, Miniball reference and software](https://people.inf.ethz.ch/gaertner/subdir/software/miniball.html) | Robust smallest-ball construction exists; our fixed-iteration heuristic is not an exact implementation or an optimality proof. |
| Rectangle and sphere geometry for high-dimensional NN | [Katayama and Satoh, SR-tree, SIGMOD 1997](https://www.ri.cmu.edu/pub_files/pub3/katayama_norio_1997_2/katayama_norio_1997_2.pdf) | Sphere-versus-rectangle selectivity and hybrid enclosing regions are already examined in the same NN setting; paper explicitly relates region refinement to ellipses/circles/convex hulls. |
| R-tree bounding rectangles | [Guttman, SIGMOD 1984 DOI](https://doi.org/10.1145/602259.602266) | Axis-aligned enclosing rectangles are standard. Publisher endpoint could not be fetched; rectangle-versus-sphere context independently read in the primary SR-tree paper, not inferred from search summaries. |
| Minimum-volume enclosing ellipsoid | [Todd and Yildirim, On Khachiyan's Algorithm, author manuscript](https://people.orie.cornell.edu/miketodd/TYKhach.pdf) | MVEE/core-set optimization is established. Our centroid/diagonal-scale/factor enclosure is neither full-covariance nor a minimum-volume ellipsoid. |
| PCA bounding region / exact filter-and-refine | [Faloutsos et al., Fast Subsequence Matching, SIGMOD 1994](https://www.cs.cmu.edu/~christos/PUBLICATIONS.OLDER/sigmod94.pdf) | Contractive lower-dimensional filtering followed by original-space verification is an established structure; projection/filtering itself is not novelty. |

No separate ellipsoid-tree novelty is asserted: the primary SR-tree paper already
places ellipsoidal region approximation within known shape-refinement work, and
the primary MVEE work establishes enclosing ellipsoidal geometry. This is enough
to kill novelty of “replace a box with a ball/ellipsoid.” It does not establish
a performance comparison with any particular ellipsoid-tree implementation.

Allowed research question: within fixed P2 membership and PCA8, do three explicit
safe shapes improve frozen hard-query ancestor certifiability? A future GPU
co-design thesis would still require a non-incremental mechanism and decisive
same-contract end-to-end comparison against these established alternatives.
