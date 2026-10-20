# Reproduce Gate 1A without exposing held-out outcomes

Existing Python3, NumPy and a C++17 compiler are sufficient. Install nothing.
Use the repository layout because inherited trace preparation refers to its
parent contract and manifest. All output parents must exist; all output names
must be fresh. An existing output is rejected, never replaced.

From this directory, public checks require no dataset:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 gate1a.py check-protocol
PYTHONDONTWRITEBYTECODE=1 python3 test_gate1a.py
PYTHONDONTWRITEBYTECODE=1 python3 check_public.py
```

The **one-command replay** needs the privately retained original snapshot and
Gate0's PDX parent raw trace. It never evaluates a new query:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  nice -n 10 python3 gate1a.py replay \
  --data /private/GIST1M.f32bin \
  --parent-raw /private/pdx_parent_raw \
  --out /new/private/gate1a_run
```

The dataset must be exactly 3,840,000,012 bytes with SHA256
`f371099f42fea105bed573c67bbfd5b522743220873cf68aa900eb6c44b388e7`.
It is hashed before and after extraction. The private query payload is exactly
491,520 bytes:128 rows of960 little-endian FP32 values. Its public manifest
contains per-vector hashes, IDs and radius bits; vectors are not redistributed.
Identity duplicates stop rather than triggering an outcome-dependent redraw.

Development replay rebuilds the existing solver, repeats its synthetic
qualification, regenerates all28 inputs and outputs, and checks every output
CSV byte-for-byte against Gate0. It checks all317,807 distinct weighted contexts
and all125,000 sectors per batch, not a sampled subset. It uses at most4 CPU
workers at actual nice10, preserves logs, stops on the first failure and never
automatically retries. B8 retains the old4096/context and2M/batch oracle caps.

For execution consistency rechecking, without rerunning population targets:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 gate1a.py verify-run \
  --work /private/gate1a_run
```

This self-check alone is **not sealed execution admission**. The independent
`check_evidence.py` additionally requires the first450-file raw census, exact
original commands/logs, all qualification fixtures, the complete8-source set,
and byte equality of128 rows with the original hash-bound database. It rebuilds
the identical binary and recomputes every development context without rerunning
population searches:

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  nice -n 10 python3 check_evidence.py \
  --work /private/original_task_root --data /private/GIST1M.f32bin \
  --anchors evidence/RAW_ANCHORS.json --out /new/private/closure
PYTHONDONTWRITEBYTECODE=1 nice -n 10 python3 test_evidence.py \
  --work /private/original_task_root --anchors evidence/RAW_ANCHORS.json \
  --out /new/private/tamper_checks
```

This independent checker intentionally binds the original task-root command paths,
not a relocated archive with rewritten registrations. Its eight counterfactual
mutation tests run on copies, never on sealed originals. `check_public.py` is the
portable hash/scalar check; it is not independent vector execution admission.

Run bindings retain private original command paths, logs and host registrations.
Public results expose only portable scalars and hashes. A fresh replay is a new
CPU execution, not proof that another CPU has the old CPU's timing. Scheduler
execution time is not measured here; old32 wall times are resource diagnostics.

Do not derive held-out zone order, first crossings, context keys or oracle paths
in an attempt to "prepare" Gate1B. Those are held-out features/outcomes and require
the later implementation freeze and exclusive Gate1C start ticket. No public
download URL is implied by a checksum; provision authorized original inputs.
