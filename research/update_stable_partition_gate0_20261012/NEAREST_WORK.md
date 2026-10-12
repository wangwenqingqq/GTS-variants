# Five nearest controls

These are ranked by mechanism overlap, not year or citation count. Full source
locators and limitations are in [the evidence cards](EVIDENCE_CARDS.md).

| Control | Problem solved | Persistent state | Structural trigger | Identity/churn boundary | What GTS++ would still need |
|---|---|---|---|---|---|
| [EGNAT](https://users.dcc.uchile.cl/~gnavarro/ps/is11.pdf) | Expensive reconstruction when a metric center is deleted | Old memberships/ranges survive center replacement, with conservative tolerance | Full bucket expands locally; quality-driven tolerance rebuild suggested | Historical identity, not unchanged current geometry; no GTS churn metric | Different radial/physical mechanism and same-contract benefit; not a GPU translation of ghost hyperplanes |
| [dsa-tree combined deletion](https://users.dcc.uchile.cl/~gnavarro/ps/sccc03.pdf) | Sustainable exact metric deletion with controlled search cost | Timestamped history and fake-node topology between repairs | Fake-node fraction exceeds alpha | Explicit deferred repair is evaluated; repair may affect younger siblings/ancestors | Independent mechanism beyond tombstones, historical pruning and thresholded reconstruction |
| [Dynamic VP-tree](https://link.springer.com/content/pdf/10.1007/PL00010672.pdf) | Parent partition changes propagate down a radial tree | VPs/intervals until overflow/underflow | Occupancy-based redistribution, split/merge, root event | Directly names possible global reorganization; some structural events still rebuild subtrees | Decisive difference beyond retaining VPs during ordinary updates or switching overflow policies |
| [ikd-Tree](https://arxiv.org/pdf/2102.10808) | Whole rebuild is wasteful for small incoming point frames | Existing coordinate splitters, lazy-delete state | Balance and invalid-node criteria | Partial rebuild, no radial-pivot churn guarantee; coordinate-space only | Exact arbitrary-metric/GPU coupling with a non-incremental mechanism and charged quality cost |
| [Pkd-tree](https://pal.cs.ucr.edu/papers/2025/SIGMOD25/pkdtree.pdf) | Efficient parallel batch dynamic kd-tree maintenance | Existing splitters outside reconstructed subtrees | Relaxed weight balance | Single-tree selective reconstruction plus measured balance/query tradeoff | Not merely parallelizing a known partial-rebuild policy; distinguish batch/cache methods too |

## Why the other families do not rescue the candidate

SIHC gives a particularly explicit small-update/large-hierarchy-change motivation,
but it is insertion-only clustering rather than exact dynamic metric retrieval.
It weakens a broad "stability is a new objective" claim, not a same-setting
KILL-1 by itself. PM-tree fixes global filter pivots for an index lifetime, which
is different from GTS local child-membership decisions. BDL-tree retains static
components until carry/underfill rebuild but does not protect identity across
that reconstruction. These distinctions are genuine; none creates an independent
new mechanism for the current three-step recipe.

## What is not established

No prior control was executed, ported, or compared to current P/P2 in this task.
There is no evidence here that a literal port meets the leaf-churn, verification
or maintenance-work gates. Differences in geometry, deletion contracts, physical
packing, query fanout and repair scope remain real implementation costs. They
must motivate a specific new mechanism, not be used as generic novelty language.
