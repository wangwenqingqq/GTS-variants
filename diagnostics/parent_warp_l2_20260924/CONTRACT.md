# Parent-owned pivot reuse after multi-CTA traversal

At every tree split, the ten children inherit the same `pid` from their
parent. The original child-owned L2 traversal computes query-to-pivot distance
up to ten times for this group. A previous single-CTA parent-reuse variant
reduced logical distance count but lost performance because too few lanes
produced distances and a block-wide barrier serialized publication.

This independent batch-one L2 prototype assigns one warp per parent, eight
warps per CTA and many CTAs per level. Lane zero computes the original scalar
distance in the original coordinate order, broadcasts one float within its
warp, and lanes zero through nine independently test child bounds. No block-
wide barrier, changed arithmetic, tree/layout, candidate/result compaction,
Graph or host delivery is introduced. Q (multi-CTA child-owned) and W (warp-
per-parent) both skip the independently validated dead count stage; Q/W
isolates parent pivot reuse plus the ownership change. Complete ordered
float32 output, CPU oracle, sanitizer and paired end-to-end timing are
required before a performance claim. The first full-output check must verify
that every live sibling group has one pivot ID on the actual million-point
trees, not only in source code. No paper novelty is claimed from this mapping.

Run only on an admitted idle GPU under its advisory lock; stop on foreign
activity and preserve failed attempts. No production path is changed.

The bounded scale screen uses GIST and Deep at N=1,000,000, their existing
eight fixed query IDs and normal radii. On one physical GPU, first run complete
Q/W outputs and CPU oracle/native-order checks; then W memcheck/synccheck.
Only if these pass, run four independent paired rounds QW, WQ, QW, WQ,
reversing dataset order on odd rounds, with eight warmups and eight measured
queries/process. Compare Q/W within each round and report every process mean,
median ratio, 4/4 wins and paired interval. Q and W must share the same new
binary and fixture; prior Q timings are never used as a denominator. NSYS
traces diagnose warp-parent and downstream kernel identities after timing.
