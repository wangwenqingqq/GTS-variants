# Same-semantics build-distance tiling: design and gate0

The two prior diagnostic captures justify an engineering intervention in the
shallow getPivotDis mapping, not a new tree algorithm or research contribution.
Nearest prior art is ordinary independent CUDA block/output partitioning and
[grid-stride execution](https://developer.nvidia.com/blog/cuda-pro-tip-write-flexible-kernels-grid-stride-loops/).
This cheap novelty test rejects novelty from tiling alone; the experiment is
still useful to strengthen the baseline and remove a measured execution cost.

## One change, no materialized task list

Keeper B0 is current PAR+FULL with original one-node/512-thread-block scoring.
B1 partitions a node into512-object tiles. A flat block ID explicitly decodes
`node_slot = blockIdx.x / tiles_per_node`, `tile = blockIdx.x % tiles_per_node`.
The original composite key continues to use node_slot, **never the new block ID**.
Each CTA reloads the same original midpoint pivot into its own four-byte shared
slot. Only tile0/thread0 writes pid_list[node]; no inter-CTA dependency/race.
Each valid object has exactly one writer; leaf sentinel keys and tail predicates
retain the original semantics and per-object arithmetic/order.

For a layer, the conservative maximum-node-size bound starts at N and applies
`upper = floor(upper/10)+9` per depth. This monotone bound covers each original
equal-child/remainder-last partition; using the exact last-child formula on
only the bound would be invalid because that formula is not monotone. Use
ceil(upper/512) tiles per node. Root N1M has1954 CTAs; the next grids are
1960/2000/2000/10000. These are computed task counts, not speed predictions.
No task allocation, prefix scan, pivot-preparation kernel, copy or new fence
is needed. Host bound/grid computation and the added launch argument remain
inside the existing construction boundary.

## Frozen hardware and data contract

Live-admitted idle RTX PRO6000 Blackwell Server96GB, SM120, CUDA13.1, driver
590.48.01; common device-local NUMA placement and unchanged shared settings.
Original FP32 AoS coordinates, D128/D960, per-point original FP32 subtraction,
pow and accumulation expressions; double composite key, original thrust sort
and tie/partition policy. Parser remains N<=1M (plus inherited warm/buffer
capacity), K8 for this campaign. No Tensor Core, precision, layout, threshold,
search, unsafe incremental insertion or dynamic-policy change.

| Role / object | Ownership / lifetime / readiness |
|---|---|
| CTA | one explicit node/object tile,512 threads,16 warps; no cluster |
| Lane | one object position; same ordered dimension loop and scalar result |
| Shared pid | four bytes per CTA; thread0 produces, original CTA barrier, all lanes consume |
| pid_list | exactly tile0/thread0 per splitting node; subsequent sort/split reads after existing whole-kernel fence |
| dis_list | one writer per valid object; sort consumes after original fence |
| registers | node/range/pivot/index and scalar distance live across dimension loop; added tile decode, no reduction state |
| global data/order | unchanged AoS/strides; immutable during scoring; overwritten only by original sort after completion |
| persistent state | no added GPU allocation or owned buffer |

The lower-bound hypothesis is larger independent grid/waves, **not fewer distance
calculations or proved coalescing/byte savings**. Added costs: CTA pivot reloads,
integer decode, conservative padding/tail CTAs, extra argument and Host geometry.
Registers/stack/local/shared and exact selected-function SASS are checked after
compilation. Occupancy/traffic claims need actual profiler counters; none is
inferred from the grid count alone.

## Verification and timing ladder

1. Fresh source overlay; unchanged arithmetic body/sort/query files; NODE is
   retained as opt-in control, no new default. Bound and writer ownership tests.
2. Complete per-layer input order/keys/pids, sorted keys/order, occupied tree
   fields/split/empty masks, and owned refit bounds. Unowned/uninitialized node
   and unwritten pid slots are explicitly masked, not treated as defined state.
3. D128 high-entropy, tail, repeated-key, root-leaf and mixed leaf/split cases;
   original GIST4096; pointer churn/restoration plus two-rebuild bounded trace.
   Then original N1M with one actual rebuild and complete profile-prefix answers.
4. Changed-kernel memcheck/racecheck/synccheck; target N1M access memcheck. Prior
   unresolved96B context symbols remain distinct from ordinary access passes.
5. Only if these gates pass: six alternating B0B1/B1B0 pairs,12 fresh primary
   processes on unchanged336 events (256 queries,40I,40D,2 rebuilds). Complete
   Host-ready/ACK continuous time including all maintenance and final release;
   setup/warmup separate. No profiler time denominator or old samples pooled.

Reject mapping-only status on any defined-state/topology/result difference;
stop and diagnose, not silently relax equality. CI crossing1 or opposing order
strata is inconclusive. Kernel-only improvement is insufficient. Longer shapes,
100k workflows, production/leak-clean/default and external wins remain separate.
