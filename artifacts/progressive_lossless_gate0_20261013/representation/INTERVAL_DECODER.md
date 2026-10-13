# Exact intervals and safe numerical rejection

At cumulative b in {4,8,16}, prefix p denotes integer key window
`[p << (32-b), ((p+1) << (32-b))-1]`, using wide arithmetic at the upper endpoint.
Intersect that window with all finite keys, then inverse-map its two endpoints.
The endpoints are actual FP32 values, exactly representable in FP64. An empty
finite intersection is invalid for the admitted service; no dataset values are
excluded by narrowing to observed minima/maxima. At 32 bits the value is exact.

Project the full FP32 query coordinate onto [lo,hi]. The real squared gap is a
lower bound on the original squared gap. To remain below both exact-real distance
and the frozen ordered FP64 oracle, round one ULP toward zero after the positive
gap subtraction, after its square, and after each nonnegative ordered sum.
Zero stays zero. Max with the preceding safe stage bound ensures monotonicity.
The one-ULP helper operates on a positive finite double's bits, with IEEE formats
and FE_TONEAREST checked; no fast-math, reassociation or FMA contraction is allowed.
Finite FP32 extremes' differences/squares/960-term sums cannot overflow FP64;
FP32 subnormal squares do not underflow FP64. Monotonic rounded arithmetic also
places the safe accumulation below the original-coordinate ordered oracle.

Reject only LB>cutoff. Equality proceeds. Complete reconstruction is followed by
ordered FP64 difference, multiplication, addition in dimensions 0..959 and exact
bit comparison with the frozen oracle. No empirical tolerance is used to forgive
false rejection or final-distance mismatches. This is CPU numerical qualification,
not CUDA exactness, sanitizer success, or measured DRAM proof.
