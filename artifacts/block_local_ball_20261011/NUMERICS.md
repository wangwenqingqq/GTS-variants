# Conservative block-local ball

Membership is the unchanged ordered-FP64 squared-distance comparison
`score(q,x) <= r*r`, with FP32 coordinates and radius. Squared rounded scores
are not assumed to be a metric. The real L2 distance satisfies triangle inequality.

For finite FP32 and `1 <= D <= 4096`, use the prior proven envelope
`e=(4*D+16)*2^-52`. Ordered subtraction, product and dimension-ascending sum,
compiled without fast math or FMA contraction, give real norm bounds via outward
division by `1+e` / `1-e`, outward square root and `nextafter`.
See [the original derivation](../block_certificate_headroom_20261010/NUMERICS.md).
No new precision relaxation or ordinary rounded sqrt is used for rejection.

For every frozen block, choose its one C0 center without query information.
Compute all center/member scores and set `R_B` to the maximum upper endpoint.
Then every real member distance to its center is at most `R_B`.
An ordered-reference hit has real query/member distance at most
`r_upper = outward_sqrt(r*r/(1-e))`. Real triangle inequality therefore implies
`d(q,c_B) <= R_B+r_upper` for every block containing a hit. The query/center
lower endpoint is no larger than the real distance, so reject only if
`qcenter_lower > nextup(R_B+r_upper)`. Equality is retained.

Zero score remains enclosed even when outward rounding makes the upper endpoint
slightly positive. Zero-radius/identical-vector blocks remain safe. The FP32
maximum, subnormals, cancellation, duplicates and adjacent FP32 values stay
within the prior FP64 range proof. NaN/Inf, malformed payloads, invalid row
indices, dimensions, partitions and non-FP32 radii are rejected before evaluation.

The C0 *selection diagnostic* uses ordinary FP64 sqrt of four prior pivot scores.
Its mean is accumulated left-to-right in frozen member order, and squared
signature distances are added in pivot order. Exact score ties use smallest
immutable occurrence ID. This affects which conservative ball is chosen, not
the safety proof; no oracle or query influences that choice.

Qualification tests cover all ten requested boundary categories and decision
gate boundaries. Fresh independent verification recompiles the pair kernel at
O0, checks all 2,000,000 center/member scores and 262,144 query/center scores
bitwise, and compares every query/center value with the retained exhaustive
reference. It reconstructs C0 via scalar accumulation, radii, all oracle/keep
rows and gates. Compilation, CPU correctness and structural counts are separate
from CUDA sanitizer and end-to-end performance gates, which are not run here.
