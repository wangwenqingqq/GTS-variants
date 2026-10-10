# Conservative certificate numerics

This CPU diagnostic uses the same ordered FP64 squared-distance membership as
its retained exhaustive reference, but its block bounds enclose the *real* L2
metric, to which triangle inequality applies. A rounded score is not itself a
metric. No ordinary rounded square root is treated as an exact certificate.

For finite FP32 coordinates and D<=4096, nonzero differences and squares are
normal in FP64, and no sum can overflow FP64. With round-to-nearest, no FMA or
reassociation, each squared term has at most three rounding factors and the
ordered sum at most D. Thus, for real squared distance S and computed s,
`(1-u)^(D+3)*S <= s <= (1+u)^(D+3)*S`, where `u=2^-53`.
The deliberately wider `e=(4*D+16)*2^-52` strictly exceeds both deviations for
this dimension range. Its representation and `1+e`, `1-e` are exact dyadic FP64
values. Zero distance is exact. For all admitted finite FP32 inputs,
`S in [s/(1+e), s/(1-e)]`. One nextafter toward the appropriate infinity after
each rounded division and hardware square root encloses the real norm.
The lower endpoint is clamped to zero.

A reference hit obeys `s(q,x)<=r*r`; hence its real distance is at most
`sqrt(r*r/(1-e))`, rounded outward. The FP32 radius's square is exact in FP64.
We reject a block only when `q_lo > nextup(block_hi+r_upper)` or
`block_lo > nextup(q_hi+r_upper)`. Therefore, real triangle inequality proves
that no ordered-reference hit can be rejected. Strict inequalities retain
boundary ties. This is a conservative numerical envelope, not a tighter-bound
innovation or a change to the membership contract.

Tests cover exact Decimal norms (including extreme/subnormal FP32, cancellation,
duplicates and nextafter boundaries), reject NaN/infinity/malformed payloads,
and check every actual query-pivot score bitwise against the retained ordered
exhaustive scores. Every queried block is compared with oracle hit membership;
zero false prune is mandatory. These are offline correctness gates, not CUDA
sanitizer or runtime performance gates.
