# Current-P audit (2026-10-11)

The human selected PAR_STRONG/FULL/TILED, not Safe-C1. The live 25-file
P build matched every prepared source hash; the binary and prepared receipt
are pinned in KEEPER_PINS.json. The parent logical adapter is the latest
qualified P of the external-closure campaign.

PAR range materializes one entry for EVERY canonical nonempty leaf, using -1
for inactive entries. It launches one 256-thread CTA per list entry. Each
active leaf loads the shared query, reaches one CTA barrier, then object j
writes only leaf_slot[nid]+j. Canonical leaf partitions make output owners
disjoint. The final N-sized scan/collect is common and unchanged. Leaves can
change size after updates/rebuilds; stride-ten packing covers all legal 1..20
sizes. Bounds, candidates and distance accumulators are not shared.

FULL kNN is already a dense verify_distances kernel, not the old dataProcessKnn
leaf verifier. It remains byte-for-byte unchanged. Global BLOCK_THREADS stays
256: changing it would also change traversal, refit and other algorithms.
P1 changes only the range verify_materialized launch. P2 changes that kernel
and its call, preserving the existing target::hit arithmetic.

The current numerical contract uses ordered RN FP64 subtraction, multiplication
and addition (numeric.cuh), unlike the original-GTS FP32-subtraction adapter.
No helper, layout, pruning, update or result contract is replaced.

A per-lane inactive-leaf return before the shared-query barrier is unsafe. P2
checks the whole three-entry group uniformly, loads the query cooperatively,
then all 32 threads reach the barrier. Only afterward may lanes 30/31 or an
inactive/missing leaf return. List bounds guard the final partial group.
