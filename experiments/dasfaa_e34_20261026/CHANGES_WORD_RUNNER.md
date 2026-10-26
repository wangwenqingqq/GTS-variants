# Word E4 bounded phase runner

**Current state: local implementation under contract-scope hold, not production-ready.**
The primary owner identified that the existing P harness returns IDs without the
native k-distance fields. Word initialization/GPU work must remain stopped until
the user resolves the full ID+distance output scope and a newly frozen harness
passes review. These provenance fixes do not waive that unresolved requirement.

## Ownership and implementation

Added only `word_campaign.py`, `test_word_campaign.py`, and this note. The running
vector executor, safety helper, evaluator, kernels, and frozen contract were not
edited. Word reuses `campaign.execute`, `campaign.acquire_same`, and the existing
resource/PID-safe admission helpers. No SSH, NVML, GPU, sanitizer, real signal, or
remote process was invoked during this implementation task.

## Phase freeze and launch

The primary owner must explicitly launch Word after the vector plan is processed.
`STOP_CAMPAIGN.json` prevents launch. The local controller must also check its
`LOCAL_STOP_CAMPAIGN.json` before sending any remote command; optionally convey
that state with `E34_SSH_FAILED=1` or `E34_SSH_STOP_FILE`. The runner cannot infer
a local SSH failure from an inaccessible remote host.

Require an immutable task-local `resume_20261026/WORD_PHASE_FREEZE.json` (or
`E34_WORD_FREEZE`) with:

```text
files: {root-relative-path: {sha256, bytes}, ...}
paths: {word_manifest, tree_binary, count_binary, scan_script, audit_script,
        oracle_binary, oracle_source, tree_source, source_build_manifest,
        word_build_manifest}
oracle_sha256: {"61000": hash, "150000": hash, "300000": hash}
runtime_files: {absolute-read-only-dependency-path: {sha256, bytes}, ...}
```

Every named path, every Word-manifest input, every feasible full oracle, and every
compiled P header from `source_build_manifest.compiled_sources` must be included.
Each case base/query path must stay inside the task root and be covered by both
the Word input manifest and the phase file map; commands recheck task locality.
The required `WORD_BUILD_RECORD.json` binds exact tree/count/oracle output paths
to source paths, successful guarded compiler commands/logs, CUDA13.1/sm120 metadata,
and source/binary/log hashes. The timing build cannot enable instrumentation;
the separate count build must define `INSTRUMENT=1`.
All file hashes are checked before initialization and before each step. The phase
also freezes its runner, existing executor/helper, resource guard, interpreter,
boot ID, vector-completion evidence, and complete plan. The exact original
absolute `FAISS_PYTHON` invocation path is frozen separately from its resolved
executable and executable hash, preventing two venv launch paths from collapsing
into one identity. A nonempty `runtime_files` map freezes installed compiler/backend
sources, critical extension libraries, and version metadata; these absolute
external dependency files are read and hashed only, never edited or installed.
Keep raw device-specific dependency paths in local evidence, not portable publication. Full oracles and the new
bounded oracle are hash-checked again immediately before auditing outputs.

Run each command through the outer guard with a timeout no greater than 900 s:

```text
python word_campaign.py <root> init
python word_campaign.py <root> step <explicit-word-epoch>
```

Set `GTSPP_GUARD` and `FAISS_PYTHON` to verified host-local paths. There is no auto-run,
all-mode, retry, or replacement epoch. The phase uses the prior vector GPU UUID;
if it is unavailable the primary owner must leave Word pending rather than launch
or select another card. The global campaign lock serializes vector/Word work.
The latest vector telemetry timestamp is copied into the Word telemetry state,
retaining the >=30 s cadence across this successful phase boundary.

Each successful step does at most one guarded child, limited to 600 s and 16 GiB
RSS, with the existing available-memory gates. CPU dependency/oracle work and
known skipped loads never acquire or launch GPU work. The bounded CPU oracle uses
16 OpenMP threads, clears visible GPUs, and publishes a hash only after completion.
Any operational error latches the global stop and invalidates the phase timings.

## Preserved scope

