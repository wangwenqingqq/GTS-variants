# Authorized static-matrix recovery (historical)

This records the first recovery authorization, not live status. It subsequently
stopped with44 valid rows; see [second stop](STATIC_SECOND_STOP.md) and the
[separately authorized second recovery](STATIC_RECOVERY2.md). Do not relaunch
the original68-entry driver.

The user approved correcting the CPU environment and resuming at the failed
entry, **without rerunning any of the four passed processes**. This supersedes
the stopped status at checkpoint `3aac39e`, not its original evidence.

## Exact recovery boundary

- Keep all original R1/R2/R3 sources, four successful primary payloads and the
  failed fifth invocation. The original public STOPPED proof is fixed by SHA256
  in `STATIC_RECOVERY.json`; it is not rewritten into a successful result.
- Resume the original72-job schedule at index4: one failed CPU Flat entry plus
  67 never-attempted entries, **68 new processes**. Do not replace any further
  failure automatically. Completion would consume91/102 primary attempts,
  including18 prior internal, four preserved external, one failed external and
  68 recovery attempts. GPU qualifier attempts remain32/32.
- Correct only CPU dependency routing. CPU Flat uses the already-qualified
  Faiss interpreter and native OpenMP setter/getter at one thread; threadpoolctl
  is required only for KD/Ball. No installs or upgrades. The GPU Flat branch AST,
  all native queries, GPU binaries/kernels, data, queries, tolerances, timings
  and method/task order are unchanged.
- Apply the historical `STATIC_CPU_ENV_FIX.patch` exactly once; current source
  already contains that fix. The patch remains as an audit record, not a command
  to reapply to current HEAD.
- Before launch, bind all6 previous qualification outputs and the exact4+1
  primary prefix, including source, registration, complete payloads, failure,
  guard/device/placement, commands and request hashes. The final strengthened
  offline check passed with zero native reruns. Empty/short public-prefix and
  extra-guard negative tests fail closed.
- Import-only preflight checks both installed environments before a new process.
  Recovery uses separate requests/outputs/guards under `recovery`, leaving
  `primary` and its failed receipt intact. One campaign lock and the original
  per-process device guard remain in force.

## Current evidence status

The recovery is registered and running; its first corrected CPU Flat process
passes all80 warmup/measured complete-output checks with native one-thread
control. See [launch and first-pass binding](evidence/STATIC_RECOVERY_LAUNCH.json).
This is **not a complete ranking**. Preserve the
interruption and timestamps: the first four observations are not pretended to
have been measured continuously with the later processes. Shared-CPU and
fixed-observed-query limitations still apply.

`static_results.py` now combines only the bound four-row original prefix and a
COMPLETE68-row recovery. It requires all72 valid entries in original order,
retains the failed attempt separately, and uses the frozen paired estimator.
The full completed-matrix real-evidence path remains pending; compilation,
dependency checks, retained-prefix checks and a running driver are not a result.

Use `static_campaign.py run --stage recovery` with the original build/work,
`--qualification-source` pointing to immutable R2 and `--original-source` to
immutable R3. Other required interpreter, guard, device and NUMA arguments are
unchanged. A pre-existing recovery directory rejects another invocation; do not
start a second driver to monitor or finish this one.

GPU_TREE/MVPT remain missing comparators, the96 B context-symbol issue remains
open, and no100k/1B/10k-long expansion or manuscript publication is authorized
by this recovery. See [recovery contract](STATIC_RECOVERY.json),
[retained stopped evidence](evidence/STATIC_STOPPED.json), and
[qualification](STATIC_QUALIFICATION.md).
