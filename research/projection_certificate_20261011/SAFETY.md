# Exact-safe bridge for the stored projection

## Construction

Treat every saved FP64 coefficient as an exact dyadic rational. Compute the full
8-by-8 Gram matrix P P^T using Python Fraction arithmetic, including coefficient
rounding after a common scale. Require max_i sum_j |Gram_ij| <= 1 exactly. The
Gram matrix is symmetric positive semidefinite, so its spectral radius is no
larger than its infinity norm; hence ||P||_2 <= 1. Every prefix remains
contractive. Approximate PCA/QR orthogonality is not the safety premise.

Covariance construction may use the installed BLAS arithmetic: it chooses the
basis only, not the score contract. Full N=1,000,000 database rows are used in two
fixed-order passes, never query labels, thresholds or visited masks. Both
families are certified after canonical sign and common (1-2^-40) shrinkage.

## Ordered projection and signed endpoints

The input domain is checked finite FP32 in [0,2]. A row norm at most one gives
sum_i |p_i x_i| <= 2 sqrt(960). Ascending-coordinate FP64 multiplication then
addition with FMA disabled has absolute error no larger than
 gamma_(4*960+8) * 2 sqrt(960), below the predeclared ETA=1e-8.
This is an analytic bound, not a tolerance fitted to observed residuals.

For nonzero coefficients, |p_i| >= 2^-100 is checked. Their FP64 dyadic grid is
at least 2^-152, and FP32 coordinates have grid 2^-149 or coarser. Products and
nonzero cancellations therefore cannot underflow FP64; FTZ and DAZ are disabled.
The deliberately loose gamma budget covers each multiply/add. RN is explicitly
selected by the ordered CPU projector. The independent implementation performs
separate NumPy multiply and add, never BLAS dot. It checks every object in every
frozen bridge region and the eight query rows.

Use lo=FP32_floor(nextdown(min(zhat)-ETA)) and
hi=FP32_ceil(nextup(max(zhat)+ETA)); round32 checks conversion direction.
Coordinates can be negative: no clipping of lower endpoints or query intervals.
At query time [nextdown(qhat-ETA),nextup(qhat+ETA)] contains the real Pq.

## Joint lower bound and original score

Each gap is max(0,nextdown(lo-qhi),nextdown(qlo-hi)). Its square is rounded down.
Accumulate S_j=max(S_(j-1),max(0,nextdown(S_(j-1)+square_j))). Both choices are
lower bounds on the new exact nonnegative prefix sum, so this also preserves
nesting when adding zero or a tiny square. Lower-round sqrt(S). The resulting
bound is no larger than the real distance from Pq to the stored box, and the box
contains every exact Px in the region. Contraction then bounds real original L2.

The inherited original RN-FP64 squared-L2 contract has distance error at most
sqrt(gamma_(4D+8)*4D) + 2*u*sqrt(4D), below RHO=1e-4. Subtract RHO with directed
down rounding and clip at zero. The final bound is therefore <= the inherited
RN-FP64 region-truth distance, not just the real metric. This envelope also
covers the final RN sqrt. Compare strictly > the unchanged RN sqrt(U*_squared).
The inherited squared/sqrt classification bridge and full-path native bound
remain unchanged; max(native, projection) combines two safe bounds.

A 128-pair independent all-object screen must PASS before pruning curves. Stage B
also checks every region/query/prefix bound <= its frozen truth, zero top-K
region false prunes, identical C0 counts and monotone nested bounds. These checks
complement the derivation; finite testing alone is not the proof. This is offline
CPU correctness, not CUDA sanitizer success or end-to-end acceleration.
