# CPU-only reproduction

Use an existing Linux Python3/NumPy and g++/OpenMP installation. No CUDA,
additional dependency,hardware setting change or foreign-process operation is
needed. Retain the repository layout for reused helpers and the pair kernel.

Provision the original GIST1M FP32 file and the32 original ordered-FP64 distance
arrays. Exact sizes and SHA256s are in CONTRACT.json;checksums are not download
links. Query IDs and radius are inherited,not selected by this experiment.
Raw paths must be outside Git and outside the execution source tree. Use fresh
output names with existing parents;all existing outputs are rejected.

```sh
export PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OMP_THREAD_LIMIT=4 OMP_MAX_ACTIVE_LEVELS=1
export OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
ART=artifacts/tree_partition_diagnosis_20261020
nice -n 10 python3 "$ART/run_study.py" \
  --data /private/GIST1M.f32bin --references /private/reference32 \
  --work /new/private/run
nice -n 10 python3 "$ART/verify_study.py" \
  --data /private/GIST1M.f32bin --references /private/reference32 \
  --run /new/private/run --out /new/private/verification
```

The controller freezes12 source identities,builds the reused pair kernel and
new construction-only center helper,passes the small synthetic qualification,
then starts exactly3 builders serially. Actual nice10 is checked. OpenMP uses
at most4 threads;BLAS is constrained to1. The first failure stops execution,
without retry or erasing completed/failed outputs. Each population process has
an1800-second ceiling. Verification starts exactly3 serial geometry replays.

After all population targets succeed,the controller seals the exact59-file
campaign into `run.ANCHORS.json` **before** postrun verification. The verifier
binds that seal,original qualification,compile/source/library identities,exact
commands,starts,exit/COMPLETE hashes and complete directory roles. It uses a
fresh O0 build and reverse pair orientation for every covering radius;node-center
query scores are checked bitwise against the retained authority. Median split
memberships,owner-based oracle and all per-query/per-level metrics are rebuilt.

The semantic verifier intentionally retains original registered source/command
paths. A relocated raw archive is useful for portable hash/scalar checks,but
rewriting registrations does not admit the original execution. Reproduction is
a fresh campaign,not a claim of timing equivalence across replaced CPUs.

Do not substitute frozen128 held-out query vectors or derive their query-specific
features. No GPU/index admission follows from any structural count here.

## Portable delivery checks

These do not read private data or frozen held-out queries and do not replace
the full geometry replay above:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/check_public.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/check_public.py" --archive /private/RAW_R1.tgz
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/test_public.py" --out /new/private/delivery_tests
```

The optional archive check verifies all164 original members. The last command
keeps six deliberately altered delivery copies in a new directory outside the
source tree,refreshes publish hashes for five of them,and requires all to fail
the portable gate. It never changes the preserved originals.
