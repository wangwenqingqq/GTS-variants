# Reproduce without a GPU

Use existing Python3/NumPy and a C++17 compiler; install nothing. From this artifact:

```sh
c++ -std=c++17 -O2 -Wall -Wextra -pedantic solver.cpp -o /new/private/solver
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 test_solver.py \
  --binary /new/private/solver --out /new/private/fixtures
```

All output paths must be fresh and their parents must exist. Fixtures are public
synthetic programs, not another measurement of real vectors. Optimized Python
is deliberately rejected. No CUDA dependency is used.

## Full structure and CPU scheduling

Provision the privately retained parent RAW_R1 containing RESULTS.json and64
safe/order arrays. They must match the parent public manifest and recovery
INPUT_IDENTITY.cpu_results_sha256. A checksum is identity,not a public download.
No original vectors need be downloaded or read for this trace study.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python3 prepare.py \
  --parent-raw /private/parent_raw --out /new/private/inputs
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  nice -n 10 python3 run_cpu.py --inputs /new/private/inputs --work /new/private/campaign
python3 analyze.py --inputs /new/private/inputs \
  --runs /new/private/campaign --out /new/private/analysis
```

The last two commands are a fresh campaign, not an admission of the old campaign.
On a shell already running with a nonzero niceness, arrange actual nice10 for
that task; the driver checks actual priority and does not change host settings.
The source and parent references must be provisioned with the repository layout.
The controller executes28 combinatorial population processes at most4 at once,
not28 timings of a query engine. Wall times are resource diagnostics only.

## Historical full execution closure

`verify.py --work <original_work_root> --out <new_postrun_output>` binds the
historical518-file raw census, sources/build/qualification/start ledger, exact
commands, logs, exits and hashes, then regenerates all inputs/statistics and
recompiles the binary identically. Its current-source identities must match the
recorded checker references. It runs only tiny synthetic qualification checks,
not another population search or GPU target.

**This checker is intentionally bound to the original absolute registered command
paths and GCC environment.** Extracting the archive elsewhere and substituting
paths does not admit old measurements and is expected to fail. The exact original
checker snapshot/proof are retained privately. A fresh portable reproduction is
separate from historical-path admission.

## Public versus private evidence

Git contains task-owned CPU code, contract, source-model tables/scalars and hashes.
Raw per-sector traces, original safe/order arrays, binaries, hostname-bearing
registration and private command paths remain outside Git. The private archive
contains532 exact members:518 raw observations,13 actual checker files and proof.
All member sizes/SHA256s are checked on the execution host and independently
locally. No manuscript or prior campaign is edited.

No physical DRAM, cache, GPU state traffic, output latency, update ACK, batching
window, recipe lookup cost or SLA is measured. The modeled transposed database
is not a newly built persistent vector index. No performance plot is fabricated;
readable tables expose the source-model quantities directly.
