# Premise gate,not a new-index proposal

The classical shared frontier / low-dimensional Euclidean direction is closed.
This precheck does not tune or execute its query-ball/annulus candidate.

1. [SPB-tree,Efficient Metric Indexing for Similarity Search,ICDE2015](https://irc.cs.sdu.edu.cn/973project/result/download/2015/53.EfficientMetric.pdf),
   sections IV-B/IV-D: fixed pivots need not remain database members;object
   insertion/deletion can retain pivots. SFC/B+tree/RAF maintenance updates
   affected entries/bounding boxes. Pivot-distance caching is not new.
2. [AV-tree,PVLDB2023](https://cs.au.dk/~karras/avtree.pdf) and
   [RECAST,arXiv2608.06962v1,2026-08-07](https://arxiv.org/html/2608.06962v1)
   already exploit earlier paid query distances for exact metric pruning.
   They are nearest-art controls for query-adaptive reuse,not measured here.
   Absence of an observed full dynamic evaluation is not a novelty certificate.
3. [Quickjoin,Metric Space Similarity Joins](https://www.cs.umd.edu/~hjs/pubs/jacoxtods08.pdf)
   establishes metric partition joins. Existing own CPU family helpers are reused.
4. [DBSimJoin](https://ysilva.cs.luc.edu/publications/DBSimJoinJournal.pdf)
   already addresses nonblocking complete metric-join operators.
   No output-streaming contribution is proposed by this precheck.

## Why a cheap premise test is permitted before a performance campaign

If x,p and the metric do not change,d(x,p) does not change. Removing other
objects or moving the bytes of x cannot invalidate that value when it is bound
to x's immutable occurrence identity. Inserting y requires its own distances.
A conservative block envelope after deletion may become loose without becoming
unsafe;insertion outside it requires expansion. Replacing pivot contents or
reusing an ID with another generation invalidates dependent values. Those are
different cases and must not be conflated as a global-invalidation cost.

The experiment measures this distinction and query utility,not a new repair
algorithm. Ordinary incremental columns are an adversarial simple control.
They are NOT SPB-tree: no SFC,B+tree or RAF implementation is substituted.
Native SPB-tree and native GTS update ACKs remain missing,so a full5x/10x
strong-baseline performance gate cannot pass in this artifact.

Original GTS source is inspected privately and not redistributed. Its native
update path uses tombstones,an insertion buffer,and reconstruction when that
buffer reaches its threshold. Rebuilding on every CPU snapshot is explicitly
a diagnostic,not a faithful reproduction of native update cost.
