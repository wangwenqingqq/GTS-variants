# Gate0: engineering attribution, not a new packing thesis

Checked before implementation on2026-10-11. The nearest baseline is the
[original GTS source](https://github.com/ZJU-DAILY/GTS/tree/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639)
and [GTS paper](https://arxiv.org/abs/2404.00966). Our audit targets its concrete
one-CTA-per-leaf verifier, not a claim that every GPU tree has the same problem.

Generic SIMT work assignment and tree divergence are established. NVIDIA's
[tree traversal analysis](https://developer.nvidia.com/blog/thinking-parallel-part-ii-tree-traversal-gpu/)
discusses packet traversal and work assignment, while
[Aila and Laine's traversal-efficiency study](https://research.nvidia.com/sites/default/files/pubs/2009-08_Understanding-the-Efficiency/aila2009hpg_paper.pdf)
studies SIMT execution efficiency and scheduling in tree traversal. These are
nearby mechanisms, not exact-GTS performance comparators. Neither establishes
the gain for this frozen task, and neither justifies calling fixed3 novel.

Decision: reject generic multi-leaf packing as a standalone novelty thesis;
permit the explicitly requested bounded engineering experiment to distinguish
CTA shrink from packing. Do not rescue a subsumed thesis with a modest gain,
extra packaging or broader implementation. Any later paper contribution needs
a separately defensible mechanism and strong external same-contract evidence.
