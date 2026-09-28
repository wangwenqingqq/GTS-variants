# L2 leaf early rejection after traversal/count fixes

At N=1,000,000 the normal-radius GIST and Deep queries retain approximately
92–99% of leaf nodes as candidates. The original leaf kernel computes the
full 960/96-dimensional L2 distance for every candidate even though the CPU
oracle shows most points miss the radius. This screen keeps fixed batch-one
Q traversal, dead-count removal, result selection, Graph, tree, output order
and transfer. Q is the original generic leaf, H is the same one-thread-per-
point full-sum L2-specialized leaf, and J adds a conservative early rejection
check every 32 dimensions. All hit distances preserve the original coordinate
order and final sqrt. J never emits a truncated distance; it only drops a
candidate whose partial nonnegative sum exceeds `(r+0.001f)^2` for the fixed
positive normal radii. This margin is far above float32 rounding scale here;
full CPU/original-order checks remain mandatory for every mode and boundary.

The pre-run CPU sample of 4096 deterministic record IDs per query predicts
mean processed fractions of approximately 0.60 for GIST and 0.63 for Deep,
but it is a hypothesis, not a GPU timing result. Q/H isolates metric
specialization; H/J isolates early rejection. Compare complete hot batch-one
query time on the same idle physical GPU with at least four paired process
rounds, alternating QHJ/JHQ/HJQ/QJH order after full-output and sanitizer
gates. Preserve all unfavorable observations. No production path changes,
new paper novelty, or cross-campaign speedup multiplication are claimed.
