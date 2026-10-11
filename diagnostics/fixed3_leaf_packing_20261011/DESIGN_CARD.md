# Fixed3 design and falsification card

Target: RTX PRO6000 Blackwell Server, SM120, CUDA13.1. Scalar FP32 inputs,
row-major D96/960, original FP32 subtraction and ordered double accumulation;
no tensor instructions, approximation or reassociation. B1 only, original tree,
workspace, bounds, task list and complete output adapter.

| Role | G0 | G1 | G2 |
|---|---|---|---|
| CTA | one leaf,512 threads | one leaf,32 threads | up to3 leaves,32 threads |
| Object owner | lane=slot | lane=slot | ten-lane subgroup,slot=lane%10 then+10 |
| Persistent state | per-thread double accumulator | same | same, sequential slots |
| Output owner | original task/slot | unchanged | original task/slot |
| Collective state | none | none | none |

Live state: task/node/query addresses survive through a leaf; one object's
accumulator and loop index live through its ordered distance loop; three result
writes end that object's lifetime before its owner's next slot. No shared/TMEM,
pipeline stages, swizzle, bank-conflict assumption, register cap or new barrier.
SASS/resources must verify actual registers and local stack/spills. The original
multi-metric body can retain unrelated local-memory requirements; do not call
these a new spill without comparison.

Ready graph: existing merge completes -> independent leaf loads -> ordered
distance loop -> original slot stores -> existing synchronization -> original
sort/merge -> complete host output. No cross-leaf handoff or earlier pruning.

Hypothesis: excess CTA/warp scheduling and partial-warp scalar instruction issue
cost can be reduced. G1 isolates block shrink; G2/G1 isolates ten-lane multi-leaf
ownership, including its extra address selection and second padding-slot pass.
Useful distances and logical input/output bytes are invariant; actual cache
traffic need not be. Poor row-major cross-lane coalescing, dependent FP64 work,
register pressure or unchanged non-leaf stages can limit the end-to-end benefit.

Frozen three variants only. CPU mapping proof, real-kernel all-slot/tail tests,
full independent oracle and sanitizers precede profiling. Separate count builds
record per-node sidecars and must match bit-for-bit; their times are never used.
Two reverse-order fixed32 NSYS rounds decide Gate E. The intended fixed NCU
launches cannot be collected: before runtime collection the counter-admission
probe returned ERR_NVGPUCTRPERM. No privilege escalation or driver-policy change.
E5 therefore uses NSYS-recorded actual grid/CTA counts plus unchanged useful
work and lower leaf duration; issued instructions, traffic and hardware occupancy
remain unavailable, not inferred. Only a passed gate permits the registered
256-query six-round experiment.
See CONTRACT.json for the exact order, estimator, stop rule and uncovered scope.
