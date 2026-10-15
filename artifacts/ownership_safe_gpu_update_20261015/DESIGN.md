# CUDA design card — before GPU compilation/execution

Prototype construction and exploratory CPU enumeration preceded this card;no CUDA target has run. This card freezes the implementation/measurement intent before GPU compilation/execution,not a retrospective claim of preregistration before exploratory code.

| Item | Contract |
|---|---|
| Target | RTX PRO6000 Blackwell,SM120,CUDA13.1;actual card/NUMA/driver recorded in private registration |
| Payload | FP32 vectors copied as uint32 bits;row-majorD960 in real service;D1/31/128/960/1024 in synthetic correctness |
| Domain |1<=B<=min(N,512),distinct live IDs;serial ACK;no cross-insert composition |
| CTA/warp roles |One128-thread CTA per final destination;all4 warps perform identical strided column copies;no producer/consumer split |
| Global state |Database allocation unchanged;per-Store4096B plan buffer only forFINAL;Host plans and ledgers separately owned |
| Shared/TMEM |None;no swizzle,bank or Tensor Core assumptions |
| Registers |Row source/destination,one word/column,loop/address state;no persistent accumulator;expected low register count,verify actual SASS/resources |
| Useful work |FINAL loads/stores net_rows*D32-bit words;Native/WAVES move native_moves*D words. MetadataH2D=8*net_rows except native one-move dispatch |
| Barriers |No CTA/warp/device barrier in materializer;stream order H2D→kernel and final stream sync protect consumption/reuse |
| Ready graph |Host validation→logical ownership/witnesses→composition+certificate→metadata upload→kernel→stream sync→ACK;overwrite only after previous ACK |
| Live set |Host tail/target plan lives through submission/sync;device plan persists untilrelease;kernel per-thread word last-used before next loop iteration |
| Nonalias |Distinct destinations,original sources outside all final destinations;all original allocated vector bytes preserved including retired rows |
| Fallback |B1 uses native erase;one final row uses nativeD2Dcopy;zero moves submits no copy/kernel but retains sync |
| Ordinary control |WAVES uses all native commands and exact RAW/WAW/WAR-safe levels;descriptor arrays remain alive until final sync |
| Cost floor |No arithmetic bottleneck predicted;max(memory traffic,launch/readiness) plus Host planning/API/wait. This is a hypothesis,not achieved bandwidth |
| Verification |Independent CPU row-label replay+exhaustive tests→native body roundtrip→GPU full-capacity/high-entropy/invalid tests→sanitizers→screen→same-round micro/W2→profilers |
| Promotion |Operator≈25% andW2≈10% are effect-size reference lines;confidence/effect/scope separate. Ordinary batching explaining gains means engineering-only |

Query kernels and source layout remain immutable. No query indirection,tombstone,statistics refresh,async API visibility,Graph or production claim is introduced. Primary Host-ready ACK includes all new construction/submission/audit costs. Strict capacity and qualification-only per-ACK readback are excluded from primary events;release remains included in service. Their time is separately recorded,not silently removed from only one candidate.
