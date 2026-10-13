# Gate0 decision: NO_GO_LOSSLESS_PROGRESSIVE

## Required questions

1. **Can a single lossless representation support exact progressive decoding?**
   Yes for this admitted finite-FP32 range workload. The stored four layers recover
   all 960M original coordinate bits, and strict safe interval bounds give zero
   FN/FP on all 32M memberships. Original-coordinate ordered-FP64 scores agree
   bit-for-bit for every full decode. This does not establish efficient GPU execution.
2. **Does source payload fall at least 30% below dimension-progressive?** No.
   Bit-progressive is **1,025,475,825 B/query** versus **1,014,828,776 B/query**:
   ratio **1.0104914732926336**, a **1.0491% increase**, not the required reduction.
   The GO ceiling is **710,380,143.2 B/query**. Even the conditional ceiling of
   **850,000,000 B/query** is exceeded.
3. **Is a second raw FP32 search truth required?** No. Candidate search receives
   only the four layers and one full query; final refinement completes those
   layers. Original data and frozen distances remain external validation evidence.
   No claim is made that the entire research host contains no original data copy.
4. **Is representation size at most 1.05x raw?** Yes.
   **3,840,000,064 B** versus the **4,032,000,000 B** ceiling. The 64-byte header is
   included; there is no separate codebook or raw search fallback.
5. **Final gates?** **Gate0: NO_GO_LOSSLESS_PROGRESSIVE. Gate1: NOT_RUN.**
   Quality, ownership, and size pass; the primary source-byte gate fails. Applying
   the approved precedence leaves no threshold ambiguity. Zero GPU/NCU starts.

## Mechanism, counterevidence, and added costs

The tested mechanism replaces incremental dimension reads with incremental
ordered-FP32 bit layers and exact per-coordinate enclosing intervals. The first
four key bits contain sign and only three high exponent bits, no mantissa; their
intervals are too loose on this fixed pool. **31,997,099 / 32,000,000 pairs** survive
that stage. Consequently, the first two layers consume **959,956,485 B/query**
before considering the final two layers. This alone exceeds the stop threshold.
The small 32-bit survivor set cannot recover this already-spent source payload.

Relative to full scan, ideal source payload falls by 73.2949%, but the stronger
dimension-progressive comparator removes slightly more bytes. Using only the
weak full-scan comparison would misrepresent the outcome. Layer decoding,
interval arithmetic, prefix retention, flag/output recording, and any GPU
compaction/state traffic are added costs, not unexplained free work. Actual DRAM
and latency effects remain unknown; no speedup is inferred from logical counts.

## Implementation, mechanism, and thesis decisions

- **Implementation:** CPU reference is correctness-qualified within the frozen
  workload. It is not a production GPU path.
- **Mechanism:** reject this query-independent ordered-key layout with the fixed
  4/8/16/32 schedule on this GIST1M pool. Confidence is high for this finite pool:
  every planned pair was evaluated, rather than sampled for byte estimation.
- **Thesis:** do not promote the broad "exact search as progressive decoding"
  thesis. Prior art already establishes important storage/query primitives and
  that abstraction in other domains. This failed feasibility test supplies no
  decisive same-contract advantage or distinct research contribution.
- **Do-not-revive boundary:** no automatic bit/dimension sweep, learned codec,
  query/radius change, entropy coding, raw fallback, or GPU port to rescue this
  rejected candidate. Reopening requires an explicitly authorized new contract,
  an independently defensible mechanism, renewed prior-art review, and a cheap
  bound showing source payload below the stronger baseline. It is not a scheduled
  continuation of this experiment.

No Gate1 directory or CUDA prototype was created. The existing dimension-progressive
keeper and its historical evidence remain unchanged; this result neither strengthens
nor weakens its separate correctness or dynamic admission gates.
