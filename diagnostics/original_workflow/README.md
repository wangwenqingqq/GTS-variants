# Original GTS is the active baseline

## Continuation — 2026-09-24

The next bounded round also completed on user-authorized idle GPU2: 36 processes,
3,648 query counts, and four NSYS traces. Blocking synchronization cut main-thread
CPU time by roughly70–73% but increased workflow wall time by roughly20% on the
two synthetic repeated workloads. See [the GPU2 attribution report](profile_20260924/RESULTS.md).
The current AGENTS.md records authorization to use other idle GPUs with per-device
admission and locks; earlier GPU0-only wording below is historical.

GPU0 execution is now complete: original GTS passed 7/9 count probes and failed
2/9 because an empty insert buffer retained its previous result count. A separate
one-line `rnum_reset` variant passed all nine probes, plus nine memcheck and nine
synccheck runs. An independent original build reproduced all nine original
outcomes. See [the continuation report](RESULTS_20260924.md) and
[validated evidence](results_20260924/EVIDENCE.json). No performance claim is made.

The preparation record below and `PREFLIGHT.json` are historical snapshots from
commit `1ab7b08`; its delivery hashes refer to files at that commit, including the
README before this continuation note. The pinned original CUDA files remain
unchanged. This branch packages the continuation for `wangwenqingqq/GTS-variants`;
raw runtime artifacts remain under ignored `local/` directories. The upstream
`ZJU-DAILY/GTS` reference identifies source provenance, not the push destination.

## Decision — 2026-09-24

Stop developing the legacy unsafe `archive/GTS_incremental` variant. Preserve
its source, reports and negative results as historical evidence; do not delete
or silently repair them. The active baseline is **original GTS**, upstream commit
`3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`, identified by the eight GTS source hashes
in [the existing original-source manifest](../original_tree_redundancy/SOURCE_PINS.json).
The repository-root include/src files are still the historical incremental code,
not the active comparator. The local snapshot was rechecked against all eight
original hashes. A source copy is not proof of the current remote host's state.

No prior incremental speedup or correctness result transfers to original GTS.
Original GTS buffers inserts, queries the tree and buffer, applies tombstones,
and rebuilds at its native **10-item buffer threshold**. It does not directly
append records into padded leaves. Keep the unmodified original as a distinct
reference even if a separately named correctness/portability repair is needed.
This is baseline selection and preparation, not a new novelty or speedup claim.

## Preparation-time status and next gate (historical)

- Local source identity and deterministic probe/oracle tests: checked; see
  `PREFLIGHT.json`. No original CUDA source or kernel is edited by these tools.
- Nine **synthetic semantic probes** are prepared; no GPU outcomes are claimed.
- The configured remote SSH route returned connection refused during this turn.
  No remote state was verified, binary built, GPU work launched or host changed.
  No alternate host/GPU or background retry was started.
- First next gate: restore/verify the existing route, verify remote source hashes,
  hardware/toolchain, GPU0 process state and advisory lock; compile a fresh original
  binary, then run checks and bounded sanitizer probes before profiling.
- Prior original-GTS query-only results remain in
  [original_tree_profile](../original_tree_profile/README.md) and
  [original_flow_20260923](../original_flow_20260923/README.md). They did not test
  insertions/deletions. Its static range workspace failure on a large-memory GPU
  remains separate evidence; do not call that a timing result or hide a repair.

## Frozen preparation contract

`gts_20260924_original_update_contract`: N1000, D128, L2, FP32 storage of
SHA-256-derived integer coordinates in[0,255]. All1000 original rows are unique.
Native MAX_H3, MAX_SIZE20, buffer threshold10 are unchanged. Peak live rows1010;
no leaf-padding or direct-insert mechanism is introduced. These probes fit the
nominal fixed-height capacity; actual leaf and memory legality still need GPU
validation. Radius0 isolates identical rows; radius10000 includes all possible
points. This is deliberately **not a representative latency workload**.

Each probe starts a fresh process. Query row0 is retained; inserts reference row0
only, before the first rebuild. Deletions select current logical positions.
Rebuild preserves the retained row0 as the first row. Thus current/original row
identity agrees where used; broader post-rebuild insertion semantics are not
being assumed. An independent active multiset and integer squared distances
compute exact expected counts. Full result IDs/distances, general distributions,
other metrics, concurrency and sustained performance are not certified by counts.

| Probe | Purpose | Expected query counts, not GPU results |
|---|---|---|
| query_only | Original update-query control | 1,1,1 |
| all_include | Full result count, no mutations | 1000 |
| buffer_insert | Query before/after buffered insert | 1,2 |
| base_delete | Delete an included base row | 1000,999 |
| buffer_delete | Query buffer then delete its last row | 2,1 |
| rebuild_no_prior_buffer_query | Rebuild control without old buffer count | 11 |
| rebuild_after_buffer_query | Query buffer, trigger rebuild, query twice | 2,11,11 |
| mixed_delete_rebuild | Base delete then rebuild | 1009 |
| rebuild_then_delete | Delete one rebuilt duplicate occurrence | 11,10 |

The stale `rnum[0]` hypothesis is **source-only**, not a reproduced GPU failure:
original update.cuh clears in_size after rebuild (line539), conditionally refreshes
rnum only for a nonempty buffer (592–595), and unconditionally adds rnum (597).
Buffer-delete and before/after-rebuild control probes can localize that boundary.
Retain any failure and localize the first divergence before editing; do not assume
it explains another version's missing-result failure.

## Use the prepared copy, never root include/src

```sh
python3 diagnostics/original_workflow/test_prepare.py "$ORIGINAL_GTS"
python3 diagnostics/original_workflow/prepare.py prepare "$ORIGINAL_GTS" "$SCRATCH"
# $ORIGINAL_GTS is the pinned original directory containing include/ and src/.
# $SCRATCH must not exist; preparation performs no GPU calls.
```

After the remote preflight is satisfied, use the installed CUDA toolchain:

```sh
"$CUDA_HOME/bin/nvcc" -std=c++17 -O3 -arch=sm_120 -rdc=true -lineinfo \
  -Xptxas=-v -Xnvlink=--ignore-host-info \
  -I"$SCRATCH/source/include" "$SCRATCH/source/src/main.cu" \
  -o "$SCRATCH/bin/gts_original" > "$SCRATCH/logs/build.log" 2>&1
```

This is a pending build command, not a claimed compiled artifact. Reuse the
existing admitted GPU0 runner's locking/snapshot/timeout/sanitizer procedures
when executing each manifest case. The native command shape is:

```text
gts_original data.txt CASE.updates 2 RADIUS cost.txt
```

Capture the exact command, binary/input/source hashes, stdout/stderr, return code
and pre/post GPU state in new per-case directories. Check return code and CUDA
errors independently of the count parser; matching counts do not waive them.
A nonzero exit, CUDA error, timeout or foreign GPU activity stops the run; preserve
the record. Do not label any such record a valid timing sample.

```sh
python3 diagnostics/original_workflow/prepare.py check "$SCRATCH" CASE COST_FILE
```

After original correctness is bounded, the workflow audit resumes on original
operators: static RNN/kNN, update traversal/counting, buffer distance/scan/merge,
delete lookup/prefix/compaction, getNewData, build distance/sort/split, workspace,
managed scalar control and host waits. Coalescing and CPU/GPU-boundary mechanisms
remain separate, and full-operation A/B includes all added packing/copy costs.
No new runner/profiler framework is introduced while the host is unavailable.
