# Observation-only design

The baseline is the pinned original tree's complete-ID adapter, not a range
scanner or GTSPP implementation. No search decision, numeric primitive, tree,
layout or launch geometry changes. Instrumentation is removable byte-for-byte.

- Target: SM120, original FP32 vectors / double ordered L2, sequential B1.
- Leaf: one CTA per compacted leaf, 512 threads / 16 warps; thread `did`
  owns object `did`. MAX_SIZE is checked <=32 for participation masks.
- Sidecar: one 40-byte record per allocated node, no query-shared ownership.
  Node predicate thread owns bound fields; leaf thread0 owns entry fields;
  valid object threads atomically OR three participation masks. No shared memory,
  cross-CTA handoff, barriers or new pruning. Original default-stream kernel
  ordering and existing device synchronizations protect node-to-leaf reads.
- Query lifecycle: allocate sidecar once, clear before each query, observe the
  original stages, synchronize, write raw records, then reset. All instrumentation
  time is diagnostic and forbidden as an optimization or formal timing result.
- Existing leaf lower bound versus entry disk is the online screen. Final output
  membership and final-kth comparison are retrospective only. Parallel leaf
  execution has no total branch visitation order or evolving top-k heap.
- Warp ledger distinguishes 16 launched warps/CTA, one or more object-active
  warps, and distance-loop lanes (self skips arithmetic but remains an answer).
  It does not measure hardware occupancy or dynamic warp instruction execution.
- Freeze source, data/index/query hashes and runtime before collection. Stop on
  foreign activity, output mismatch, sanitizer errors or drift. Do not implement
  a gate/packing optimization or collect new formal latency in this delivery.

Novelty screen: rechecking an already enforced original predicate is not a new
mechanism. Packing is a conventional execution mapping, not presumed a paper
contribution. Only this cheap diagnosis is authorized; a later mechanism needs
prior-art and same-contract end-to-end gates.
