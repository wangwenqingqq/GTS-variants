# Pre-experiment sector novelty triage

**Admission: CHARACTERIZATION_ONLY.** This task asks whether one already-known
query-priority family retains certificate yield after fixed 8-coordinate grouping.
It does not propose a new ordering thesis and does not admit CUDA or paper claims.

[BOND](https://www.cs.uoi.gr/~nikos/sigmod02.pdf) Section 5.1 and
[PDX-BOND](https://ir.cwi.nl/pub/35044/35044.pdf) Section 5 establish query-aware
exact partial-distance order; PDX also combines that order with vector-block
vertical storage. Their blocks are not automatically the unchanged row's 32B
coordinate sectors. Exact narrow equivalence to fixed-budget row-major sector
selection is **unknown at triage**, not inferred absent. Summing priorities into
sectors alone is not demonstrated non-incremental novelty. A positive diagnostic
triggers the dedicated narrow audit; a negative/gray gate stops without a sweep.

The [NVIDIA guide](https://docs.nvidia.com/cuda/archive/12.9.1/cuda-c-best-practices-guide/index.html#coalesced-access-to-global-memory)
Section 9.2.1 distinguishes requested bytes from transactions and discusses
32B units for compute capability 6.0+. It does not prove our execution traffic.
The conditional geometry assumes a future device payload base aligned to 32B;
the unchanged input file's 12B header makes the CPU mmap offset misaligned.
No device allocation, sector counter, cache behavior or coalescing is measured.

This is a cheap fixed-pool falsification, not a costly implementation campaign.
No positive count or modeled-byte result rescues a subsumed research mechanism.
Primary source identities are recorded; PDFs and downloaded HTML stay private.
