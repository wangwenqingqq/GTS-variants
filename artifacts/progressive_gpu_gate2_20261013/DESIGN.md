# One-candidate design card

Target: RTX PRO6000 Blackwell Server Edition,188SM, sm_120, original row-major
FP32 GIST1M/D960. Keeper is the frozen strengthened non-padded B1 binary.
Hypothesis: fixed staged prefix reads cut coordinate demand enough to beat the
near-streaming keeper despite stable CUB selection and scalar count readbacks.

| Role | Ownership / lifetime |
|---|---|
| CTA256 /8 warps | Eight distinct active row occurrences; no shared state or CTA barrier. |
| Warp32 | Coalesced32-coordinate loads within its original row; uniform tail return, all active lanes participate in five shuffles. |
| Lane0 | Persistent FP64 estimate, original int32 ID, current-stage replay-coordinate count. Only lane0 uses ordered replay. |
| Stage temporary |16-byte AoS for every current input plus uint8 keep flag; immutable until CUB finishes. |
| CUB stable select | Writes survivors into the second16-byte state buffer in original ID order; temporary scratch preallocated for N but every selection is charged per query. |
| Host controller | Reads the actual selected count after each stage; never knows survivors in setup. Launches next stage from the returned count. |
| Final output | Reads complete selected hit states, emits all IDs, FP32 Euclidean fields and inherited FP64 casts of FP32 scores; all D2H/resize/completion charged. |

Original coordinates0..959 and stages128/256/512/960 remain fixed. Stage1
generates owner IDs and zero initial sums inside each request. No survivor lists,
full scores, query-dependent metadata or unresolved construction are moved to
setup. Build only uploads unchanged vectors and preallocates reusable capacity.

Ready graph: query H2D -> stage reads -> tuple/flag writes -> stable select ->
count D2H + stream completion -> next-stage launch -> final materialization ->
complete output D2H + completion. A single stream orders every buffer use. The
temporary buffer is overwritten only after count completion proves selection
has finished. No Graph, cooperative launch, persistent kernel or inter-stream
shared handoff is used. Pointer/stream churn tests use independent instances.

Phase live set: each lane holds one FP32 chunk accumulator and address state;
lane0 additionally holds the FP64 continuation/interval and ordered fallback
scalar. No960-element register array, dynamic shared memory, register cap or
hand-tuned occupancy target. Static registers/local/stack are recorded after
build rather than inferred from source scopes.

Predicted ledgers: coordinate demand1.014829GB/query; additional state/owner/
padding/flags about87.6MB/query under a pessimistic all-input select-read model.
FP32 direct differences/FMA and warp sums replace full-D reads; ordered replay
adds rereads and scalar FP64 work. Four scans, four selections, count waits and
one output kernel add control/readiness work. CPU Gate1 is not a timing keeper.
Reject conditions and all measurement gates are frozen in CONTRACT.json.
