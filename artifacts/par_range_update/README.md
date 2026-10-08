# PAR range/update reproducibility artifact

This is a closed reproduction of the **PAR_STRONG dynamic range-query module**,
not a unified GTSPP product or a completed paper-wide evaluation artifact.
The public entry explicitly dispatches PAR_STRONG first. The frozen experimental
executable still defaults to NATIVE when called directly; use this entry, not
an unqualified direct invocation. No CUDA kernel or update algorithm is changed
by packaging.

## Verified checkpoint

[The compact receipt](VERIFIED.json) records the clean code checkpoint
`326e004dd045006d32c1abe1d65d0ae9c86d3a60`: all 11 GPU processes passed,
20152 full query outputs and 24456 event observations were checked, and all
four sanitizer checks passed. Both 10000-query traces include 50 rebuilds.
Two earlier failures (nvcc alias/header lookup; GitHub443 connection) occurred
before any GPU process and are retained rather than omitted.
GPU proof used the documented `--upstream` path with this task's verified pinned
cache; online fetching passed local preparation and remote attempt A but failed
in B. Do not call this unconditional online reproduction success. The final
receipt adds no new speedup estimate and does not complete unified GTSPP.

## Supported contract

| Item | Qualified scope |
| --- | --- |
| Initial data | Deterministic hash-generated N=1000, D=128, integer coordinates 0..255 stored as FP32 |
| Query | Batch 1, inclusive Euclidean radius, full IDs and exact FP32 distance fields |
| Formal historical radius | 0; correctness boundaries also use 10000 (all include) |
| Insert | Reference/reinsertion of an existing physical base row, **not a new external vector** |
| Delete | Current live-multiset rank; base tombstone or insertion-buffer deletion |
| Identity | Logical occurrence/rank, not stable application IDs; duplicate occurrences remain distinct |
| Update protocol | Serialized ACK before the next event; rebuild when actual buffer occupancy reaches 10 |
| Qualified main trace | 10000 queries + 1000 insertions + 1000 deletions; 50 rebuilds; seed 2026100431 |
| Device | Tested on RTX PRO 6000 Blackwell Server, sm_120, CUDA 13.1, Linux, NUMA-bound single GPU |

**Unsupported/unqualified:** kNN, arbitrary external arrivals, variable dimensions,
large-N extrapolation, MVCC/concurrent updates, stable IDs, multi-GPU execution,
Faiss/CAGRA superiority, and paper-wide artifact admission. No claim that these
are impossible; they are not established by this module.

## Fresh-checkout reproduction

Prerequisites already installed: Python 3 + NumPy, Git, g++, CUDA nvcc and
compute-sanitizer, nvidia-smi, numactl. No dependencies, hooks, GPU settings, or
system services are installed/modified. Only a **new** work directory and advisory
GPU lock files are written. Do not use Python `-O` (it disables evidence checks).
The bare command defaults to a new `par-reproduction` under the system temporary
directory. A work path inside any Git checkout is refused, including explicit
paths, to avoid accidentally committing raw/device evidence.

From the repository root:

```bash
python3 artifacts/par_range_update/test_recipe.py
python3 artifacts/par_range_update/reproduce.py --work /tmp/par-reproduction
```

The default selects an idle sm_120 GPU and derives its NUMA node from PCI sysfs.
To choose an idle device explicitly, add `--gpu 7` or `--gpu GPU-...`.
An occupied device or unknown NUMA mapping is refused. The reused guard acquires
both shared lock names, checks foreign processes before/during/after every GPU
job, and can terminate **only its own** process group on conflict/timeout.
Advisory locks are not a reservation against noncooperating users; any such
activity invalidates the run. No existing process is stopped.

The script fetches the pinned upstream GTS commit, checks eight original file
hashes, applies the host/result adapter, copies the existing PAR/region headers,
and checks **all 16 resulting source hashes** against the qualified source.
CUDA executable symlinks are resolved to the toolkit directory so relative
header/helper lookup is not broken by an outer PATH alias.
No previous campaign, external fixture, prebuilt executable, or private controller
directory is needed. Inputs are regenerated and must reproduce the two exact
historical data/event hashes. To prepare without CUDA execution:

```bash
python3 artifacts/par_range_update/reproduce.py --prepare-only --work /tmp/par-prepared
```

For offline preparation, additionally use `--upstream /path/to/pinned/GTS-checkout`.
It is read-only and must contain the pinned `Source Code/GTS` files. The artifact
does not redistribute the complete upstream headers or impose a new license on
them; obtain them from [original GTS](https://github.com/ZJU-DAILY/GTS/tree/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639)
under the upstream authors' terms. `adapter.patch` contains the measured adapter
changes and context, not an independent reimplementation of GTS.

## Acceptance and outputs

The default entry builds the same-source executable plus the existing CPU/GPU
structural checks, then performs 11 serialized GPU processes:

1. Structural check: nine topologies, six states, SPLIT/FUSED controls; this checks
   shared plan/stale-epoch/capacity machinery, **not PAR performance**.
2. PAR/NATIVE correctness at both boundary radii: four fresh processes.
3. PAR memcheck/racecheck/synccheck and NATIVE memcheck: four fresh processes.
4. Full 12000-event trace once each for PAR and NATIVE: two fresh processes.

The CPU integer squared-L2/live-multiset oracle checks every returned ID and exact
FP32 field, every observed update transition/rebuild, ordered native/PAR identity,
and final module-owned release. The oracle is independent of the CUDA traversal;
small scalar-oracle regression checks cover duplicates, rank deletion and inclusive
radius semantics. A failure is retained in its new directory; the recipe never
replaces failed/slow samples automatically.

`PREPARED.json`, `BUILD.json`, `ENVIRONMENT.json`, `REGISTERED.json`, `ROWS.json`,
`GUARDS.json`, and `COMPLETE.json` bind source, input, executable, job order,
oracle, and guard evidence. Raw inputs, full output arrays, logs and GPU/process
details stay in the chosen work directory, **outside Git**. A valid final receipt
has `state=scoped_artifact_verified` and `timing_claim_admitted=false`.
The NATIVE control shares the original `rnum[0]=0` correctness repair and output
adapter; it is not an unmodified historical executable. The update algorithm,
native kernels, arithmetic and pruning geometry remain unchanged.

These fresh trace durations are reproduction diagnostics, not a new speedup
estimate: one PAR and one NATIVE run do not satisfy the six-round performance
contract. Historical measured performance stays in its original campaign, with
the same-binary native comparator, full Host-ready/ACK denominator, and retained
order/confidence evidence. See [claim/module ledger](CLAIMS.md).

## Remaining submission gates

This closes the scoped reproduction chain, not the research thesis or the complete
GTSPP submission. Required next gates remain unified kNN/range/update integration,
application-facing identity/arrival semantics, appropriate larger dynamic workloads,
and the separate final10000 external-comparison admission. Integration must first
pass its own novelty and same-contract correctness/performance gates. Anonymous
submission packaging/license review is also separate; this existing public owner
repository is not an anonymized AE bundle.
