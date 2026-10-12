# Evidence cards

Four families: A dynamic metric trees; B incremental hierarchy; C explicit stability; D deferred/buffered rebuilding.

`PARTIAL` means state survives some updates, not that every pivot/boundary survives deletion or reconstruction. `UNCLEAR` is missing evidence in the reviewed source, not proof the method cannot support the operation.

## egnat — Fully Dynamic Metric Access Methods based on Hyperplane Partitioning

**Paper/source:** [Fully Dynamic Metric Access Methods based on Hyperplane Partitioning](https://users.dcc.uchile.cl/~gnavarro/ps/is11.pdf)

**Year/venue:** 2011, Information Systems 36(4):734–747. **Family:** A/C/D.

**Evidence locator:** Sections 2–3, especially 3.1–3.2; conclusions; PDF pages 3, 4, 5, 17 (1-based).

- **Data/query type:** General metric objects; range search
- **Exact or approximate:** Exact range; kNN reduction discussed, not a GPU kNN evaluation
- **Dynamic update — insert:** Route to nearest existing center; append to bucket; full bucket becomes an internal GNAT node.
- **Dynamic update — delete:** Remove bucket object directly. Replace deleted internal center, retain old ranges and membership, accumulate replacement-distance tolerance.
- **Partition representation:** Centers, historical Voronoi/hyperplane memberships, ranges and per-center tolerance I_v.
- **Does existing partition decision persist after update?:** PARTIAL: old memberships survive center replacement; new insertions follow the new center. This is not one immutable boundary for both generations.
- **When does repartition happen?:** Bucket capacity causes local expansion. Rebuild when accumulated tolerance makes queries inefficient is explicitly suggested, not a calibrated implemented trigger.
- **Does it identify structural instability?:** YES: expensive subtree reconstruction after center deletion is the stated problem.
- **Does it explicitly target stability?:** YES for avoiding immediate reorganization while retaining exact search; NO claim of quantified GTS sparse-update churn.
- **Nearest overlap:** Retain historical decisions, admit updates locally, widen exact pruning and defer repair until quality degrades.
- **Key difference:** Hyperplane rather than radial quantile partitioning; tolerance reduces pruning; no packed GPU maintenance.
- **Novelty risk:** HIGH
- **Material caveat:** Center identity itself changes. Conclusions call systematic subtree-reconstruction policy study future work.

## dsat — Improved Deletions in Dynamic Spatial Approximation Trees

**Paper/source:** [Improved Deletions in Dynamic Spatial Approximation Trees](https://users.dcc.uchile.cl/~gnavarro/ps/sccc03.pdf)

**Year/venue:** 2003, SCCC. **Family:** A/D.

**Evidence locator:** Sections 2.1–2.3, 3.1–3.3.1, 4; PDF pages 2, 3, 4, 5, 6, 7, 8, 9 (1-based).

- **Data/query type:** General metric space; range search
- **Exact or approximate:** Exact range
- **Dynamic update — insert:** Follow existing neighbors with bounded arity; add a child and timestamp, update covering radii.
- **Dynamic update — delete:** Compare subtree reinsertion, timestamp-ordered reconstruction, and content-free fake nodes. The combined method retains fake nodes until a subtree fake fraction exceeds alpha.
- **Partition representation:** Neighbor objects, insertion timestamps, radii; fake nodes preserve topology but not deleted object content.
- **Does existing partition decision persist after update?:** PARTIAL: historical paths survive deferred deletion; pruning must account for insertion history and fake nodes.
- **When does repartition happen?:** Combined method rebuilds affected subtree when fake-node fraction exceeds alpha; optimized reconstruction skips unaffected older history.
- **Does it identify structural instability?:** YES: deletion can change later insertion decisions and degrade search quality.
- **Does it explicitly target stability?:** YES for sustainable search/update tradeoff; not measured leaf-signature stability.
- **Nearest overlap:** Exact metric history preservation plus an evaluated explicit deferred-repair threshold.
- **Key difference:** Timestamp/neighbor scheme, not fixed GTS quantiles; fake nodes increase traversal.
- **Novelty risk:** HIGH
- **Material caveat:** Rebuild scope may include younger sibling descendants and affected ancestors, not just the deleted node’s descendants. Does not promise zero churn.

## dvp_publisher — Dynamic vp-tree indexing for n-nearest neighbor search given pair-wise distances

**Paper/source:** [Dynamic vp-tree indexing for n-nearest neighbor search given pair-wise distances](https://link.springer.com/content/pdf/10.1007/PL00010672.pdf)

**Year/venue:** 2000, The VLDB Journal 9:154–173. **Family:** A/B.

**Evidence locator:** Sections 2, 5.1–5.3; PDF pages 3, 9, 10, 11, 12, 13, 14, 15, 16 (1-based).

- **Data/query type:** Pairwise metric distances; nearest-neighbor retrieval
- **Exact or approximate:** Exact under the metric pruning contract
- **Dynamic update — insert:** Traverse radial intervals. Insert without redistribution when target leaf has room; otherwise redistribute siblings or split/rebuild selected subtrees.
- **Dynamic update — delete:** Remove from leaf; underflow invokes redistribution or merge and possibly root contraction.
- **Partition representation:** Vantage points and ordered radial distance intervals.
- **Does existing partition decision persist after update?:** PARTIAL: ordinary updates retain existing decisions; redistribution changes intervals and non-leaf splits invoke subtree construction.
- **When does repartition happen?:** Page capacity, ancestor room and minimum occupancy/fanout; root event can be global.
- **Does it identify structural instability?:** YES: Section 5 explicitly explains parent-to-child split propagation and possible global reorganization.
- **Does it explicitly target stability?:** YES for limiting substantial restructuring while maintaining balance, not explicit decision leases.
- **Nearest overlap:** The same radial hierarchy already treats decision reuse as the default and structural events as conditional.
- **Key difference:** Redistribution can still alter many memberships; not guaranteed stability across every rebuild.
- **Novelty risk:** HIGH
- **Material caveat:** Deletion of an indexed object is specified. Separate physical erasure/lifetime of an internal VP copy is not fully resolved here; do not assert arbitrary representatives disappear immediately.

## pkd — Parallel kd-tree with Batch Updates

**Paper/source:** [Parallel kd-tree with Batch Updates](https://pal.cs.ucr.edu/papers/2025/SIGMOD25/pkdtree.pdf)

**Year/venue:** 2025, PACMMOD 3(1), article 62 (SIGMOD). **Family:** B/D.

**Evidence locator:** Sections 4.1–4.2, 5, 6.5; PDF pages 9, 10, 11, 19 (1-based).

- **Data/query type:** Coordinate-space points; kNN, range/report/count
- **Exact or approximate:** Exact queries; coordinate-dependent, not an arbitrary-metric index
- **Dynamic update — insert:** Sieve a batch through existing splitters; recurse into balanced subtrees; reconstruct the first subtree that would become unbalanced.
- **Dynamic update — delete:** Two rounds: locate actual deletions/discard absent requests, then remove and identify imbalance for selective reconstruction.
- **Partition representation:** Axis splitters, subtree sizes, weight-balanced hierarchy.
- **Does existing partition decision persist after update?:** PARTIAL: splitters persist outside explicitly reconstructed subtrees.
- **When does repartition happen?:** Each child size must stay within (0.5-alpha) to (0.5+alpha) of parent; violations reconstruct locally.
- **Does it identify structural instability?:** YES: nested spatial regions prevent ordinary rotations; lazy reconstruction avoids rebuilding after every update.
- **Does it explicitly target stability?:** YES for amortized update/query balance; no metric-pivot identity objective.
- **Nearest overlap:** Recent parallel preserve-by-default plus thresholded partial reconstruction, with query-quality tradeoff studied.
- **Key difference:** Shared-memory kd-tree, coordinate splitters and cache-efficient batch algorithms, not a GTS CUDA metric tree.
- **Novelty risk:** HIGH
- **Material caveat:** A future parallel/GPU port needs an independent mechanism; batching or physical-layout engineering alone is not sufficient novelty.

## ikdtree — ikd-Tree: An Incremental K-D Tree for Robotic Applications

**Paper/source:** [ikd-Tree: An Incremental K-D Tree for Robotic Applications](https://arxiv.org/pdf/2102.10808)

**Year/venue:** 2021, arXiv:2102.10808v1. **Family:** B/D.

**Evidence locator:** Sections III.C–D; PDF pages 2, 3, 4, 5 (1-based).

- **Data/query type:** LiDAR/coordinate points; nearest neighbor and box operations
- **Exact or approximate:** Exact search on the maintained set; optional downsampling changes that set
- **Dynamic update — insert:** Compare coordinates on existing division axes, append locally; reinsertion clears lazy-delete labels.
- **Dynamic update — delete:** Point/box lazy deletion, propagated labels; physically discard invalid nodes during reconstruction.
- **Partition representation:** Point/axis boundaries, subtree sizes, invalid counts and coordinate ranges.
- **Does existing partition decision persist after update?:** PARTIAL: existing split planes remain until selective rebuild.
- **When does repartition happen?:** Child-size alpha-balance or invalid-node alpha-deleted violation; small rebuild synchronous, large rebuild may use another thread.
- **Does it identify structural instability?:** YES: small newly acquired frames make whole-tree rebuilding wasteful.
- **Does it explicitly target stability?:** YES for incremental local maintenance with monitored quality; not formal pivot-decision churn.
- **Nearest overlap:** Sparse mutation, persistent decisions, explicit quality/size signals, selective reconstruction.
- **Key difference:** Coordinate kd-tree; no arbitrary-metric radial decision or GTS physical-plan reuse.
- **Novelty risk:** HIGH
- **Material caveat:** Do not equate exact search after downsampling with exact search over discarded raw points; no cross-GPU speedup imported.

## mtree — M-tree: An Efficient Access Method for Similarity Search in Metric Spaces

**Paper/source:** [M-tree: An Efficient Access Method for Similarity Search in Metric Spaces](https://www.vldb.org/conf/1997/P426.PDF)

**Year/venue:** 1997, VLDB:426–435. **Family:** A/B.

**Evidence locator:** Sections 3.3–3.4, 4; PDF pages 5, 6 (1-based).

- **Data/query type:** General metric objects; range and kNN
- **Exact or approximate:** Exact
- **Dynamic update — insert:** Choose covering/least-enlargement subtree, append to leaf and enlarge necessary radii.
- **Dynamic update — delete:** UNCLEAR in this primary article: Section 3.3 explicitly omits deletion due to space; underflow algorithm not provided.
- **Partition representation:** Routing representatives, covering balls, parent distances.
- **Does existing partition decision persist after update?:** PARTIAL: representatives and memberships persist on ordinary insertion; bounds can enlarge.
- **When does repartition happen?:** Overflow splits a page, promotes representatives and can propagate to root. No periodic global rebuild policy specified.
- **Does it identify structural instability?:** YES for costly reorganization of static top-down metric trees, not the new GTS churn metric.
- **Does it explicitly target stability?:** NO dedicated sparse-update partition-identity objective; efficient balanced dynamism is central.
- **Nearest overlap:** Local admission with decision retention between explicit structural events is established.
- **Key difference:** Overlapping ball hierarchy instead of balanced radial quantiles.
- **Novelty risk:** HIGH
- **Material caveat:** No completed insert/delete stability proof from this article; routing object changes at split remain possible.

## pmtree — Pivoting M-tree: A Metric Access Method for Efficient Similarity Search

**Paper/source:** [Pivoting M-tree: A Metric Access Method for Efficient Similarity Search](https://ceur-ws.org/Vol-98/paper3.pdf)

**Year/venue:** 2004, DATESO:27–37 (CEUR Vol.98). **Family:** A/C.

**Evidence locator:** Sections 3.2–3.3; PDF pages 5, 6 (1-based).

- **Data/query type:** General metric objects; similarity range search
- **Exact or approximate:** Exact metric filtering
- **Dynamic update — insert:** M-tree path insertion plus update hyper-ring bounds and leaf pivot-distance arrays.
- **Dynamic update — delete:** UNCLEAR: full deletion handling, particularly physical deletion of a lifetime pivot, is not specified in the reviewed paper.
- **Partition representation:** M-tree balls intersected with rings around a lifetime-fixed global pivot set.
- **Does existing partition decision persist after update?:** PARTIAL: YES for global filter pivots across index lifetime; NO guarantee that local routing/split identities are fixed.
- **When does repartition happen?:** M-tree node splitting creates new hyper-ring arrays. No quantified stability/quality-trigger rebuild policy.
- **Does it identify structural instability?:** NO dedicated update-induced structural-churn identification.
- **Does it explicitly target stability?:** NO; goal is tighter regions and efficient filtering.
- **Nearest overlap:** Fixed/persistent pivot vocabulary and pivot-distance reuse are not new.
- **Key difference:** Filter anchors are not the per-node decisions that choose GTS child memberships.
- **Novelty risk:** MEDIUM
- **Material caveat:** Do not equate a fixed global pivot set with unchanged tree partition decisions.

## slim — Slim-trees: High Performance Metric Trees Minimizing Overlap Between Nodes

**Paper/source:** [Slim-trees: High Performance Metric Trees Minimizing Overlap Between Nodes](https://www.cs.cmu.edu/~christos/PUBLICATIONS/EDBT_SlimTree.pdf)

**Year/venue:** 2000, EDBT:51–61 (long author manuscript). **Family:** A/B.

**Evidence locator:** Sections 4–6; PDF pages 3, 4, 5, 8, 9 (1-based).

- **Data/query type:** General metric objects; similarity queries
- **Exact or approximate:** Exact metric search
- **Dynamic update — insert:** ChooseSubtree aims at good occupancy; split overflowing node using MST clustering and group representatives.
- **Dynamic update — delete:** UNCLEAR for a full deletion/underflow path in the reviewed paper. Slim-down’s relocation/removal is not a general deletion contract.
- **Partition representation:** Ball representatives and radii, MST split; overlap measured by fat/bloat factors.
- **Does existing partition decision persist after update?:** PARTIAL: ordinary insertions retain representatives; splits and quality optimization can redistribute membership.
- **When does repartition happen?:** Capacity split; Slim-down postprocess or after a direct descendant split. Quality measures identify room for improvement, not an automatic stable-decision threshold.
- **Does it identify structural instability?:** NO dedicated sparse-update identity-instability characterization.
- **Does it explicitly target stability?:** NO; explicitly optimizes overlap/search quality.
- **Nearest overlap:** Local dynamic admission plus explicit quality-driven reorganization.
- **Key difference:** It intentionally moves objects to reduce overlap rather than protecting old partition identity.
- **Novelty risk:** MEDIUM
- **Material caveat:** The after-split optimization is implemented; other variants are proposals. Do not claim every quality threshold is experimentally calibrated.

## mvp — Indexing Large Metric Spaces for Similarity Search Queries

**Paper/source:** [Indexing Large Metric Spaces for Similarity Search Queries](https://www.cs.cmu.edu/~eugene/refs/f-series/Bozkaya-ozsoyoglu-99.pdf)

**Year/venue:** 1999, ACM TODS 24(3):361–404. **Family:** A.

**Evidence locator:** Sections 7.1–7.2, 9; extended version of SIGMOD 1997; PDF pages 30, 31, 32, 41, 42 (1-based).

- **Data/query type:** General metric objects; similarity range search
- **Exact or approximate:** Exact metric filtering; similarity is not ANN answer approximation
- **Dynamic update — insert:** Section 7.2 proposes downward growth if balance may be violated; implementation/evaluation explicitly future work.
- **Dynamic update — delete:** UNCLEAR: Section 9 says efficient insert/delete handling remains open.
- **Partition representation:** Multiple per-node vantage points, equal-cardinality radial partitions, cached pivot distances.
- **Does existing partition decision persist after update?:** PARTIAL/proposed: retain VPs and cached distances for reuse during restructuring; not an evaluated dynamic mechanism.
- **When does repartition happen?:** Suggested global restructuring when inserted distribution skews the tree; no explicit numerical trigger.
- **Does it identify structural instability?:** YES: skew under insertion and expensive global restructuring are discussed.
- **Does it explicitly target stability?:** NO dedicated churn minimization objective.
- **Nearest overlap:** Reuse the same vantage points and precomputed distances across restructuring is explicitly anticipated.
- **Key difference:** Static/evaluated bulk structure; dynamic semantics and quality-trigger implementation missing.
- **Novelty risk:** MEDIUM
- **Material caveat:** Do not label original/extended MVP-tree fully dynamic, or ignore its proposed same-pivot restructuring reuse.

## gnat — Near Neighbor Search in Large Metric Spaces

**Paper/source:** [Near Neighbor Search in Large Metric Spaces](https://www.vldb.org/conf/1995/P574.PDF)

**Year/venue:** 1995, VLDB:574–584. **Family:** A.

**Evidence locator:** Sections 4.1–4.3 (build/search/degree selection); PDF pages 6, 7 (1-based).

- **Data/query type:** General metric objects; range search
- **Exact or approximate:** Exact under triangle inequality
- **Dynamic update — insert:** UNCLEAR: reviewed original describes recursive bulk construction, not a dynamic admission algorithm.
- **Dynamic update — delete:** UNCLEAR: no complete dynamic deletion mechanism specified.
- **Partition representation:** Split centers, nearest-center domains and pairwise distance ranges.
- **Does existing partition decision persist after update?:** UNCLEAR under updates; centers persist only for a built static tree.
- **When does repartition happen?:** Recursive build and adaptive degree; no update-trigger rebuild contract.
- **Does it identify structural instability?:** NO dedicated update-induced partition instability.
- **Does it explicitly target stability?:** NO; goal is reflecting intrinsic geometry and effective pruning.
- **Nearest overlap:** Hierarchical decision representation is antecedent to dynamic GNAT variants.
- **Key difference:** Dynamic guarantees belong to later EGNAT/code, not the 1995 paper.
- **Novelty risk:** LOW
- **Material caveat:** Occurrences of insert/delete in edit-distance examples do not establish dynamic index updates.

## cover — Cover Trees for Nearest Neighbor

**Paper/source:** [Cover Trees for Nearest Neighbor](https://www.hunch.net/~jl/projects/cover_tree/paper/paper.pdf)

**Year/venue:** 2006, ICML (long author version). **Family:** A/B.

**Evidence locator:** Sections 2.2.3–2.2.4, Algorithms 2–3; PDF pages 5, 6 (1-based).

**Official auxiliary metadata:** [project page](https://www.hunch.net/~jl/projects/cover_tree/cover_tree.html)

- **Data/query type:** General metric objects; nearest neighbor
- **Exact or approximate:** Exact nearest neighbor
- **Dynamic update — insert:** Find a covering parent at a compatible scale; preserve nesting, covering and separation.
- **Dynamic update — delete:** Remove occurrences across levels; reparent/promote children to restore covering constraints.
- **Partition representation:** Representatives at discrete scales and cover links; not disjoint quantile partitions.
- **Does existing partition decision persist after update?:** PARTIAL: unaffected links survive; deleted representatives require local repairs.
- **When does repartition happen?:** Metric invariants immediately dictate repair; no deferred quality-threshold/global rebuild schedule specified.
- **Does it identify structural instability?:** NO GTS-like sparse-update radial instability characterization.
- **Does it explicitly target stability?:** NO dedicated partition-identity stability goal.
- **Nearest overlap:** Exact dynamic metric indexing does not inherently require whole-tree rebuilding.
- **Key difference:** Scale-based cover structure, not packed radial partition persistence.
- **Novelty risk:** MEDIUM
- **Material caveat:** Author project page reports an insertion-pseudocode issue. This card establishes documented operations, not implementation correctness or disputed asymptotic bounds.

## sihc — SIHC: A Stable Incremental Hierarchical Clustering Algorithm

**Paper/source:** [SIHC: A Stable Incremental Hierarchical Clustering Algorithm](https://www.scitepress.org/PublishedPapers/2009/18571/18571.pdf)

**Year/venue:** 2009, ICEIS:300–304. **Family:** C.

**Evidence locator:** Introduction, Section 3, Algorithm 1; PDF pages 1, 2, 3 (1-based).

- **Data/query type:** Hierarchical clustering/dendrograms, not a query index
- **Exact or approximate:** Not an exact range/kNN retrieval contract; not identical to full-batch SAHN
- **Dynamic update — insert:** Descend nearest child; add a new parent/singleton at the height-distance condition; update visited heights.
- **Dynamic update — delete:** UNCLEAR: no deletion algorithm provided.
- **Partition representation:** Cluster hierarchy, merge heights and proximity measures.
- **Does existing partition decision persist after update?:** YES for old hierarchy topology under insertion; heights can change.
- **When does repartition happen?:** Insertion creates a node, does not rebuild prior hierarchy; no quality-failure reconstruction threshold specified.
- **Does it identify structural instability?:** YES: a few added cases can dramatically change the whole dendrogram.
- **Does it explicitly target stability?:** YES: stability and user comprehensibility are the explicit central goal.
- **Nearest overlap:** Avoiding small-update/large-hierarchy change is established outside exact metric indexing.
- **Key difference:** Clustering-quality objective and insertion-only topology, no exact query or dynamic deletion contract.
- **Novelty risk:** MEDIUM
- **Material caveat:** Not a same-setting KILL-1 by itself; its quality experiments cannot validate GTS pruning.

## bdl — Parallel Batch-Dynamic kd-trees

**Paper/source:** [Parallel Batch-Dynamic kd-trees](https://arxiv.org/pdf/2112.06188)

**Year/venue:** 2021, arXiv:2112.06188. **Family:** D/B.

**Evidence locator:** Sections IV.A.2, IV.B.1–3; Algorithms 3–5; PDF pages 4, 5, 6, 7 (1-based).

- **Data/query type:** Coordinate kd-tree forest; batched kNN
- **Exact or approximate:** Exact kNN over all live components
- **Dynamic update — insert:** Buffer and logarithmic carry: combine new/buffer/component points to build selected static trees.
- **Dynamic update — delete:** Mark leaf deletions and collapse empty branches; under-half-full components are dismantled and survivors reinserted.
- **Partition representation:** Log-structured static kd-tree components plus a dynamic buffer.
- **Does existing partition decision persist after update?:** PARTIAL: untouched component partitions persist; rebuilt components can change all decisions.
- **When does repartition happen?:** Capacity/carry on insert; component occupancy below half on delete.
- **Does it identify structural instability?:** YES for the cost of rebuilding with every batch; no recursive metric-pivot churn measurement.
- **Does it explicitly target stability?:** NO dedicated identity stability objective; amortized batch maintenance/query tradeoff.
- **Nearest overlap:** Buffered/deferred rebuilding can retain most existing decisions between merges.
- **Key difference:** Multiple query components and merge costs; deferral is not identity preservation through reconstruction.
- **Novelty risk:** MEDIUM
- **Material caveat:** Logarithmic buffering alone is not a new stable-partition mechanism, and query fanout must be charged.

## gnat2013 — Resolution Independent Density Estimation for Motion Planning in High-Dimensional Spaces

**Paper/source:** [Resolution Independent Density Estimation for Motion Planning in High-Dimensional Spaces](https://www.cs.rice.edu/~mmoll/publications/gipson2013resolution-independent-density-estimation.pdf)

**Year/venue:** 2013, ICRA. **Family:** B/D.

**Evidence locator:** Section III, Algorithm 1 and GNAT rebuild policy; PDF pages 3, 4 (1-based).

- **Data/query type:** Motion-planning configuration spaces; GNAT density sampling
- **Exact or approximate:** GNAT uses a metric, but planner’s evaluated task is sampling/path planning, not an exact search benchmark
- **Dynamic update — insert:** Add accepted planning states to the GNAT and planning tree.
- **Dynamic update — delete:** UNCLEAR: planner paper does not establish dynamic GNAT deletion.
- **Partition representation:** GNAT branch pivots, child regions/radii and leaf configuration sets.
- **Does existing partition decision persist after update?:** PARTIAL: decisions retained between rebuilds; no protection during full reconstruction.
- **When does repartition happen?:** Evaluated policy rebuilds from scratch after approximately 10% node-count growth since the previous rebuild. Section III wording is imprecise; this is not total node count greater than 0.1 times the old size.
- **Does it identify structural instability?:** YES for balance degradation, not leaf-signature churn.
- **Does it explicitly target stability?:** NO dedicated decision-identity goal.
- **Nearest overlap:** Explicit deferred rebuild already appears in a GNAT application.
- **Key difference:** Growth heuristic and whole-structure rebuild, not accumulated stability signal.
- **Novelty risk:** MEDIUM
- **Material caveat:** This 10% growth policy is not the current OMPL header’s policy; do not mix paper and code versions.

## ompl_gnat — OMPL NearestNeighborsGNAT.h (version-pinned official implementation)

**Paper/source:** [OMPL NearestNeighborsGNAT.h (version-pinned official implementation)](https://raw.githubusercontent.com/ompl/ompl/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/NearestNeighborsGNAT.h)

**Year/venue:** Source revision dated 2026-04-06. **Family:** A/D.

**Evidence locator:** Constructor and add/remove/rebuild; lines 95–109, 147–205, 444–489

- **Data/query type:** Official GNAT nearest/R/kNN API with a valid metric
- **Exact or approximate:** Exact metric-pruning API intent; not executed/validated in this task
- **Dynamic update — insert:** Route to closest existing pivot, update ranges/radii, append to leaf; split leaf when size exceeds max leaf size and degree.
- **Dynamic update — delete:** Cache removals; removing a pivot immediately rebuilds the entire GNAT; cache capacity also triggers full rebuild.
- **Partition representation:** Pivots, per-child distance ranges, radii, leaf data and removed cache.
- **Does existing partition decision persist after update?:** PARTIAL: existing pivots/membership survive ordinary updates, not pivot deletion or rebuild.
- **When does repartition happen?:** Also rebuild on splitting with cached removals; optional size-based rebalance; re-adding cached object or changing metric can rebuild.
- **Does it identify structural instability?:** NO explicit sparse-update identity-stability objective in reviewed header.
- **Does it explicitly target stability?:** NO; practical nearest-neighbor maintenance.
- **Nearest overlap:** Implemented local admission and conditional deferred repair provide a concrete conceptual control.
- **Key difference:** Full rebuild for deleted pivot; no historical-boundary tolerance as in EGNAT.
- **Novelty risk:** HIGH
- **Material caveat:** Pinned revision 73bd861b15dd7d39129ceecf66b74387d3d84884, not moving docs. Default rebalancing=false; deletion/split cleanup can still rebuild.
