# Candidates and retention order

The table was evaluated before retaining B1; retention means one graph comparator, not admission to prototype. Remove execution labels before testing a dependency claim. Strong C2 already permits direct segment gather/reduction in split.

| Candidate | Exact targeted C2 dependency | New dependency/state | Synchronization/lifetime/owner | Prior-art risk | Correctness risk | Source-level physical upside | D0 disposition |
|---|---|---|---|---|---|---|---|
| X0: pre-sort no endpoint state | Endpoint write/read across native sort | To work: another persistent encoding, changed sort/producer schedule, or later recomputation | Certificate produced under parent; child unknown until sort; ordinary registers/shared die at kernel completion | High for generic fusion/streaming; no admissible complete new graph supplied | Cannot cross unchanged native kernels in only ephemeral storage | Target 32 MB/level endpoint round trip | Rejected in the single-producer/unchanged-kernel/no-state model; no universal byte lower bound |
| X1: produce after sort | Global endpoint sidecar | Second coordinate read and full directed recomputation | Child known; fold intervals locally; new per-level refit/reduction completion | Ordinary recompute-versus-materialize tradeoff | Exactness plausible if membership and ordered arithmetic preserved, not validated | Avoid 32 MB sidecar but restore 7.68 GB source operand reads/level | A concrete tradeoff, not single-read certification; not retained |
| Y0: nominal scalar + fixed envelope | Full directed pair stream | Scalar correction/envelope | Nominal parent score available before child; correction state lifetime unspecified | Standard error-envelope risk; not surveyed as retained mechanism | Same nominal scalar can imply different required node extrema; exact contract fails | Potential arithmetic reduction, not quantified or measured | Scalar-only exact reconstruction rejected by witness |
| Y1: residual/EFT/adaptive certificate | Some/all full directed stream | Per-coordinate residuals, proof state, filtering/refinement or fallback | Must specify precise producer, state and final extrema before child consumption | Unresolved; mechanism not specified enough for a mini-gate | Wider enclosure is not bit-identical final extrema; a constructive exact producer is missing | Unknown, including added tests/corrections | Unknown future mechanism, not admitted and not declared impossible |
| Z: split ownership propagation | Alleged owner map + standalone post-split reduction | Same physical-row sidecar, gathers and min/max; block scratch | Parent -> child via sorted order and native interval; reduce before next overwrite | Direct ordinary block/segmented reduction | Same source obligations as C2, including later-level membership stability | Zero required dependency delta against strong C2; launches may differ only vs weaker schedules | Retain one complete graph, then reject by equivalence |

## X: what must survive?

Safe information is computed while a row has a scoring parent; the future child assignment depends on sorting. With completed scoring followed by unchanged native Thrust kernels, ordinary producer registers/shared memory do not survive to the child consumer. Reuse without rereading requires **some persistent sufficient information** across that cut. Another buffer/hash/queue is still materialization, even if it is not named an endpoint array. A changed persistent producer-sort-consumer algorithm needs its own exact order/state/readiness proof; none is supplied here.

This is a conditional storage-or-recompute argument, not an information-theoretic claim that every pair always needs exactly 16 bytes. Inputs persist, replay exists, endpoint compression or extrema-only certification may be possible. X1 removes endpoint state by restoring the coordinate reread; source accounting prices that tradeoff but predicts no runtime.

## Y: what exactly failed, and what remains unknown?

The [algebraic witness](NUMERIC_KILL_TEST.md) rejects reconstructing exact intervals or required extrema from only the native nominal scalar, dimension and parent identity. It does not prove that a producer using coordinates/residuals must execute every original intrinsic, nor that all cheap deterministic enclosures are impossible. A generic widened enclosure changes the frozen final lo/hi contract. Error-free transforms, input-specific exactness tests, compressed certificates and adaptive extrema refinement require a concrete constructive graph and worst-case fallback before admission. Rewriting RD/RU calls into different operations is not, by itself, deletion of their information dependency.

## Z: why it is not a second research mechanism

`id_list` already transports physical occurrence identity through the unchanged sort. Child `lid,size,pid` already defines the consumer segment and inherited pivot. Compute ownership on consumption; gather two endpoints per row; use ordinary min/max. Strong C2 can do this inside split with no separate owner-map stage. Z still has all these value/readiness edges. Naming the same operation ownership propagation does not create a deletion.

## Selection

Select **Z only** because it is the one complete, same-contract design with explicit producers/consumers and costs; apply graph equivalence and its specific reduction mini-gate. Selection does not discard a demonstrated X/Y mechanism: X1 is the known reread tradeoff, X0/Y0 fail their specified models, and Y1 has no admitted constructive producer. Do not implement three candidates or call missing evidence a proof of their universal impossibility.
