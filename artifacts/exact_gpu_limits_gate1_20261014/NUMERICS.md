# Restricted oracle and numerical contract

This is an offline, full-population diagnostic, not an implemented search.
The authority is the existing original-coordinate, sequential FP64 squared-L2
score. Every newly computed full score must match its complete reference bit
for bit. FP32 inputs are promoted before subtraction; product and addition are
separate FP64 operations under round-to-nearest, without contraction,
reassociation or fast math. Inclusive hits satisfy score <= T. A rejection
requires a strict inequality. Each true hit is charged all 960 coordinates.

## Oracle scope

The pair oracle sorts the 960 rounded nonnegative squared contributions for
each pair in descending order. The query-global oracle first accumulates each
dimension's contribution over **all reference nonhits**, in original row order,
divides by the nonhit count, and sorts those means descending, breaking ties
by ascending dimension ID. It then applies that single order to all objects.
This order is fitted and evaluated on the same population intentionally:
it is an optimistic diagnostic, not a learned policy or held-out estimator.

These are free-construction references within the nonnegative-coordinate
partial-sum rejection family. They are not information-theoretic, arbitrary
index, arbitrary representation, memory-traffic, or dynamic-search lower
bounds. In particular, computing the contributions, their orders, the full
authority scores, and nonhit identities is free only in the model. A fixed
query order is not claimed optimal among all fixed orders. Reordered rounded
addition is not claimed to reproduce the authority score or an exact-real
minimal certificate. The measured statistic is the declared first crossing.

## Guarded cross-order certificate

Let the same rounded nonnegative contributions be c_j, u=2^-53, and
gamma_D=D*u/(1-D*u). Standard nonnegative sequential-sum error bounds give
F_original >= (1-gamma_D) sum_j c_j and
S_reordered,k <= (1+gamma_D) sum_selected c_j.
Consequently S_reordered,k > T*(1+gamma_D)/(1-gamma_D) certifies
F_original > T. The guard is computed from the exact rational
T/(1-2*D*u), rounded upward, with one additional nextafter toward +infinity.
This also covers the rounding of guard construction.

All finite FP32 differences squared fit normal FP64 range (or equal zero),
and the sum of at most 960 terms cannot overflow FP64. The build requires IEEE
binary32/binary64 and FE_TONEAREST. Inputs and outputs must be finite.
Every guarded crossing on an authority hit is a hard failure. A nonhit not
crossing the guard is charged D as an explicit full-authority fallback.

The ordinary reordered threshold and guarded threshold are recorded separately.
Primary gates use the planned ordinary oracle, with the guarded result as a
mandatory decision-stability check; disagreement between their gate labels
stops as UNCLASSIFIED. Raw arrays, histograms, guard-related changes, and
nonhits needing full fallback are retained, even if the aggregate is unchanged.

## Denominators

- Primary B1 denominator: original-order per-coordinate first crossing,
  mean 167.29161475 dimensions/object over 32,000,000 pairs.
- Secondary implementation denominator: the 128/256/512/960 checkpoint
  payload, 1,014,828,776 source B/query, equivalent to 253.707194 dimensions.
- Neither dimension count is actual DRAM traffic. Coordinate bytes omit
  query/state/output/sector/cache/control traffic. Reordered noncontiguous
  coordinates are not assumed to achieve four transferred bytes each.

All integer gates use exact cross multiplication; statistics weight each
query-object occurrence equally. Quantiles interpolate the full integer
histogram at rank (n-1)*p. No sample confidence interval is appropriate for
this fixed population. No GPU timing, update, output, or SLA is measured here.
