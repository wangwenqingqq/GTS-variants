# Admission: CPU opportunity test only, no novelty promotion

Shared-query execution is established. [QPipe, SIGMOD 2005](https://www.pdl.cmu.edu/PDL-FTP/Database/qpipe.pdf)
shares operators across consumers. [SharedDB, PVLDB 2012](https://arxiv.org/pdf/1203.0056)
uses global plans and query membership. [Dual-tree algorithms, ICML 2013](https://proceedings.mlr.press/v28/curtin13.html)
organize both query and reference sets with branch-and-bound pruning.
[Hitcher, KDD 2026](https://scholars.cityu.edu.hk/en/publications/hitcher-efficient-gpu-based-vector-search-via-cluster-centric-ker/)
documents cluster-centric GPU cross-query data reuse and hitch-ride ordering.
The latter mechanism is confirmed from its author-institution abstract, not a
verified implementation of our exact arithmetic and dynamic split contract.

These precedents block novelty claims based merely on a DAG, query bitmask,
access compatibility, shared scans or plan caching. They do not establish that
the complete proposed certificate/splitting problem is subsumed. Missing direct
coverage is uncertainty, not proof of novelty.

The user authorized a bounded fixed-batch CPU falsification. We test whether a
strong simple shared-access schedule already approaches a finite oracle. The
oracle is optimal only within fixed per-query PDX zone chains and one tile
buffer; it is not an information lower bound for arbitrary search algorithms.
No recipe index, learned signature, CUDA implementation, service benchmark or
manuscript change is admitted by this test.

All batches already exist at one immutable snapshot. This differs from the
previous frozen Poisson/500us arrival test, which remains closed on its original
scope. Offline batches neither disprove that negative nor establish an SLA.

Primary source pages were rechecked on 2026-10-19. No third-party code or paper
text is redistributed here; the inherited PDX mechanism and trace identities
remain in the parent artifact.
