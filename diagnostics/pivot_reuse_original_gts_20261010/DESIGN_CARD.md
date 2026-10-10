# G1 design and qualification boundary

- Target: one SM120 RTX PRO6000, user-authorized physical GPU1/NUMA0.
- Contract: GIST1M×960 FP32 input, original double Euclidean arithmetic, K8,
  **sequential B1 only**, complete original-ID/FP32 fields returned to Host.
- Hypothesis: avoid the measured query/object repeated arithmetic. No new upper
  bound or pruning. The strongest competitor is the mapping/reset/branch cost
  exceeding roughly1% arithmetic savings.
- Roles unchanged: `getDisPQ` one thread per query/sibling-pivot group;
  `nodeProcessKnn` one thread per query/node; `dataProcessKnn` one CTA per
  surviving leaf, original512 threads with at most20 active object threads.
- Immutable mapping: direct object-ID→compact pivot slot,4N bytes; no full-table
  hash. Same-level pivot uniqueness and sibling identity are checked. Different
  vector-equal instances have distinct object IDs. Cross-level aliases share a
  slot. Externally edited same-level alias indexes are explicitly rejected.
- State ownership: one active query per process; cache double and valid-int
  belong to that query only. Allocation, validity memset and frees are inside
  original query time. Static mapping preparation/space are separate setup.
- Ready edge: original default-stream ordering and per-kernel synchronizations
  publish a full double before any next-layer/leaf read. Same-level writers use
  distinct slots. No new barrier, shared-memory handoff or asynchronous pipeline.
- Live state: one extra slot/valid/cache branch in distance kernels, no vector
  copies or new shared-memory arrays. Record final resource metadata separately;
  existing large metric-dispatch stack is not attributed to this cache.
- G0 search header is byte-identical to the existing complete-ID adapter.
  All drivers reject B32. G1's direct search entry also rejects qnum!=1.
- Qualification: fixed32 full-output oracle checks, bitwise G0/G1 fields,
  active-work conservation and hit bridges; duplicate/self synthetic4097 inputs;
  cache component cold-reset and pointer churn; mem/race/sync checks of component
  and one fixed real query. Formal source and orchestrator freeze follows gates.

## Explicit uncovered cases

The original complete-search adapter admits N≥4097 and K≤32. The four-object
component test covers N<K cache behavior, **not** original root-leaf search or
variable-cardinality result semantics. Candidate management is unchanged because
G2 already exists. No new certificate is claimed for original small-N/root-leaf
search, all possible K-boundary orderings, in-process index replacement,
concurrent/multi-query batches, arbitrary alias-edited trees, updates or Graphs.
These limitations must remain visible; the measured conclusion is the fixed
GIST1M/K8/B1 contract, not a universal original-GTS exactness proof.
