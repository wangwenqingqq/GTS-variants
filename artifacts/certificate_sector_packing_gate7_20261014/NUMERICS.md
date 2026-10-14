# Exactness across a coordinate permutation

The oracle is unchanged: FP32 inputs promoted to FP64 before subtraction,
FP64 multiplication, then FP64 additions in original dimension order 0..959,
round-to-nearest, no contraction or reassociation. Membership includes equality.

A mathematical coordinate permutation preserves squared L2. A permutation of
floating-point additions need not preserve the frozen bits. For q=0 and FP32
x=[2^27,1,1,1], original-order FP64 summation is 2^54, whereas the reversed order
is 2^54+4. The fixture retains this counterexample.

The packed candidate has one FP32 database only. The inverse permutation restores
original-order full accumulation directly from that database for the quality
audit. Its partial reads only selected packed coordinates, also accumulating in
original dimension order. Sector moment sums are ranking scores, never grouped
distance certificates. A nonnegative subset accumulated in the same order is
bounded by the frozen full sum; every population pair is checked anyway.

The full audit is not a deployed fallback: it deliberately reads 960 dimensions
per pair. The candidate subset reads 128 distinct coordinates. The reported
512M+3328*survivors source-byte model assumes the selected FP32 coordinates are
retained and later merged with unseen coordinates in the original order, without
source rereads. Mapping, retention, recomputation, register/shared/spill and
layout-conversion costs remain UNKNOWN, not zero. It is neither a measured GPU
transaction count nor a complete-search traffic bound or speedup claim.
