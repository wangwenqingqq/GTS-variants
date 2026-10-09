# External closure (in progress)

This folder implements staged baseline admission from the pinned 5598585 source.
Read `CONTRACT.md` and the existing `../rebuild_tree_baselines/BASELINES.md`.
No new primary result is implied by compilation or qualification.

- `cpu_development.py`: disjoint-coordinate leaf selection using the existing
  installed CPU executor. Use `prepare`, then `run`; output directory must be new.
- `prepare_tree.py`: apply minimal ownership/full-delivery overlay to a supplied
  pinned upstream clone. Compile `tree_service.cu` with and without
  `-DCLOSURE_REUSE`, CUDA C++17, `-O2 -lineinfo -arch=sm_120 -rdc=true`.
  Use the resolved toolkit nvcc path, not an unrelocated wrapper symlink.
- `range_service.cu`: complete B1 native cuVS FP32 L2Unexpanded scan, inclusive
  filter, CUB compaction and full output; no finite top-K surrogate. Requires the
  already installed libcuvs C API, RMM, logger and DLPack headers; no upgrades.
- `qualify.py`: preregister then run bounded cases under the existing guarded
  runner. Run family gates independently; retain failed families and all logs.

Service request format: first line number of calls, then `task row radius K`
per call, task 0=kNN / 1=range. Output arrays contain every delivered ID/field,
with offsets and per-call Host-ready times. These qualification executors are
not yet the formal warmup/pass/lifecycle harness. Internal R/T/P and formal
external measurements remain separate gates; no old ratios are multiplied.

## Explicit implementation identities

`tree_native`: `-rdc=true`, no REUSE/TAIL_SAFE. Native query arithmetic/pruning,
plus mandatory wrapper output and allocation-registry release; one call only.
`tree_adapt`: add `-DCLOSURE_REUSE`, repeated B1 lifetime fix only.
`tree_safe`: add BOTH `-DCLOSURE_REUSE -DCLOSURE_TAIL_SAFE` and use
`-Xnvlink=--ignore-host-info`, the established toolkit compatibility recipe.
This separately labeled safety overlay removes one unused out-of-bounds next-root
load, not a numerical/partition/pruning repair. It does not erase native kNN
membership failure or establish full baseline admission.

`UPSTREAM_HEADERS.json` fails preparation on any supplied-header drift. Generated
`SOURCE.json` records every input/output header hash. Actual macros, toolkit,
commands and binaries must be recorded with each private build, independently of
source manifests. Never identify two differently built binaries by one label.

Every prepare/run requires a fresh private work directory outside this checkout.
Pass verified `--numa-node` to CPU/GPU runners; runtime placement must match the
preregistered placement. Keep host paths, UUIDs, environment and command receipts
in private evidence. `finish_a.py` independently rebinds development coordinates,
selected CPU output, exact payload byte counts, native fields, small range cases,
two million-row snapshots and first-call bridges before emitting admission.
Only sanitized, explicitly selected proof summaries belong in this repository.

CPU API qualification uses `native_cpu.py` (`build`, `knn`, `range`, `release`,
`capabilities`). Empty snapshots return empty results; K>N returns min(K,N)
valid neighbors rather than dummy IDs. Native Faiss strict-boundary failures are
retained; `inclusive=True` is separately labeled CPU_FLAT_INCLUSIVE_ADAPT and
must pass both boundary and target-snapshot checks. It does not modify distances
or the external membership/field tolerance. KD/Ball keep native FP64 coordinates,
one native thread, fixed leaf and explicit default traversal parameters.

`cpu_edges.py` checks every leaf 32/128/512 and N=0/1/7/513 with 32 consecutive
calls. `cpu_snapshot.py` is a qualification-only full-output driver for the
inclusive CPU Flat adapter. These new API tests do not retroactively relabel
the original native CPU timing source; private original scripts and receipts
remain independently bound. Future formal timing must freeze the actual adapter.

## Clean compilation and runtime libraries

With pinned local source and already installed dependencies, build outside Git:

```sh
python3 artifacts/external_closure/build.py --work "$BUILD_DIR" \
  --upstream "$UPSTREAM" --cuda "$CUDA_HOME" \
  --cuvs-site "$CUVS_SITE" --dlpack-include "$DLPACK_INCLUDE"
export LD_LIBRARY_PATH="$(python3 -c 'import json,sys; print(":".join(json.load(open(sys.argv[1]))["library_search_dirs"]))' "$BUILD_DIR/BUILD_REGISTERED.json"):${CUDA_HOME}/lib64:${LD_LIBRARY_PATH:-}"
```

Keep that export in the SAME shell/environment used to launch `qualify.py` or
`followup.py`. The builder's environment only reaches compile/ldd subprocesses;
it does not configure the parent shell. Preserve BUILD_REGISTERED/BUILD, logs,
source manifests and runtime library identities with private evidence. The
separate `evidence/CLEAN_BUILD.json` confirms compilation, NOT runtime remeasurement
of those newly built binaries.

`verify_a.py` is the fail-closed completeness gate for this specific campaign:
all20 expected receipts, including two retained runtime failures, all18 successful
runtime output proofs, exact CPU edge matrix/source identity, real adapter hashes
and foreign-process checks are required. Missing cases cannot yield admission.
`finish_a.py` now applies it before saving. The original already-executed numerical
proof remains immutable; `ADMISSION_BINDING` records later independent binding and
the strengthened CPU boundary rechecks without relabeling old execution sources.
`curate.py` refuses to publish an unbound or stale admission summary.

## Direct cumulative / strengthened-reference short campaign

See [measured direct R/T/P results](RTP_RESULTS.md) and the existing
[claim-evidence ledger](../build_distance_tiles/CLAIMS.md). External B remains
pending; the internal results do not substitute for external controls.

`RTP_CONTRACT.json` fixes R/T/P, all six permutations, the unchanged admitted
binary and timing/statistical boundaries. `rtp.py --stage bridge` admits the new
T combination before `--stage primary` launches18 fresh processes. Supply the
private build, registered cases, admitted parent, reference library and guard
paths explicitly; `--help` lists all arguments. A fresh work directory is
required. Every future launch archives `EXECUTED.py` without replacement; the
narrow bridge recovery archives `EXECUTED_RESUME.py` and cannot replace an
executed GPU case. Measured original/recovery source identities are distinct
from the subsequently hardened public verification helper.

`rtp_results.py` requires both private campaigns and those original source files.
It rebinds guards, commands, placement, source, binary, complete outputs/state,
all timing fields and the exact18-job set before producing any statistic.
`rtp_report.py` renders the table directly from that JSON. Run `test_rtp.py` for
schedule, estimator, rejection and receipt-reader regression checks.

Keep the complete proof private. `rtp_curate.py --input "$FULL_PROOF" --output
"$PUBLIC_PROOF"` emits only whitelisted evidence and source/receipt hashes, then
`rtp_report.py --input "$PUBLIC_PROOF" --output "$REPORT"` generates the tables.
Both outputs must be fresh paths; never overwrite original campaign evidence.
