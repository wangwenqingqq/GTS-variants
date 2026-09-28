# Million-point traversal candidate: partial result

The previous complete-query profile on GIST/Deep at N=1,000,000 attributes
86.7%/84.2% of **query GPU kernel duration** to `findNextRnn`, which launches
only one 512-thread CTA. The isolated candidate keeps the original L2 distance
expression, pruning predicate, tree, result fusion, CUDA Graph and output
transfer. S specializes the metric but retains one CTA. P distributes children
across `ceil(node_num/512)` CTAs. The compiler reports a 47,528-byte/thread
stack for the original generic traversal and zero for both L2 variants.

On GPU 6, all six S/P normal-radius million-point full-output runs passed an
independent CPU float64 membership/distance check and the native path's exact
ordered float32 output hash. GIST S/P memcheck runs reported zero errors.
The first single-process complete-query means, after the runner's one first
call but with zero additional warmup iterations, were:

| Dataset | S, one CTA | P, multi CTA | S/P exploratory ratio |
|---|---:|---:|---:|
| GIST 1M | 2616.244 ms | 401.922 ms | 6.509× |
| Deep 1M | 278.441 ms | 49.707 ms | 5.602× |
| Tloc 1M | 3.854 ms | 3.539 ms | 1.089× |

These are **screening observations**, not accepted speedups: each arm has one
process, no additional warmups, and no same-campaign original E denominator. The frozen
63-run program requires full output, sanitizer, four paired E/S/P rounds and
traces. It stopped before timing when a foreign job entered GPU 6; no affected
sample is included. A GPU-0 restart was blocked by an existing lock-file
permission issue before any run. All eight GPUs were then occupied, so the
formal timing and remaining correctness gates are pending. The interrupted
raw records are retained under ignored `local/interrupted_gpu6/`; their hashes
and local re-audit are in [PARTIAL_EVIDENCE.json](PARTIAL_EVIDENCE.json).

The candidate changes an L2-only batch-one experimental driver. It has not
been promoted to the original GTS code or to non-L2, batch, update or kNN paths.
