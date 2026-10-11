# Exact-safe interval arithmetic contract

Inputs are finite FP32 in [0,2], D=960; scores use ordered RN binary64
subtraction, multiplication and addition with FMA/reassociation disabled.
The real Euclidean metric is not silently identified with its rounded score.

Let u=2^-53, m=4D+8 and gamma_m=m*u/(1-m*u). With true squared L2 S<=4D,
an intentionally loose forward bound is |S_hat-S|<=gamma_m*4D. This budgets
all subtraction errors (twice when squared), multiplication and ordered sum
errors, with extra slack for evaluation. The smallest nonzero FP32 difference
is at least 2^-149; its square is at least 2^-298, so no nonzero intermediate
underflows in binary64 under this input envelope. Zero terms are exact.
No intermediate overflows: the sum is at most approximately 3840.

Using |sqrt(a)-sqrt(b)|<=sqrt(|a-b|), and adding the RN sqrt error, the frozen
absolute distance-error upper bound is

```text
sqrt(gamma_(4D+8) * 4D) + 2*u*sqrt(4D) < 1e-4 = rho.
```

The executable `error_bound()` checks this inequality. This is conservative
for tiny distances too, without an unproved relative-error division by zero.

For pivot p, let stored endpoints be:

```text
lo = FP32_floor(max(0, nextdown(min_x d_hat(x,p) - rho)))
hi = FP32_ceil(nextup(max_x d_hat(x,p) + rho))
qlo = max(0, nextdown(d_hat(q,p) - rho))
qhi = nextup(d_hat(q,p) + rho)
raw = max(0, nextdown(lo-qhi), nextdown(qlo-hi))
LB_cert = max(0, nextdown(raw-rho))
```

Outward stored/query endpoints enclose real metric distances. The reverse
triangle inequality makes raw no larger than min_x d_real(q,x). Subtracting
rho makes LB_cert no larger than **every corresponding rounded RN distance**,
hence no larger than the region's RN truth minimum. All subtract results used
as lower bounds are rounded downward; min/max cannot enlarge them unsafely.
The extra sqrt slack is already covered by rho. Ties at U* are retained.

Combine with the unchanged admitted native path bound by max. The old
1e-6 native guard and 0.01 split margin are not replaced by rho. Every
query-region-pool candidate is additionally checked against exhaustive RN
truth, and all selected certificates are checked for no false top-K prune.
Such finite checks support implementation correctness; they do not replace
the arithmetic derivation.

GLOBAL metadata has FP32 lo/hi pairs and a shared ID table. REGION has the
same pairs plus packed six-bit indices into the fixed 64-ID table, padded to
16 bytes. Serialization verifies actual aligned sizes. At eight pivots REGION
requires 70 logical / 80 aligned bytes, not 64 bytes. Shared pivot vectors,
the ID table and per-query distance cache are recorded separately.
