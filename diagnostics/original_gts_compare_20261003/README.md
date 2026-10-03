# Original GTS baseline recheck

The user requested an original-GTS comparison. The immediate prerequisite is
to identify the intended optimized comparator without substituting an abandoned
incremental implementation or a range-only implementation for kNN.

This directory delivers a **baseline-only pilot**, not a completed GTSPP/GTS
comparison. See [RESULTS.md](RESULTS.md) and the immutable registration in
[CONTRACT.json](CONTRACT.json).

## Replay the measured baseline checkpoint

Use Python 3.11+, the qualified scratch tree from the preceding native-kNN
campaign, the exact measured GTS binary and unchanged data/index caches.
`REFERENCE_ROOT` must contain its `delivery/run_locked.py` portable runner,
`verify_outputs.py`, oracle, query fixtures and source/hash manifests. Inputs,
binary results and caches are not redistributed. Their identities are retained
in the text evidence. A fresh rebuild with a different container hash is a new
campaign, not a replay of this pinned checkpoint.

```sh
python3 pilot.py --reference-root "$REFERENCE_ROOT" --data-root "$DATA_ROOT" \
  --out "$NEW_SCRATCH" --python "$FAISS_PYTHON" \
  --gpu "$VERIFIED_IDLE_UUID" --numa "$VERIFIED_NUMA_NODE"
```

The script verifies source, input, binary and harness hashes, uses a lock and
before/after process admission for every GPU process, and checks full IDs and
distance fields outside the timer. Existing outputs are not overwritten.
It slices the old frozen oracle rather than changing quality requirements.
The original preserved source and caches remain untouched.

## Comparator identity still required

- The older `gtspp_knn` experiment explicitly uses `archive/GTS_incremental`.
  That is not an admitted baseline after the user's abandonment decision.
- The recent `batch_exact_highdim`, `batch_tree_inheritance` and
  `external_mask_validation` implementations measure complete range queries,
  not a native kNN implementation.
- The next formal A/B must name an exact candidate source/commit and freeze its
  semantics before launch. Both sides must be remeasured in direction-balanced
  processes. Do not call this pilot a paired experiment or a production gate.

The initial local checkpoint was held because of a pre-existing credential-bearing
trace in repository history. This publication uses a new standalone branch containing
only the two requested deliveries, without inheriting that history. Existing refs
are untouched. This does not remediate older exposure or revoke affected credentials.
