# Target-size qualification design (phase A)

Status: implementation in progress; no target performance evidence.

## Frozen boundary

The base is GTS-variants `0033cb2d1934768411ed1806c6729108f412c1e7`.
The pinned original GTS build/update owner and existing PAR / FULL / BOUND
mechanisms remain in use. A separate overlay preserves historical sources and
results. Required shapes are D128 regression and GIST N1M/D960/B1/K8 only.
A is staged original GTS with common numeric and safety repairs, not untouched
native GTS. B adds PAR; C changes FULL to BOUND. No WARP/FUSED routing is added.

## Capacity and ownership

Preflight replays events to determine the maximum physical base plus insertion
buffer. Capacity is rounded to 32 once; an unexpected growth rejects the run.
The native update loop owns compaction, tombstones, buffer, and rebuilds. kNN
owns only its mirror and two recursive Top-K scratch buffers, each
ceil(capacity/256)*allocated_K. All allocation products use checked size_t
arithmetic. The original fixed tree height is raised to the minimum height
whose largest leaf is at most MAX_SIZE; old small defaults remain.

Host answers grow on demand under a fixed 1 GiB combined ID/field budget.
Every field is retained and copied before ACK. Budget exhaustion rejects the
whole trace, never truncates it. File writing follows timing. Long traces are
not admitted until their actual output budget / equal consumption is qualified.
Host vector growth/copy costs are inside the event trace.

## Numeric design and ready graph

Input is finite original FP32. Object verification uses the existing ordered
FP64 RN subtraction, multiplication and dimension-ordered addition, no FMA.
Membership compares squared sums, not rounded FP32 square roots.
The output conversion is RN sqrt followed by RN conversion to FP32.

The fixed historical strict_l2.cuh has the compatible ordered reference
function and member-refit pattern, but its hardcoded outward padding is not
carried into the new bounds. Directed FP64 subtraction, squaring, accumulation
and sqrt enclose the true norm of every actual node member. For finite FP32
operands all nonzero intermediates are normal finite FP64. With u=2^-53,
reference_sum >= true_squared_distance*(1-u)^(D+3). A downward-rounded product
alpha <= (1-u)^(D+3) therefore gives a conservative allowed true radius
sqrt_up(cutoff_RN/alpha). Directed upper additions implement exclusion;
uncertain nodes survive. No fitted epsilon is used.

Each refit CTA owns one node, with 256 member lanes and two shared reductions.
The base/order remain read-only. Refit completion -> publish bounds/base epoch
-> PAR plan refresh when required -> kNN repack -> ACK. Query launch checks
base pointer, dimensions, physical size, and epoch. Deleted pivot rows are not
removed until actual rebuild. All lanes participate in refit reduction barriers;
there is no asynchronous handoff or tensor-core path.

Persistent live sets: common lower/upper arrays (16*node_count bytes); PAR-only
plan and query workspace; kNN FP32 AoSoA32 mirror, double scores/cutoff, live
rank/mask arrays, two Neighbor buffers and K outputs. Rebuild temporarily owns
old/new data and tree state; paid copies/refit/repack remain inside ACK.

## Gate / reject rules

CPU exhaustive small-output comparison and A/B/C ordered equality precede
bounded sanitizer runs. Then N65536 transition and N1M real rebuild smoke,
with independent chunked reference and boundary cross-checks. Missing numeric,
coverage, lifecycle or capacity proof blocks the 18-process campaign. No
compilation or narrow smoke test is described as target qualification, speedup,
default selection, or novelty.
