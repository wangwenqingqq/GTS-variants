# Scoped unified kNN / PAR range / serialized-update artifact

One executable now dispatches exact B1 kNN, inclusive range queries, physical-row
reinsertion and current-live-rank deletion through **one native GTS update
loop**. The native AoS base, tombstones, reference buffer and rebuild stream are
shared. This closes an integration gap; it is not a new novelty or external
performance claim. Qualification results are in [VERIFIED.json](VERIFIED.json)
and [RESULTS.md](RESULTS.md). The frozen contract is [DESIGN.md](DESIGN.md).

## Reproduce

Requirements: Python3 with NumPy, Git, g++, CUDA supporting `sm_120`,
compute-sanitizer, numactl, and an idle compute-capability12.0 GPU. No packages,
GPU settings, foreign processes or other campaign files are changed.

```bash
python3 artifacts/unified_search_update/protocol.py
python3 artifacts/unified_search_update/test_guard.py
python3 artifacts/unified_search_update/run.py
```

The third command creates a fresh scratch outside Git, fetches pinned original
GTS, verifies every upstream/parent source hash, builds fresh legacy and unified
executables, selects one idle GPU, then runs all registered checks. It resolves
CUDA executable symlinks before invocation. To select another idle single GPU
or use an already acquired original-GTS checkout:

```bash
python3 artifacts/unified_search_update/run.py \
  --work /path/to/new-scratch --gpu 7 --upstream /path/to/original-gts-checkout
```

The checkout is the repository root at commit
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`, not its `Source Code/GTS`
subdirectory. All required bytes are verified even in offline/cache mode.
An online fetch failure is not a successful reproduction; keep that attempt
and retry acquisition in a **new** scratch. Raw work must not be inside Git.
`--phase prepare`, `--phase build`, and `--phase verify` separate these gates;
build/verify use the existing scratch, reject changed source/recipe/binaries,
and do not overwrite prior runs. Do not use Python `-O`.

Each GPU process uses the existing dual advisory lock, PCI-derived NUMA binding
and pre/during/post foreign-compute checks. A conflict invalidates the process;
only the process group owned by this run may be stopped. All failures and slow
samples are retained; no automatic resampling or hidden workload change occurs.

## Direct executor

After preparation/build, the interface is:

```bash
REGION_MODE=PAR_STRONG KNN_MODE=BOUND \
  /path/to/new-scratch/bin/unified DATA EVENTS 2 RADIUS OUTPUT K
```

Run it only under the same GPU guard when measuring. The direct binary strictly
parses and retains both files before any GPU allocation; malformed shapes,
rows, flags, ranks, capacities and K/radius are rejected. Flags are:

| Flag | Meaning | Index contract |
| --- | --- | --- |
| 0 | Reinsertion, retaining duplicates | Current physical base row |
| 1 | Delete one occurrence | Current live-multiset rank |
| 2 | Inclusive range query | Current physical base row |
| 3 | Exact kNN query | Current physical base row |

Physical query/reinsertion rows may be tombstoned. IDs in the answer are live
ranks, **not stable object IDs**. kNN returns lexicographic (squared distance,
live rank), includes live self-matches, and pads missing slots with `(-1,+inf)`.
Range outputs retain the legacy ordering; every ID/FP32 field is checked.

`BOUND` uses eligible seed cutoff plus strict partial-sum pruning; `FULL` is a
same-selector unpruned correctness control. `NATIVE` is the original range
control. Static tree-mask/Graph kNN is not transplanted into this B1 module.
The exact public P7 kernels and provenance are retained in
[KNN_PARENT.json](KNN_PARENT.json); only their duplicate TN declaration is
removed in the prepared integration copy.

## Workload inventory and limits

| Case | Initial N / D | Range / kNN queries | Updates | K | Role |
| --- | --- | --- | --- | --- | --- |
| Full mixed8 /32 | 1000 /128 | 5000 /5000 per trace | 1000 reinsert +1000 delete,50 rebuilds | 8 /32 | Shared-state rollover stress |
| Legacy regression | 1000 /128 | 10000 /0 per trace | Same updates/rebuilds | 8 allocated, unused | Three fresh alternating pairs (2/1 order split) |
| Boundary0 /10000 | 1000 /128 | Alternating query kinds | Buffer first/last delete, repeated reinsertion,2 rebuilds | 8 /32 | Inclusive radius, IDs, FP32 fields |
| All tied8 /32 | 1000 /128, all zero | Same boundary stream | Same boundary updates | 8 /32 | Duplicate occurrence / tie ordering |
| Sparse8 /32 | 1000 /128, later base10 | Paired range/kNN | Empty live set, deleted seeds, buffers,2 rebuilds | 8 /32 | Infinity cutoff / missing slots |

These are synthetic integer-valued FP32 coordinates in [0,255], B1 only,
physical base+buffer<=1024 and live<=1010. **A mixed10k trace contains5k kNN,
not10k kNN.** It is not the earlier N1M final10000 static comparison, nor new
external-vector arrival, concurrency, stable-ID support, large-N, B32,
Graph replay, Faiss-IVF/CAGRA admission or paper-wide GTSPP completion.

Timing includes every event ACK, full D2H answer, compaction, native tree
rebuild, PAR refresh, kNN base repacking and final workspace release/drain.
Host strict parsing/validation happens before the captured context/setup timers;
it is not included in any reported warm-trace or cold-total estimate. Context,
initial build/layout and disk output are separate from the warm trace. This is
not a complete process-start-to-exit latency measurement. Initial kNN allocation is setup; every rebuild mirror cost is
inside its triggering update before ACK. Timing has the observer on in both
variants; no new observer/phase speedup admission is asserted.

Only the existing PAR-range contract is tested for <=5% non-regression in three
fresh alternating pairs; mixed-mode single runs are correctness/stress, not a positive
speedup estimator. Publication preserves inherited rights and redistributes no
complete upstream GTS headers, datasets, binaries or raw machine captures.
