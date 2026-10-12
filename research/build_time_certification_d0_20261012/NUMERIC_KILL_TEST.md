# Numeric kill test: nominal scalar loses exact certificate information

**Result: a native nominal scalar alone cannot determine the required frozen interval, and therefore cannot guarantee every final child extremum.** This is an exact algebraic witness under source-level FP32 round-to-nearest/ties-even subtraction semantics; no CUDA/CPU prototype, measured sample, generated-code identity or dataset error histogram is claimed.

Use D=960, pivot first coordinate `p=1`, remaining pivot/object coordinates zero. Two representable FP32 object coordinates are `a=0` and `b=2^-25`.

1. Exact differences are `a-p=-1` and `b-p=-1+2^-25`.
2. Around -1, the next FP32 value toward zero is `-1+2^-24`. The latter difference is the exact midpoint. Ties-even picks -1. Both native FP32 differences therefore become -1, so every following unchanged nominal operation and same-parent key encoding receives identical operands.
3. FP32-to-FP64 promotion is exact. Both promoted differences are exactly representable. The second square is `(2^25-1)^2 / 2^50`; its integer numerator has 50 bits, so the square fits FP64's 53-bit significand exactly.
4. Ordered directed square/add (with 959 zero tails) and directed roots are exact in this witness. Required intervals are `[1,1]` and `[1-2^-25,1-2^-25]` respectively, distinct bit patterns.

A child segment consisting of any number of such duplicate-coordinate nonpivot rows has extrema equal to the respective pair interval, so scalar information loss is relevant to **final node lo/hi**, not only an artificially stricter per-pair requirement. Physical occurrence indices remain distinct. The witness need not run a new tree or claim a measured keeper failure: it disproves the information sufficiency of that scalar-only mapping.

Native nominal accumulation is double; the loss occurs **before** it, at FP32 subtraction. A correction depending only on that scalar, D and parent cannot distinguish the two inputs. An enclosure could include both outcomes, but does not equal both required endpoint bit patterns.

## Boundary of the proof

This does **not** establish that all real pairs differ, that each pair must retain 16 bytes, that all deterministic enclosures are expensive, or that residual/EFT/coordinate-aware/adaptive algorithms are impossible. Identical final extrema may not require exact computation of every non-extremal pair; a future filter/refine mechanism must prove this rather than be ruled out by the scalar witness. The frozen nominal compiler/pow lowering has not been audited in this D0 task. The validator checks exact integer/rational premises, not CUDA rounding or complete runtime semantics.

For interval producer semantics, see the frozen `numeric.cuh:17-24` and [CUDA 13.1 double intrinsics](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-math-api/cuda_math_api/group__CUDA__MATH__INTRINSIC__DOUBLE.html). The arithmetic operation graph remains two directed subtracts, two directed squares and two directed additions per coordinate, plus two directed roots per pair, until a constructive replacement is admitted.
