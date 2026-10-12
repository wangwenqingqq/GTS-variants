# Numerical safety contract

This is a CPU-only offline experiment. Empirical zero violations are necessary,
but do not replace the following enclosing-set and arithmetic arguments.

## Inherited projection and score

The stored PCA8 matrix is unchanged. Its exact-rational Gram infinity norm is at
most one; the spectral norm is therefore at most one. On the inherited FP32
input domain [0,2]^960, each ordered projected coordinate has error less than
ETA=1e-8. Recheck the matrix certificate and inherited error formulas at build.
Original scores are the unchanged ascending-dimension RN-FP64 squared L2, with
separate multiply/add and no FMA. The inherited distance error bound is less
than RHO=1e-4. All shapes compare strictly `LB > sqrt(U_star_squared)`; full
false-prune validation also uses the original squared-score relation, not only
the rounded square root. All bounds have RHO subtracted conservatively.

## Stored-center balls and diagonal ellipsoid

Center construction folds points in ascending object-ID order. The final center
is rounded to FP32, then every radius/scale/factor is recomputed against that
stored center; no prequantization radius is reused. For each coordinate form an
upper enclosure of `abs(cached_z-stored_center)+ETA`, rounding upward after
subtraction/absolute-value enclosure and addition. Ordered squared terms,
addition, square root, and positive division also round upward operation-wise.
The maximum enclosing radius is rounded to FP32 toward +infinity. Hence each
ball contains the full coordinate-error box of every original projected point.

The diagonal scales are FP32-upward maxima of these deviations. Even a dimension
with identical cached coordinates has strictly positive scale because ETA is
positive; this avoids an unproved exact-coordinate constraint. The factor is a
full maximum of the upward norm of deviations divided by the stored scales,
again FP32-upward. Every true projected point therefore satisfies
`sum_j ((Px_j-c_j)/s_j)^2 <= R^2`. Validate the stronger coordinate-box enclosure
on every object at all three levels. There are 3M object memberships per shape.

The minimax center is only a fixed 64-step farthest-point heuristic. Region IDs
are sorted, making argmax ties choose the lowest object ID. Keep the first
smallest full maximum ordered squared radius among the initial centroid and
all 64 iterates, then apply the same stored-center enclosing-radius procedure.
Its safety does not require an optimal center. Record a witnessed cached RN
half-diameter only as a numerical quality proxy, NOT a certified optimal-radius
lower bound or approximation ratio. No optimality or whole-ball-family kill is
claimed from this approximation.

## Query lower bounds

Each true query projection lies within Euclidean distance
`e = upward(sqrt(8)*ETA)` of its cached query vector. Distance to any closed set
is 1-Lipschitz. Balls use a downward norm of the absolute query/center difference,
then subtract stored radius, e, and RHO downward, clipping at zero after each
step. The unchanged keeper AABB retains its per-coordinate interval arithmetic.

For `E={y: sum_j y_j^2/s_j^2 <= R^2}`, write `d=q_cache-c`. For ANY finite
nonnegative lambda the Lagrange dual gives

```
dist(d,E)^2 >= sum_j lambda*d_j^2/(s_j^2+lambda) - lambda*R^2.
```

The right side follows by minimizing
`||d-y||^2 + lambda*(sum_j y_j^2/s_j^2-R^2)` over unrestricted y. No assumption
about solver convergence is needed. The fixed 64-bisection solver only chooses
lambda; an approximate or suboptimal lambda cannot make the dual unsafe.
Evaluate the dual with lower squared absolute differences, lower products,
upper positive denominators, lower quotients and ordered sums, and upper penalty.
Clip its lower enclosure at zero, sqrt downward, subtract e and RHO downward.
All elementary operations are separate FP64 ufuncs, never dot products or FMA.
The scalar reference uses explicit Python additions (not Python 3.12 compensated
`sum` for float folds). Synthetic tests additionally compare against an exact
rational dual, including zero spread, repeated points, ties and cancellation.

## Full and independent gates

- G1: all object memberships satisfy stored-shape upper enclosure.
- G2/G3: all 3,552,000 candidate/query/region bounds compared with own original
  region truth; no false strict top-K prune; own-region truth is recomputed from
  the pinned original score cache, not substituted with projected truth.
- G4: all 24 original PCA8 query/level counts and truth denominators identical;
  full stored AABB endpoints identical too.
- G5: 128 query/region pairs at EACH level, 384 total, selected before outcomes.
  Independently reproject every original vector in these regions, rebuild all
  stored shape parameters, scalar query bounds, and original ordered scores.
  Require exact coordinate, metadata, bound, and original squared-truth equality.
- Serialize and reload all 12 full metadata cells, including actual zero padding
  and 48/64/80-byte record strides. Public source/count replay is separate from
  private full-metadata replay and original-vector recomputation.

## Auxiliary point-set diagnostic

This is NOT query-conditioned index metadata and is NOT a fifth deployed
certificate. It is the nearest point distance in the unchanged PCA8 projection,
enclosed above and below using operation-wise rounding and `2*e` to account for
both point and query projection errors. A set enclosing those true projected
points cannot have distance greater than their nearest-point distance. Its
upper envelope therefore supplies an optimistic geometric ceiling for this
frozen query/partition/projection, and its lower envelope supplies a certified
pointwise diagnostic count after the inherited RHO adjustment. Report both;
never extrapolate to arbitrary projections, nonlinear representations or other
queries. An unsuccessful finite shape family alone does not prove that PCA8 is
information-limited.
