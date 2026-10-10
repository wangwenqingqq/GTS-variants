# Decision: diagnose packing next; stop the redundant bound recheck

**Select fixed three-leaf warp packing for a later mechanism experiment. Do not
implement it or promote it in this diagnostic delivery.** Keep original GTS.

| Gate | Evidence | Decision |
|---|---|---|
| At least20% additionally prunable using existing entry information | 0/2,929,074 | Fail; do not add a duplicate leaf gate |
| At least30% no-contribution leaves AND a safe prior predicate | 99.99160% retrospectively empty, but no extra existing predicate | Fail the conjunction; no speculative pruning |
| Many object-active warps have at most25% active lanes | 0 with <=8 lanes; actual9/10 | This specific threshold is not met; do not count empty CTA warps as full distance loops |
| Packing independent small leaves improves lane fill without changing visits | Static fixed3:31.24997% to93.74884%, same work; greedy equal | Pass structural screening only |
| Correctness and same-contract net performance of a new mechanism | No new mechanism implemented or timed | Unknown; no production promotion |

## Next falsifiable experiment, not executed here

A minimum fixed3 mapping should preserve all leaves and exact per-object ordered
arithmetic, leaf predicates and output slots. Bound checks, task indexing, packing
and final materialization costs belong in its complete timing. First distinguish
shrinking the512-thread CTA from combining three leaves: a smaller one-leaf CTA
is an attribution control, not evidence of packing. Predeclare the final candidate
and controls before timing rather than trying many packers and choosing winners.

A real win needs correct full results, sanitizer/resource checks, measured issued
work or scheduling evidence, leaf-kernel improvement and a direction-balanced
same-campaign host-ready advantage. More active lanes alone is not success. No
new formal256-query campaign is authorized or run as part of this diagnostic.

Packing is a conventional mapping family, not an established novel contribution.
Before a research implementation, perform the nearest-prior-art kill test. Even
an original-GTS improvement is not external superiority, current-GTSPP improvement
or a dynamic maintenance benefit. If packing fails its measured gate, preserve it
and inspect node-task/materialization costs rather than resurrecting pivot cache.
