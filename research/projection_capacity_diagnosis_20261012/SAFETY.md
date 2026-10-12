# Arithmetic and scope safety

## Stored full matrix

Covariance uses all1M FP32 rows converted exactly to FP64, centered with the same
8192-row procedure as the previous fit; a single full eigh orders960 directions.
A sign convention fixes the largest-absolute coordinate positive. Every prefix
uses the SAME stored full matrix and one common contraction scalar.

For each original coordinate d, separately form signed outer products P[:,d]
P[:,d]^T. Nextafter toward minus/plus infinity encloses each multiplication and
each signed accumulation. Only AFTER complete cancellation-aware Gram intervals
are formed do we take elementwise absolute upper bounds and upward row sums.
Gershgorin bounds ||PP^T||_2 by this infinity norm. Scale and then recertify the
actually rounded stored matrix: require upper<=1. Exact-rational synthetic tests
check the interval primitive. Identity-defect infinity norm gives a certified
full-space singular-value lower bound sqrt(1-defect). Full960 is near-isometric,
not bit-identical to the original ordered score path.

## Projected coordinates and common nested envelope

Each row of a contractive matrix has L2 norm<=1 and L1 norm<=sqrt960. On the
verified [0,2]^960 domain, FP64 BLAS dot error is bounded by gamma(2D+8)*2sqrtD,
well below ETA=1e-8, regardless of normal reduction order or FMA. Original FP32
conversions are exact. Require every nonzero stored coefficient>=2^-100: its
FP64 dyadic quantum is at least2^-152, and FP32 inputs have quantum>=2^-149.
Products, ordered/BLAS sums and their differences have quantum>=2^-301; nonzero
squared differences are therefore>=2^-602, safely normal FP64. Zero terms remain
zero. This excludes FP64 dot/distance underflow/FTZ dependencies; the original
FP32 score path is normal for the same reason. Independent ordered projections are NOT required to be
bit-identical to BLAS, only within their proved coordinate error envelopes.

The true projected difference norm is at most 2sqrt960. Cached endpoint errors
add at most E=upward(2sqrt960*ETA). RN subtraction errors add less than1e-12 in
norm. Nonnegative product/sequential-prefix accumulation error is bounded by
gamma(2D+8)*(2sqrtD+E+1e-12)^2. The sqrt inequality and sqrt rounding put projected
arithmetic norm error below3e-5; the inherited original ordered-score norm error
is below5e-5. Both together are below RHO=1e-4. Constants and rational inequality
checks are executable in arithmetic_proof(); tiny IEEE underflow contributions
are far below the reserved slack (no overflow in this domain).

For each cached nearest-point norm d, use lower=max(0,down(d-E-RHO)) and
upper=up(d+E+RHO), with one common margin at ALL k. Each true projected point norm
lies in the envelope; minima preserve intervals. The lower is also <=original
RN score-derived region distance. Strict lower>sqrt(U_sq) is independently
checked against the ORIGINAL squared truth relation for zero false prunes.

Nonnegative sequential cumsum cannot decrease; sqrt/minimum/constant subtraction
and clipping are monotone. Therefore all point and region distances, lower/upper
envelopes, and strict-prune masks nest across the frozen prefixes. Verify every
region/query/k, fail closed on any violation. No per-k margin/normalization hides
violations. Safe and possible counts remain distinct; possible masks are capped
by original truth-prunable regions for an upper alignment<=1. Raw central masks
are only diagnostic and never drive admission.

## Independent and historical bridges

Use24 query-region pairs selected from preceding preregistered samples before
measurement: one pair per query x level, all members, all eight prefixes. Rebuild
full960 coordinates using separate ordered multiply/add on original vectors,
then separately implemented prefix distances/scalar envelopes and original scores. Require exact original truth and
all192 lower/upper classification agreements; require coordinate/prefix-distance
errors within the proved envelopes. Report24 pairs /192prefix-cell checks, not
192 independent regions. Keep original vectors/projected caches private.

The unchanged original P2 truth/U are fully bridged. Historical PCA8 construction
similarity and original preceding point-set counts are reported separately; full
PCA rebuilding is not required to reproduce historical bytes. Full960 original
classification differences, missing guaranteed regions and distance differences
are explicit. Original truth remains the100% opportunity endpoint by definition.

## Claim limits

Only this data/partition/eight queries/U*/basis/grid are covered. Thresholds mean
first measured grid point, not an untested minimal dimension. Distance-loss sums
use signed RN-FP64 aggregates without clipping; envelope-based sums are descriptive
aggregations, not certified summation intervals. No GPU, query cost, compressible
metadata, alternative-direction superiority or universal intrinsic-dimension
statement follows from the protocol decision labels.
