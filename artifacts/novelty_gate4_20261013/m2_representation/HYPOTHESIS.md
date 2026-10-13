# M2 — one compact interval screening representation

Only concrete candidate: one8-bit interval code per original coordinate0..255,
fixed per-dimension uniform boundaries over the initial data. First/last intervals
have unbounded tails, so later finite coordinates need not change the boundaries.
Raw960-coordinate rows remain the sole exact fallback store. No PCA, reordering,
PQ, bit-plane variant or second encoding is explored.

The interval contains the true FP32 coordinate. Query-to-interval squared distance
is a conservative lower bound. Screen at128 and256 dimensions using codes only;
then reread **all256 raw coordinates of every encoded-screen survivor** to form
the exact state before later stages. This reread is charged to the first-two-stage
budget, not hidden as a later-stage cost. No vector is accepted from its code.

Expected benefit: avoid raw prefix reads of rejected rows. Added costs:256MB codes,
257 FP64 boundaries per dimension, full-dataset encoding, query LUT, retained-ID
selection, exact-prefix rereads and ordinary later-stage/output work. A new CUDA
realization, update benchmark and physical traffic measurement are not included.

This mechanism is the known interval filter/refine family (matrix M2). Its byte
headroom may be positive without a new thesis. No non-incremental distinction
from that family is asserted. Reopen requires a different explicit mechanism,
not choosing another quantizer or making this one faster.
