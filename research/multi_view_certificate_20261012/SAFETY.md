# Safety and measurement boundary
The original score cache retains ascending-dimension RN-FP64 squared L2, separate multiply/add, FMA/reassociation disabled. N=1M, D=960, K=8, B=1, queries, U*, P2 ownership remain frozen.

## Gates
- G1: every stored view is proved contractive via exact-rational Gram row-sum <=1. QR/eigh orthogonality is not assumed exact. Random views are independently contractive; their concatenation is not asserted contractive.
- G2: full projected-coordinate extrema at L3/L4/L5 are expanded by ETA=1e-8, nextafter-outward FP64, then outward FP32. All forty cached directions are checked for complete coverage. The analytic ordered-dot error is below ETA on the verified full-data domain [0,2].
- G3: **43,512,000** constituent bounds and **10,656,000** max bounds are checked against own-P2 original-score truth. Zero violations.
- G4: zero false top-K prunes for every constituent and max. Ordered-dot equality on 4,448 original-vector rows covers all objects in twelve independently selected regions and all queries. Full original-score-cache arithmetic validation is inherited from base evidence, not recomputed here on all original vectors.
- G5: old covariance/mean and PCA8 basis bytes, P2 extrema, own-truth bytes and all three keeper counts reproduce exactly.
- Additional: 3,528 generic scalar bounds equal vectorized bounds; fixed-basis dominance and contiguous nesting pass. Python3.13/NumPy2.4 replay checks every constituent again and all 36 packed 64B record arrays, reloads serialized bytes and reproduces bounds/masks/counts. A separate original-vector build fixture replays (264 rows x32 new directions).

A record concatenates eight FP32 lo/hi pairs, without per-view padding. In 8x1 logical views are 8B apart, not separately 16B aligned. This packed offline format is not a tested GPU load strategy.

## Arithmetic caveats
No Python -O. Do not use builtin floating sum to validate ordered RN-FP64 accumulation: Python3.12+ can compensate. The repaired inherited split reference explicitly left-folds in ascending object-ID order. Lower-bound energies are never summed across views.

Contraction and ETA/RHO margins provide the safety argument; finite full-workload comparisons are regression gates, not arbitrary-input proofs. Domain/hash/nonzero-coefficient checks preserve the inherited normal-range error contract. Domain or arithmetic-policy changes require re-derivation.

## Stage distinctions
Compilation, norm proof, sampled original-vector checks, full cached-truth safety, count bridge, serialization replay and rendered plots are distinct completed gates. CUDA/Graph/memcheck/NCU/NSYS/stress/sustained latency gates are not applicable and were not run. Resource-only seconds are retained for audit, not comparator speed.
