# GPU-Tree first-loss diagnosis and bounded repair

Experiment: `GTSPP_20261010_gpu_tree_first_loss`; no performance claim.
Parent: author GPU-Tree partition/B+-tree/priority-queue implementation, PNUM8,
K8, M4, DNUM500. Original, ownership-only, tail-safe and K-bound repaired
identities remain separate. No P kernel changes.

## First observation, before repair

On the fixed N4096/D17 duplicate-occurrence input, the first partition's bound
search has only three occurrences {0, 1, 2101}. Its maximum distance
0.952549934 is below the true global eighth distance (~0.965016685).
It prunes node171 at lower bound0.961247087 before visiting instances374/394.
The main search repeats this underfilled-heap pruning. All11 roots survive
partition and tree filters; merge cannot restore missing leaves. Both diagnostic
processes reproduce the prior native/32-call reuse complete ID/field bytes.

## One repair mechanism

A K-distance upper bound must be backed by K occurrences. Retain the incoming
valid bound until the local answer queue is full. The initial bound search uses
infinity before K results and publishes infinity if it remains underfilled.
Apply this invariant at both native traversal call sites. Keep the earlier
unused-tail-read protection under its separate safety macro. Do not deduplicate,
change precision, relax quality, tune PNUM or replace the retrieval algorithm.

## CUDA design card

- Target: SM120, CUDA13.1; original FP32 L2 fields and FP64 membership reference.
- Roles unchanged: one CTA/query; one thread/subtree in full search, one thread
  for initial bound selection. Native persistent topology and query heaps remain.
- Layouts/ownership unchanged; native B+-nodes, candidate queue and answer queue.
- Ready graph unchanged: construct -> bound -> partition/tree filters -> traverse
  -> local top-K -> merge/sort -> full Host output -> release.
- No new buffers, shared memory, barriers, MMA or dispatch. Scalar fullness test
  changes only bound readiness. Register impact is not measured performance.
- Work prediction: additional traversal/verification before K candidates exist;
  necessary for exactness, not an optimization. Output and precision unchanged.
- Reject: any missing member/field/occurrence, invalid runtime, sanitizer failure,
  or unexplained resource/identity change. A bounded pass is not N1M admission.
- Ladder: old-output parity traces -> bounded repair/range regression -> three
  sanitizer tools -> two target snapshots -> conditional separately registered
  same-round P/GPU-Tree timing. No automatic replacement; maximum8 new processes.
