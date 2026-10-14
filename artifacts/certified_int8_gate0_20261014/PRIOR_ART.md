# Gate A: original-score certificates and precision escalation

**Verdict: SUBSUMED_PRIOR_ART at the proposed core-thesis level.**
This is a research-admission judgement, not a numerical rejection of INT8.
The requested INT8/L2 implementation and its performance remain untested.
No dataset row has been quantized or replayed.

## Direct evidence and material differences

The closest source is [PVS in EAHR, arXiv2608.07152v1](https://arxiv.org/html/2608.07152v1#S2.SS3.SSS1),
dated 2026-08-07, before this plan. Section 2.3.1 supplies per-vector symmetric
Int8 codes/scales, quantized queries, residual-based deterministic intervals for
original float32 inner products, and raw-vector evaluation only for ambiguous
ordering. Appendix A.1 adds outward endpoints and a finite-precision guard,
conditional on finite intermediates, no integer overflow and the stated operation
count/error model. This is not merely exhaustive search over quantized scores.

PVS targets inner-product ranking and resumable top-k, not this ordered-FP64
Euclidean range contract. Its metadata, interval width and implementation costs
are not assumed identical. It is a preprint; no peer-reviewed publication or
source-code/benchmark reproduction is claimed. Those distinctions do not make
candidate-wise certified precision escalation a new core mechanism.

## Mandatory coverage

| Seed / area | Primary source and locator | Evidence category / admission relevance |
|---|---|---|
| Error-bounded approximate dot products; qdot | [QDOT](https://arxiv.org/abs/2105.00115), Sections 2-3, Theorem 3.2 and GPU implementation discussion | Bounded mixed-precision arithmetic is established; tolerance-controlled HPC, not alone original-score exact vector retrieval with selective candidate fallback. |
| VA-file / compact approximations with exact refinement | [VA-file, VLDB1998](https://www.vldb.org/conf/1998/p194.pdf), Section 4.1, pages 202-203 | Full compact-file scan, deterministic geometric lower/upper bounds and original-vector refinement already establish exact Euclidean filter/refine without a tree. Cells differ from residual balls; not the same quantizer. |
| Scalar-quantized exhaustive search | [Faiss IndexScalarQuantizer source](https://github.com/facebookresearch/faiss/blob/main/faiss/IndexScalarQuantizer.cpp) | Scans encoded data using scalar-quantizer distance computers. Exhaustiveness of the encoded-space scan is not bit-exact original-vector scoring. Not a direct certified-fallback precedent by itself. |
| Quantization plus full-precision reranking | [Qdrant quantization](https://qdrant.tech/documentation/manage-data/quantization/), rescoring/oversampling; [BBQ documentation](https://www.elastic.co/docs/reference/elasticsearch/mapping-reference/bbq), oversampling | Original rescoring improves quality on a selected set; it does not certify that every excluded original candidate is irrelevant. |
| Mixed-precision vector search / GPU / Tensor Cores | [FaSTED](https://arxiv.org/abs/2508.21230), Sections 3 and 4.6; [official repository](https://github.com/bwcurless/FaSTED) | FP16/FP32 Tensor-Core Euclidean computation with empirical accuracy evaluation. No universal zero-error original-FP32 decision/fallback guarantee is adopted. A GPU port cannot rescue a subsumed core thesis. |
| RaBitQ | [RaBitQ](https://arxiv.org/html/2405.12497v1), Theorem3.2, Eq.15 and Appendix E | Its cited tight error interval is high-probability, not a deterministic enclosure of every original pair. Do not conflate a theoretical error bound with zero-FN/FP certification. |
| BBQ | Official documentation above | Approximate search with oversampling/rescoring; not the requested unconditional certificate over all original candidates. |
| NVQ | [NVQ](https://arxiv.org/html/2509.18471v1), Sections1,3 and5 | Per-vector non-uniform quantizers and high-fidelity ANN/reranking; no deterministic original-score fallback guarantee established by the inspected text. |
| Decision-preserving low-bit search | [When Does Low-Bit Quantization Preserve the Decisions of Vector Search?](https://arxiv.org/html/2609.09854v1), Sections4 and6 | Deterministic trace coupling is conditional on action agreement; held-out certificates bound selective risk. Neither alone establishes this pointwise zero-error low-precision scan. |
| Deterministic original-score intervals + candidate precision escalation | PVS, locators above | Direct category 4 overlap with the core proposal. GPU category 5 is NOT reproduced here and is not needed for the CPU Gate A stop. |

Categories: (1) high-recall ANN; (2) exhaustive quantized-domain scoring;
(3) empirical raw rerank; (4) deterministic original-score certificates;
(5) candidate-wise GPU precision escalation. The first three are not sufficient
grounds for this stop. The primary stop relies on category 4, with older exact
Euclidean filter/refine as corroboration, not on ANN recall marketing.

## Narrow kill test and scope of inference

The proposal's four broad components—complete low-bit candidate evaluation,
deterministic error interval, original full-precision semantics, selective raw
fallback—are already present together in category 4. Changing inner product to L2,
top-k to range, rounding precision or hardware does not itself supply a distinct
non-incremental mechanism. This is the **inferred thesis-admission decision**;
we do not assert that another paper implements the identical 968B representation
or frozen 32-query ordered-FP64 protocol.

In real arithmetic, an inner-product interval [c-B,c+B] and exact norm sum A
give squared-L2 interval [A-2(c+B),A-2(c-B)]. Residual balls also give the plan's
reverse-triangle interval. The local rational witnesses check these elementary
relations and conservative ties, not a floating-point or GIST certificate.
Original norm metadata/reconstruction and authoritative FP64 rounding would
still need a separate cost/quality proof; they are not silently free.

**Stop before quantizer implementation, residual fixture, 1M conversion and 32M
replay.** All numerical query/fallback metrics are NOT_RUN, not zero or failures.
Reopen only for a specifically non-incremental mechanism with a new frozen,
same-contract comparison, or evidence that the direct precedent lacks the stated
core conjunction. More packaging, a different dtype or a small speedup is not enough.

Immutable source identities and acquisition limits are in
[SOURCE_IDENTITIES.json](evidence/SOURCE_IDENTITIES.json). Primary snapshots remain
private; no PDFs/code snapshots or claimed external speedups are redistributed.
