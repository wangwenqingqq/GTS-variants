# Frozen numerical safety gate

This is an ordered-FP64-compatible inclusive range prototype, not a proof of
real-arithmetic exactness for arbitrary inputs. Admitted vectors and queries are
finite FP32 with absolute coordinate value at most16, D=960, in original order.
Radius is the original FP32 value; cutoff is its promoted FP64 product. No FTZ,
fast math, coordinate permutation, expanded L2 or Tensor Core operation is used.

## Fast estimate and conservative interval

One warp owns one occurrence. Within each fixed128/128/256/448-coordinate
chunk, each lane performs at most14 RN FP32 subtraction/FMA steps, followed by
five RN shuffle-add levels. Lane0 adds the chunk estimate to persistent FP64
state. These FP64 additions do not make the FP32 estimate exact.

Let u=2^-24 and gamma_m=m*u/(1-m*u). A nonnegative exact squared term's path
has at most two subtraction-error factors,14 accumulation roundings and five
tree-add roundings. Gamma_32 is a conservative relative envelope for that path.
Three FP64 continuation additions and the ordered reference's at most960 FP64
subtraction/product/add operations are much smaller. With gradual underflow,
the accumulated FP32 absolute error is below2^-130 for at most960 terms;
FP32 differences are multiples of2^-149 and their FP64 squares are normal.
The bounded input envelope prevents overflow. Replacing an uncertain prefix by
its exact ordered value only reduces this envelope.

For nonnegative stored estimate S, the deliberately looser envelope

    E = round_up(S * 2^-16 + 2^-120)
    L = round_down(S - E)
    U = round_up(S + E)

contains the original ordered-FP64 prefix. Gamma_32/(1-gamma_32), FP64 error
and underflow allowances are strictly below these margins. Directed CUDA
intrinsics keep interval endpoints outward-rounded. Equality is never rejected:
reject only when L>cutoff; retain when U<=cutoff. Otherwise lane0 recomputes the
entire prefix0..K using separate __dsub_rn, __dmul_rn, __dadd_rn, and compares
that exact ordered value. This fallback is charged to the current stage.

The original prefix is monotone, so every safe early reject is a reference
nonhit. Every checkpoint is classified by the same ordered prefix, not merely
by a conservative superset. At K=960, retained hits are recomputed in ordered
FP64 even when the interval already proves membership. Thus final membership
and equality match the oracle. Hit squared scores are rounded to FP32, then
cast to the inherited FP64 observer; Euclidean fields use sqrtf of that FP32
score. Both field-squared and squared-observer errors must pass the original
5e-5*max(1,oracle_score) tolerance. No bit identity to the native FP32 keeper
is promised. Duplicate vectors remain separate original row IDs.

## Proof versus runtime gates

Build with --ftz=false and explicit rounding intrinsics. Inspect generated PTX/
SASS for the fast path and the separate ordered fallback. Synthetic tests cover
zero/duplicate/equality/adjacent representable boundaries, rejection at every
stage, all-hit/empty answers, ragged counts/tails and100 pointer/stream churn
iterations. Bounded and full target qualification compare all40 complete
answers and all four checkpoint IDs to the existing oracle/Gate1 evidence.
Run memcheck/racecheck/synccheck on synthetic and bounded target. Any failure
stops before timing; no tolerance or survivor-count relaxation is allowed.

The interval is not assumed to reproduce floating-point sums by warp reduction.
It proves when the reduction is sufficient and pays for ordered replay when it
is not. Replay reads, CUB scratch, metadata, output and launch/sync costs remain
inside the measured GPU-traffic and Host-ready denominators.