- N=61K,150K,300K,611K; Q=1,32,1024; k=8. Literal 611K remains infeasible after
  holding out 1,000 of the 611,756 source rows; neither arm is run there.
- Twelve bounded N=2,000 sanitizer tasks: P/S x memcheck/synccheck x all three Qs.
- Complete-output correctness precedes timings. Incorrect gate loads stay visible
  and are not timed or replaced. Q1024 must return exactly 1,024 rows; other Qs
  return all 1,000 held-out queries. The frozen Word auditor is loaded by its
  verified path, without modifying it.
- Six fresh-process P/S pairs, alternating PS/SP by round, three retained passes
  and one excluded warmup. Timing binaries are never instrumented builds.
- Separate P `count_binary` tasks run only after P correctness passes. Raw counts
  cover one full correctness pass: 1,000 queries including the ragged8 at Q32, or
  1,024 rows including24 repeated queries at Q1024. No count is mislabeled as a
  mean complete32-query batch.
- S byte records distinguish padded character bytes (Q*N*109) and indexed length
  metadata bytes (Q*N*4). These are logical input volumes, not measured DRAM traffic.
- G is not launched and P-approx does not exist. E3 and optional Protein/ChEMBL
  gradients remain separate unfinished scope.

## CuPy JIT binary provenance

Before every S child, temporarily set `CUPY_CACHE_DIR` to the task-owned
`<word-epoch>/cupy_cache`, `CUPY_CACHE_IN_MEMORY=0`, and
`CUPY_CACHE_SAVE_CUDA_SOURCE=1`. The existing executor copies this environment
into its guarded child. Restore the parent environment afterward, including
when the child fails. No arithmetic, compiler-option, launch, or timing-scope
setting is changed.

After each S process, record every cached `.cubin` and `.cu` by cache-relative
name, byte size, and SHA256 in that run's `jit_manifest.json`. The whole CuPy
disk-cache container is hashed; this is not a normalized or extracted SASS hash.
The cumulative cache includes RawKernel and any cached internal CuPy top-k/sort
kernels, without asserting that every cached function was dynamically executed.
A successful S process without a cached compiled binary fails the provenance
gate and cannot contribute timings.

Successful per-run manifests form an append-only SHA256 chain, with an atomic
`jit_head.json` checkpoint. Every successfully executed S step also embeds its
manifest-relative path, SHA256, and sequence into its append-only `STEP_*_DONE.json`
result. Cache validation checks every completed S anchor against the full chain
and current head; deleting the newest manifest/cache keys and resetting the head
to an older self-consistent state is rejected. Skipped S loads create no anchor.
Existing binary/source files must remain byte-identical;
new cache keys may be added only during a controlled S process. Validate the
complete manifest chain and cache snapshot before every step, including final
phase completion. Rewritten/deleted/untracked files, a modified/rewound history,
or missing binary evidence are terminal errors. Failed-process cache snapshots
are retained as diagnostics but never advance the valid chain. Keep the actual
cache outside Git with the rest of the raw runtime artifacts.

This implements capture and validation, not evidence that a real Word JIT run
has occurred; the primary owner must still execute and inspect those records.

## Local validation

`python3 experiments/dasfaa_e34_20261026/test_word_campaign.py` passes 31 mock-only
checks: full load/order preservation, immutable inputs and compiled headers,
full/bounded oracle mutation, 611K exclusion, global/local-SSH stop gates, vector
phase ordering, terminal stop/no replacement epoch, correct command repetitions,
exact Q1024 output size, bounded CPU threads/no GPU, separate instrumented counter
selection/full-pass denominators, honest logical byte records, JIT environment propagation/restoration, binary/source
hashes, append-only cache keys, prior/during-run mutation, missing binaries, failed-run
diagnostics, manifest-chain mutation, task-local case coverage, guarded build
bindings, external runtime dependency mutation, exact venv launch identity,
self-consistent JIT rewind attacks, and real S-task checkpoint anchoring. `py_compile`
also passes. These checks do not establish real Word correctness or performance;
real sanitizer, oracle audit, timing, and final independent review remain required.

The exact interpreter invocation is also bound to the runtime provenance before
initialization; choosing a different environment for the first init is rejected.
The creator-to-runner integration check covers the actual manifest schema.
