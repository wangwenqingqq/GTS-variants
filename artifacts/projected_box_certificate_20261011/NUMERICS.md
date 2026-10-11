# Safe represented-PCA projected box

Coordinates are finite FP32, converted exactly to FP64. Stored directions U
are finite FP64, D-by-4, |U_ij| <= 1. D <= 4096. Projection uses the **uncentered**
linear map x -> U^T x; centering is only for PCA training. A common translation
would not alter query-to-box separation. Directions are frozen from initial
only and reused for first_rebuilt. Rounded PCA quality affects strength, not
correctness of the certificate.

## 1. Enclosing projection dots

For one direction, compute t_hat by dimension-ascending FP64 multiplication
and summation, with no reassociation or FMA contraction. Let m=max_i|x_i|
(exact FP32 maximum) and a_j=max_i|U_ij| (exact FP64 maximum). The sum of real
absolute products is <= D*m*a_j. Compute B_j by upward rounding each of the
two multiplications. With u=2^-53, the usual dot error gamma_(2D) times the
absolute-product sum is less than e*B_j for e=(4D+16)*2^-52. Use this loose
power-of-two-representable e and round e*B_j upward. To cover gradual underflow,
add upward-rounded (2D+1)*eta, eta=2^-1074, covering product and addition absolute
rounding errors. Our admitted magnitudes cannot overflow FP64: FP32 m, bounded
U and D give products/sums below approximately 2^141. Unsafe rounding modes,
FTZ/DAZ or fast math are not admitted.

Then E=up(up(e*B_j)+up((2D+1)*eta)), and
[down(t_hat-E), up(t_hat+E)] contains the real represented-direction dot.
The extra infinity-norm reduction is charged once per query, in addition to
four dot reductions. It is not silently treated as free preprocessing.

## 2. Block boxes and query lower distance

L_j=min of all member lower endpoints, H_j=max of all member upper endpoints.
Thus the box contains every real projected member. Let [ql_j,qh_j] contain
the real query projection. A safe separation component is
max(0, down(L_j-qh_j), down(ql_j-H_j)). Square each component downward,
clamp to zero, and add four components with downward rounding after every add.
The resulting LB2_lower is <= squared distance between the query interval and
box, hence <= every real query/member represented projected squared distance.
Equality, endpoints and zero gaps are retained. This envelope can only weaken
pruning; it cannot invent a strictly positive lower separation at a boundary.

## 3. Do not assume floating directions are exactly orthonormal

Compute the real Gram matrix G=U^T U **exactly as rational sums of stored FP64
values**, using Fraction.from_float for all products. For symmetric G,
||U^T||_2^2=lambda_max(G)<=max_j sum_k |G_jk|. Round that rational maximum
upward to the smallest enclosing FP64 value A2. Near-identity Gram and eigen
residual are PCA qualification gates, not replacements for this safety bound.
For every v, ||U^T v||^2 <= A2 ||v||^2. Thus LB2_lower/A2 is a valid full-L2
squared lower bound even when rounded directions are not exact contractions.
The proof publishes exact Gram rationals and bound rationals.

## 4. Ordered-reference membership

Membership remains the prior ordered-FP64 full-D squared score <= r*r, where
r is the same FP32 radius. The prior distance envelope e ensures every reference
hit has real squared L2 <= r2_upper=up((r*r)/(1-e)). The FP32 product r*r is
exact in FP64 (48 significand bits), including extreme/zero FP32 radii. Form
threshold=up(A2*r2_upper) and reject **only** LB2_lower > threshold.
This implies no reference hit can be rejected; equality retains the block.
See the [prior distance derivation](../block_certificate_headroom_20261010/NUMERICS.md).

## 5. Independent numerical gates

Boundary tests use exact rational/Decimal dots, represented Gram and real
query/member squared distances. They cover all twelve requested categories,
including cancellation, FP32 subnormals/extremes, exact box/radius equality,
nextafter separation, duplicates, constant/final-partial blocks, and bad inputs.
Main projection computes four independent accumulators across each dimension
(vectorizable across directions); a separately compiled O0 verifier loops one
direction at a time left-to-right and reconstructs all object/query projections.
It independently reduces per-block intervals, evaluates scalar lower distances,
and builds an object-owner oracle. Shared envelope helpers are additionally
checked against high-precision arithmetic, not described as independent proofs.
No CUDA numerical, sanitizer or end-to-end gate is implied.
