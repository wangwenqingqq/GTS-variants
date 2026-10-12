# Search scope

## Question, budget and stopping rule

Candidate: preserve exact metric-index partition-decision identity by default
under sparse insert/delete, absorb changes locally, and repartition only when
an explicit stability/quality signal justifies it.

This task admits web retrieval and CPU reading only. No benchmark or mechanism
implementation is authorized until a separate PASS. Stop nearest-work expansion
once a primary-source counterexample decisively defeats generic mechanism
novelty and the mandatory named families have been checked; do not rescue a
subsumed thesis by adding more implementation work.

## Four families and completed coverage

| Family | Reviewed controls | Reason |
|---|---|---|
| A: dynamic metric trees | M-tree, Slim-tree, PM-tree, dynamic VP-tree, MVP-tree, GNAT, EGNAT, dsa-tree, Cover Tree, OMPL GNAT | Exact metric operations, representative lifetime, historical membership |
| B: incremental hierarchy | Dynamic VP-tree, ikd-Tree, Pkd-tree, BDL-tree, GNAT/STRIDE | Local admission, split/merge and partial reconstruction |
| C: explicit stability | EGNAT's old hyperplanes, SIHC, PM-tree's lifetime pivots | Separate historical decision preservation, dendrogram stability and filter-anchor persistence |
| D: deferred rebuilding | dsa-tree combined deletion, ikd-Tree, Pkd-tree, BDL-tree, GNAT/STRIDE, OMPL GNAT | Explicit quality/occupancy/carry triggers and amortization |

## Search trail

Completed searches combined the plan's concept seeds with method names. The
following are representative executed searches, not a claim that every
Cartesian combination was queried:

```text
"dynamic spatial approximation trees" Navarro Reyes deletion rebuild
"Improved Deletions in Dynamic Spatial Approximation Trees" 2003 IEEE
"Parallel kd-tree with Batch Updates" 2025 rebuild weight balanced
"persistent pivot" "metric" tree updates
"partition stability" "metric" dynamic index
"Stable Incremental Hierarchical" 2009 SIHC
"Resolution Independent Density Estimation" 2013 Gipson ICRA
```

Earlier discovery covered the named metric trees, ghost hyperplanes, stable
hierarchies and log-structured kd-trees. Followed primary references from EGNAT
to dsa-tree deletion and from ikd-Tree to partial/logarithmic reconstruction.
Author/publisher repositories were then read directly. Search snippets and
aggregators are routing aids, not the basis of technical assertions.

## Evidence standard and source provenance

All 14 paper cards use downloaded primary full text; OMPL is pinned to official
commit `73bd861b15dd7d39129ceecf66b74387d3d84884` (2026-04-06) and header SHA-256
`2a8b9c603a537e77db713d9f93776f8de47976433ac685f59394d77bd7ac7314`.
The [source manifest](evidence/SOURCES.json) gives the canonical URL, exact byte
hash, page count, and checked sections/pages. PDF locators are 1-based downloaded
PDF pages, not necessarily published page numbers. Long author versions are
identified; arXiv preprints are not silently relabeled as conference versions.

- EGNAT's 17-page author manuscript corresponds to Information Systems 2011.
- Dynamic VP-tree uses the publisher PDF, DOI `10.1007/PL00010672`.
- The 1999 MVP extension explicitly identifies its 1997 SIGMOD predecessor.
- PM-tree year/venue is checked against the official DATESO proceedings.
- Cover Tree's [official author project page](https://www.hunch.net/~jl/projects/cover_tree/cover_tree.html)
  identifies ICML 2006 and flags an insertion pseudocode issue. No implementation
  admission or complexity claim is made.
- The 2013 GNAT growth policy and the 2026 pinned OMPL header are distinct
  artifacts, not one unchanged algorithm.
- Deletion omitted in M-tree/Slim-tree/PM-tree is marked `UNCLEAR` rather than
  inferred from the word "dynamic". Similarity-query wording does not imply ANN.

## Negative/uncertain coverage

No reviewed source is asserted to quantify GTS's exact sparse-update,
radial-pivot-drift, leaf-signature churn and GPU-cost chain. This missing
observation does not prove a new mechanism. No reviewed method was run against
GTS under the same contract.

Boundary discoveries excluded from the decisive matrix:

- General stable clustering/layout work is not automatically exact indexing.
- A 2025 dynamic octree/multikernel-estimation preprint is not an arbitrary-metric
  index; abstract efficiency claims were not promoted to evidence.
- An R*-tree editing-maintenance item with a November 2026 issue date was found,
  but its first-publication timing relative to this search was not established.
  It is not used as a decisive antecedent; older metric work suffices.
- A primary M-tree bulkload paper was used for discovery, then superseded by
  direct reading of the MVP original extended source.

This finite search supports a positive overlap finding, not an exhaustive
absence-of-prior-art assertion. Reopen only for a clearly specified different
mechanism, with a fresh nearest-work screen for that mechanism.
