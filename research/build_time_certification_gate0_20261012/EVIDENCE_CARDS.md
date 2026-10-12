# Evidence cards

Checked on 2026-10-12. These are original paraphrases, not redistributed full texts.
YES fusion means algorithmic integration of topology and bound metadata, **not necessarily one kernel**. NO refit means no separate numeric certification pass in the described recipe, **not proof of a measured pass removal**. UNKNOWN is not NO.

## vp_mvp — Indexing Large Metric Spaces for Similarity Search Queries

- **Family:** A/C
- **Year / venue:** 1999, ACM TODS 24(3):361–404
- **Index type:** Metric VP/MVP
- **Exact or approximate:** Exact metric search in the mathematical distance model
- **Construction stages:** Compute vantage distances; order and partition at medians/cutoffs; record query metadata; recursively build children.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** YES
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** YES
- **Numeric contract:** Mathematical metric values; no explicit directed FP64 rounding contract established.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** VP child shells use min/max build distances; MVP medians and selected stored PATH distances support later pruning.
- **Key difference:** No joint unchanged-native-FP32 ordering plus separately rounded FP64 certificate demonstrated.
- **Novelty risk:** HIGH
- **Material caveat:** NO refit describes the published construction recipe, not a measured elimination against GTSPP. MVP persistent PATH arrays are not ephemeral sidecars.
- **Exact checked location:** PDF p3, Section 3.3 pp10–11; Section 4.2 pp14–16
- **Primary evidence:** [mvp](https://www.cs.cmu.edu/~eugene/refs/f-series/Bozkaya-ozsoyoglu-99.pdf)

## gnat — Near Neighbor Search in Large Metric Spaces

- **Family:** A/C
- **Year / venue:** 1995, VLDB:574–584
- **Index type:** Metric GNAT
- **Exact or approximate:** Exact range search in the mathematical metric model
- **Construction stages:** Select split points; assign objects to nearest split point; form cross-region min/max distance ranges; recurse.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** YES
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** YES
- **Numeric contract:** Mathematical min/max ranges; directed floating-point enclosure not specified.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Construction expressly reuses within-node distances for query-pruning ranges; no later coordinate-distance certification stage is in the simplified recipe.
- **Key difference:** Multi-center Voronoi membership is not native GTS equal-cardinality ordering; no dual arithmetic producer contract.
- **Novelty risk:** HIGH
- **Material caveat:** The paper establishes algorithmic reuse, not exact source arithmetic or one-kernel GPU fusion.
- **Exact checked location:** Section 4.1 and preceding motivation, PDF p6 (printed p579)
- **Primary evidence:** [gnat](https://www.vldb.org/conf/1995/P574.PDF)

## ompl_gnat — NearestNeighborsGNAT.h

- **Family:** C/A
- **Year / venue:** Pinned source revision
- **Index type:** Metric GNAT implementation
- **Exact or approximate:** Exact-search intent under a caller-supplied metric; floating-point safety depends on that callback
- **Construction stages:** GreedyKCenters fills a double matrix; argmin assigns members; the same matrix updates radii and cross-region ranges; recurse.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** YES
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** YES
- **Numeric contract:** double callback distances with ordinary comparisons/min/max, not outward-directed interval pairs.
- **Safe interval capability:** NO
- **Nearest overlap:** A concrete producer/consumer control: dists(j,i) serves split decisions and persistent pruning metadata without another distance callback for bounds.
- **Key difference:** No FP32 legacy-order/FP64 sidecar pair. Matrix is local to split, but remains alive through child recursion: not proven one-level peak scratch.
- **Novelty risk:** HIGH
- **Material caveat:** NO separate refit is scoped to this split flow. Parent data capacity transfers to local tmp; both tmp and dists remain alive through child recursion and are destroyed when split returns.
- **Exact checked location:** GNAT lines 416–442, 494–541, 594–609, 646–659; KCenters lines 74–119
- **Primary evidence:** [ompl_gnat](https://raw.githubusercontent.com/ompl/ompl/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/NearestNeighborsGNAT.h), [ompl_kcenters](https://raw.githubusercontent.com/ompl/ompl/73bd861b15dd7d39129ceecf66b74387d3d84884/src/ompl/datastructures/GreedyKCenters.h)

## pmtree — Pivoting M-tree: A Metric Access Method for Efficient Similarity Search

- **Family:** A/C
- **Year / venue:** 2004, DATESO:27–37 (CEUR Vol.98)
- **Index type:** Metric PM-tree
- **Exact or approximate:** Exact metric-search intent; optional compressed pivot metadata is discussed separately
- **Construction stages:** Choose lifetime-fixed pivots; insertion updates ancestor hyper-rings and leaf pivot distances; split unions child intervals or leaf distances.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** YES
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** YES
- **Numeric contract:** Hyper-ring intervals are mathematical distance ranges, not an explicitly outward-rounded arithmetic interval evaluation.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Already-computed pivot distances and child ranges become pruning metadata during insert/split without a described post-build object-distance certification sweep.
- **Key difference:** Global pivots and persistent PD/HR metadata differ from GTS level-specific scoring and one-level sidecar.
- **Novelty risk:** HIGH
- **Material caveat:** This checked source describes insertion/splitting, not a dedicated PM-tree bulk loader. Do not relabel hyper-rings as directed FP64 certificates.
- **Exact checked location:** Sections 3.1–3.3, PDF pp5–6 (printed pp31–32)
- **Primary evidence:** [pmtree](https://ceur-ws.org/Vol-98/paper3.pdf)

## mtree_bulk — Bulk Loading the M-tree

- **Family:** A/C
- **Year / venue:** 1998, ADC (institution-hosted 12-page manuscript)
- **Index type:** Metric M-tree bulk loader
- **Exact or approximate:** Exact metric-search intent
- **Construction stages:** Sample and cluster; recursively build subtrees and supertree; redistribute/rebalance; attach subtrees; update upper-region radii.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** PARTIAL
- **Separate post-build refit/bound pass:** CONDITIONAL
- **Topology + bound integration:** PARTIAL
- **Numeric contract:** Mathematical metric distances and covering radii; floating-point enclosure unspecified.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Previous-level root distances and sample distances prune later construction calculations; covering metadata is part of assembly.
- **Key difference:** The pseudocode explicitly retains an upper-region radius-update step, so it does not establish elimination of all bound finalization.
- **Novelty risk:** HIGH
- **Material caveat:** Do not promote reuse for construction decisions into proof that every bound reuses the same scored pairs or that no additional distances are evaluated.
- **Exact checked location:** Sections 3–4, PDF pp3–6; Sections 5.1–5.2 pp6–7
- **Primary evidence:** [mtree_bulk](https://www-db.disi.unibo.it/research/papers/ADC98.pdf)

## slim — Slim-trees: High Performance Metric Trees Minimizing Overlap Between Nodes

- **Family:** A
- **Year / venue:** 2000, EDBT:51–61 (long author manuscript)
- **Index type:** Metric Slim-tree
- **Exact or approximate:** Exact metric-search intent
- **Construction stages:** Insert and split; MST splits weighted object graph and selects representatives; optional Slim-down relocates objects and corrects radii.
- **Build computes pivot/representative-object distances:** YES
- **Those distances reused for node bounds:** PARTIAL
- **Separate post-build refit/bound pass:** CONDITIONAL
- **Topology + bound integration:** PARTIAL
- **Numeric contract:** Mathematical representative distances and radii; interval arithmetic unspecified.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Split graph distances and representative/radius selection are closely coupled; query bounds are maintained as index metadata.
- **Key difference:** Slim-down is an explicit post-construction overlap optimization that changes membership, not GTSPP numeric certification.
- **Novelty risk:** MEDIUM
- **Material caveat:** The manuscript does not fix distance-matrix storage/reuse semantics for all bounds; no blanket separate-refit-removal claim.
- **Exact checked location:** Sections 3–4 pp3–5; Section 6 pp8–9, 16-page author version
- **Primary evidence:** [slim](https://www.cs.cmu.edu/~christos/PUBLICATIONS/EDBT_SlimTree.pdf)

## karras2012 — Maximizing Parallelism in the Construction of BVHs, Octrees, and k-d Trees

- **Family:** B
- **Year / venue:** 2012, High Performance Graphics
- **Index type:** GPU spatial BVH/radix hierarchy
- **Exact or approximate:** Geometric acceleration; no approximate-neighbor quality target
- **Construction stages:** Morton keys; sort; construct radix topology; then assign internal AABBs by leaf-to-root parallel propagation with atomic arrival counters.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** YES
- **Topology + bound integration:** PARTIAL
- **Numeric contract:** Geometric AABB union; directed FP64 metric certificate not specified.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Topology and bounds belong to the build pipeline, and propagation consumes recorded parent pointers.
- **Key difference:** Bounding-box propagation remains a distinct post-topology step; the single-kernel claim concerns radix topology, not topology plus all bounds.
- **Novelty risk:** HIGH
- **Material caveat:** Do not call a separate bottom-up bounding pass eliminated, nor equate AABB unions with D960 pivot/object arithmetic.
- **Exact checked location:** Section 4, PDF p4; GPU implementation paragraph preceding it
- **Primary evidence:** [karras2012](https://research.nvidia.com/sites/default/files/pubs/2012-06_Maximizing-Parallelism-in/karras2012hpg_paper.pdf)

## gpu_kdtree — Real-Time KD-Tree Construction on Graphics Hardware

- **Family:** B
- **Year / venue:** 2008, Microsoft Research institutional PDF (10 pages)
- **Index type:** GPU spatial kd-tree for triangles/points
- **Exact or approximate:** Acceleration and kNN application; finite-rounding guarantee not established
- **Construction stages:** BFS large/small-node stages; triangle AABB chunk and segmented reductions; split/clip; output layout. Photon version uses sorted coordinate extrema.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** PARTIAL
- **Numeric contract:** Spatial bounds; explicit directed interval certification not established.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Bounds are computed during level build; the photon variant obtains tight large-node boxes from maintained sorted coordinates.
- **Key difference:** Several GPU passes and output reordering remain; this is not a same-distance dual FP32/FP64 metric producer.
- **Novelty risk:** HIGH
- **Material caveat:** NO standalone post-build numeric refit in the described recipe does not mean bounds need no passes. Primary PDF read via web; local download unavailable.
- **Exact checked location:** Sections 3.1–3.3, PDF pp3–5; Section 5.1 p7
- **Primary evidence:** [gpu_kdtree](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/tr-2008-52.pdf)

## str — STR: A Simple and Efficient Algorithm for R-Tree Packing

- **Family:** B
- **Year / venue:** 1997, NASA CR-201661 / ICASE 97-14; report version
- **Index type:** Spatial R-tree packing
- **Exact or approximate:** Geometric intersection index
- **Construction stages:** Sort by rectangle centers; tile and pack leaves; enclosing node rectangles provide the input metadata at the next level.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** NO
- **Topology + bound integration:** YES
- **Numeric contract:** Bounding rectangles of input rectangles; no directed metric interval contract.
- **Safe interval capability:** UNKNOWN
- **Nearest overlap:** Packed groups immediately have bounding metadata; higher-level packing operates on those node rectangles.
- **Key difference:** Spatial rectangle union, not high-dimensional metric scoring or nominal-safe arithmetic separation.
- **Novelty risk:** MEDIUM
- **Material caveat:** NO independent numeric refit is scoped to the packing description. Archival NASA report has 34 PDF pages including front matter/blanks, not the shorter conference pagination.
- **Exact checked location:** Sections 2.1–2.2, PDF pp7–10
- **Primary evidence:** [str](https://ia600900.us.archive.org/27/items/nasa_techdoc_19970016975/19970016975.pdf)

## robust_bvh — Robust BVH Ray Traversal

- **Family:** D
- **Year / venue:** 2013, JCGT 2(2):12–28
- **Index type:** BVH numerical robustness
- **Exact or approximate:** Conservative ray/box traversal; not metric-neighbor indexing
- **Construction stages:** Analyze traversal error; pad inverse direction or exit distance. Construction-time bounding-box padding is evaluated as an alternative.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** UNKNOWN
- **Topology + bound integration:** NO
- **Numeric contract:** Conservative traversal error control, primarily FP32; not a dual metric-distance interval producer.
- **Safe interval capability:** PARTIAL
- **Nearest overlap:** Proves safe pruning needs a numeric contract, and considers bounds padded during construction.
- **Key difference:** Padding depends on admissible ray origins; the preferred controls are traversal-side, not same-pair build/refit fusion.
- **Novelty risk:** MEDIUM
- **Material caveat:** Generic robustness and construction padding are prior art, but this work neither specifies GTSPP bit-exact lo/hi nor an independent refit to remove.
- **Exact checked location:** Sections 2–3; Section 6 PDF pp13–14; Section 7 p16
- **Primary evidence:** [robust_bvh](https://jcgt.org/published/0002/02/02/paper.pdf)

## cgal_filtered — CGAL::Filtered_kernel<CK>

- **Family:** D
- **Year / venue:** Release 3.3.1, 25 August 2007
- **Index type:** Geometry kernel, not an index
- **Exact or approximate:** Exact predicates with potentially inexact geometric constructions
- **Construction stages:** Wrap kernel predicates in interval filters and exact fallback; underlying CK constructions remain the same.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** UNKNOWN
- **Topology + bound integration:** NO
- **Numeric contract:** Interval-filtered/exact predicates alongside unchanged, not necessarily exact CK constructions.
- **Safe interval capability:** PARTIAL
- **Nearest overlap:** Separate nominal construction and certified decision arithmetic is already a general numerical design.
- **Key difference:** No metric tree child-bound producer, shared D960 traversal, or post-build refit elimination is established.
- **Novelty risk:** MEDIUM
- **Material caveat:** This is a numerical control only. Exact predicates can affect decisions; retaining CK constructions does not prove unchanged legacy tree ordering.
- **Exact checked location:** Release 3.3.1: Definition, Example, Implementation
- **Primary evidence:** [cgal_filtered](https://doc.cgal.org/Manual/3.3.1/doc_html/cgal_manual/Kernel_23_ref/Class_Filtered_kernel.html)

## cuda_double — Double Precision Intrinsics

- **Family:** D
- **Year / venue:** CUDA Math API 13.1.0
- **Index type:** GPU arithmetic API, not an index
- **Exact or approximate:** Directed rounding primitives, not an exact-search algorithm
- **Construction stages:** Device double add/subtract/multiply/square-root expose explicit round-down and round-up variants.
- **Build computes pivot/representative-object distances:** NO
- **Those distances reused for node bounds:** NO
- **Separate post-build refit/bound pass:** UNKNOWN
- **Topology + bound integration:** NO
- **Numeric contract:** Directed FP64 operation semantics; a correct interval expression must still be composed and validated.
- **Safe interval capability:** YES
- **Nearest overlap:** Outward-directed arithmetic on GPU is an existing capability, not the proposed algorithmic novelty.
- **Key difference:** No topology, ownership, coordinate-load sharing, or tree-bound propagation recipe.
- **Novelty risk:** MEDIUM
- **Material caveat:** YES is arithmetic capability only, not a published tree certificate. CUDA 13.1 reference is a fixed documentation control, not a GPU/runtime verification this round.
- **Exact checked location:** CUDA Math API 13.1, Double Precision Intrinsics
- **Primary evidence:** [cuda_double](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html)
