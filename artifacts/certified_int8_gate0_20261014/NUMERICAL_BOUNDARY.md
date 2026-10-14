# Unexecuted numerical-contract boundaries

These are issues to freeze only if a distinct future mechanism is admitted.
They are not a measured failure and do not cause the prior-art verdict.

- FP32 scale storage must be part of the reconstruction definition. For a
  smallest-positive FP32 input, maxabs/127 rounds to zero in FP32; the positive
  scale/domain/underflow policy cannot remain implicit.
- A residual bound must cover the true reconstruction residual and its FP64
  subtraction, sum, square-root and outward conversion errors. Merely passing
  a comparison against one ordinary FP64 estimate is not a universal proof.
- Exact integer dot/norm accumulation does not make the FP64 scaled
  norm-plus-dot expression exact. Cancellation near equal vectors, negative
  rounded squared centers and endpoint/square-root rounding need an enclosure.
- The real L2 metric and the frozen ordered-FP64 squared score are distinct.
  The interval must contain the authoritative ordered score at inclusive radius
  equality, not change metric/order/tolerance or assume real-arithmetic identities
  are bit-identical reductions.
- Raw score fallback is the union of ambiguous candidates and all final hits.
  An ambiguous hit is read once, not double-counted. Membership acceptance alone
  does not supply an exact output distance field.
- Query/control/ID/output/masks, integer code norms if persisted, norm metadata,
  and rounding guards must be charged separately; unknown cost is not zero.
- The plan's numerical label regions have uncovered cases, e.g. certification
  >=0.90 with mean bytes between1.50 and2.00GB or p90 fallback>0.15. No label or
  relaxed gate is invented. The prior-art stop precedes all numerical labels here.

All actual quantizer, residual, scale, interval, score and GPU fixtures are
NOT_RUN. The tiny exact-rational logical witnesses are not any of those gates.
