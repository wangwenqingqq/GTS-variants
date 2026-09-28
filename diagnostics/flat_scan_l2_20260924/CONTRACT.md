# Exact scan when the high-dimensional tree barely prunes

For GIST and Deep at N=1,000,000, retain the same constructed tree, its
`id_list` permutation, fixed workspaces, result delivery, deletion mapping,
CUDA Graph, radius, query IDs and float32 L2 arithmetic. Q is the generic-leaf
tree path; J is the validated early-reject tree path; F bypasses traversal and
leaf-node scheduling by scanning all records in `id_list` order with the same
32-coordinate early-reject predicate as J. F compacts hits in that order, so
complete native ordered float32 output must be identical to J and Q. Index
construction remains outside the hot-query timer in every arm; any possible
index-build saving from a production planner is not part of this comparison.

First run all three complete normal-radius outputs, validate against the
CPU-checked native ordered hash, and compare entire output files. Check F at
zero, all-hit and negative radii and run memcheck/synccheck on F. If the
single-process J/F pilot is promising, execute four paired Q/J/F rounds with
eight warmups and eight measured queries per process, alternating QJF, FJQ,
JFQ, QFJ and reversing dataset order on odd rounds. Use the same idle physical
GPU and one compiled binary, refuse foreign GPU activity, and retain any
failed attempt. Report complete host-ready query time, not kernel-only time.
No production code changes or cross-campaign multiplication are claimed.
