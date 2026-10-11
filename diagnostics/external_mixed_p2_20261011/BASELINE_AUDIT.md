# Frozen baseline audit

This campaign compares the qualified Fixed3 current-P production binary against
one previously qualified strong dense GPU retrieval-core adapter. It does not
search for new implementations and does not claim that E is the universally
fastest possible service. No stale timing observation is used in a new ratio.

P2 inherits PAR_STRONG range, ordered RN FP64 leaf distances, FULL dense KNN,
TILED construction, native buffered updates and rebuild/refit. Only the already
qualified Fixed3 range verifier differs from pre-Fixed3 current-P. Both its exact
source and existing binary/build/resource identities are rebound before running.

E uses Faiss 1.15.1 `bfKnn` with cached native vector norms and `use_cuvs=false`;
range uses cuVS FP32 `L2Unexpanded`, inclusive radius flags, CUB complete selection,
full fields and D2H delivery. Its occurrence/position tables map mutable physical
rows to immutable logical occurrences. Insert appends one vector and updates its
norm; delete swaps the last vector/norm into the deleted physical row. E never
builds a tree and is not charged an artificial rebuild. This is a service adapter,
not a statement that Faiss natively provides the mixed service.

Exact source, static Faiss library, upstream GPU distance/norm headers and resolved
shared-library hashes are verified. Installed cuVS package metadata inspected
after closure reports 26.8.1, RAFT/RMM 26.8.0; immutable ELF hashes, not those
mutable labels, establish execution identity. `pe_check.py` is the repaired canonical
checker at external source commit b3ac5ed, not the earlier failed checker.
Qualification independently replays every update and checks full output and the
final logical occurrence set. Duplicates are distinct occurrences.

Numerical contracts differ but are declared: P2 ordered FP64 field bits and
ordering; E native squared/FP32 fields within the frozen 5e-5 scale-1 tolerance.
Membership and K selection are exact on the qualified fixtures, not tolerant;
this does not prove exact native-FP32 membership for all possible boundary inputs.
E returns an extra native-squared observation payload and pays its delivery cost.

## Novelty Gate 0

This is an external positioning/kill test, not a new research mechanism. Dense
exact retrieval, append/swap-last bookkeeping and warp grouping are existing
techniques. Additional adapter engineering or an internal packing win cannot
establish novelty. A favorable external result would justify broader same-contract
experiments, not automatically a novel thesis; a negative result is retained and
must guide the next falsifiable mechanism hypothesis.
