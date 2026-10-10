# Original GTS leaf execution geometry

This is a fixed32 **diagnostic**, not a new optimized tree or a latency campaign.
The original complete-ID adapter, node predicates, distance arithmetic and launch
configuration are unchanged. See `CONTRACT.json`, `DESIGN_CARD.md`,
`LEAF_EXECUTION_GEOMETRY.md`, `WORK_COUNTS.json` and `DECISION.md`.

## Reproduce

Requirements: Linux, Python >=3.11, CUDA13.1 / SM120, NumPy/CuPy in the existing
oracle Python, numactl, compute-sanitizer, and the preceding read-only reference
fixtures. No dependencies are installed by these scripts. Current collection was
on the user-authorized physical GPU1/NUMA0. Before running, verify that the supplied
UUID resolves to that physical device and topology; the collection preflight now enforces index1 and NUMA0. GPU idle/foreign-process checks and shared locks are
mandatory. Never signal foreign processes or change GPU settings.

```sh
python3 test_protocol.py "$PINNED_GTS_SOURCE"
bash build.sh "$PINNED_GTS_SOURCE" "$NEW_SCRATCH"
python3 "$NEW_SCRATCH/run.py" --reference "$REFERENCE_ROOT" \
  --prior "$QUALIFIED_PIVOT_CAMPAIGN" --data "$GIST_DATA" \
  --python "$CUDA_PYTHON" --gpu "$VERIFIED_GPU1_UUID" --numa 0
```

`QUALIFIED_PIVOT_CAMPAIGN` is the final guarded preceding campaign, whose parent
contains `extensions/boundary` with the independent all-K and last-leaf oracles.
The source adapter verifies all eight original upstream file hashes. Data/index
hashes match the preceding campaign; absent reference indexes are rejected rather
than rebuilt. Each collection output path must be new. Only scratch is written.

The count binary writes a raw header `(magic,N,D,node_count)` followed by per-query
`(qid,pivot_calls,pivot_dimensions)` and one 40-byte row per allocated node. The
per-node format is frozen in the contract. Every visited leaf can be reconstructed
by joining its node ID to the pinned index; output members are joined separately.
Rows include entry bounds and acceptance/participation masks, not just totals.
Raw binaries stay outside Git and are hash-addressed in `RAW_MANIFEST.json`.

```sh
python3 analyze.py "$PINNED_INDEX" "$RAW_GEOMETRY" "$FULL_RESULT" \
  "$INDEPENDENT_ORACLE" "$NEW_SUMMARY_JSON"
```

Counts describe distance-loop **thread participation** and configured warp slots,
not scheduler occupancy, sampled eligible warps or dynamic SASS execution. Empty
launched warps are not assumed to run the full distance loop. Packing outputs are
structurally allocated warp bins, not necessarily arithmetic-active warps on a
self-only leaf. No measured latency or packing speedup is inferred from simulation.

## Rights and preservation

Original GTS: [ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS), revision
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Upstream headers are caller-supplied,
not redistributed. No new license is imposed on them or derived code. The initial
missing-oracle-helper packaging failure and the second collection's derived-bytecode
closing-manifest failure are preserved, not rewritten as passes. One bounded final
recollection excludes only bytecode, uses identical GPU binaries and queries, and
passes the complete identity gate. Its sidecar bytes and work summary match the
second collection exactly.
