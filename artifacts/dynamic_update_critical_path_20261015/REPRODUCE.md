# Reproduction and custody

## CPU-only source/validation check

From the repository root, with Python, NumPy and a C++17 compiler:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 \
  artifacts/dynamic_update_critical_path_20261015/test_protocol.py \
  --out "$NEW_EMPTY_CPU_CHECK_DIR"
```

No CUDA context, GPU setting or driver operation is used. Output directories
must not already exist. Keep a failed directory; choose a new path after a
documented fixture repair. The source test extracts the generated erase body,
executes it against a mock copy/sync interface and checks real C++ destruction
order for both TRACE modes. This does not measure GPU behavior.

## Original R1 source

`provenance/CONTRACT_R1.json` and `provenance/SCOPE_R1.md` are exact frozen
copies. Reverse `provenance/R1_SOURCE.diff` for the three changed source files;
the other original task files match `provenance/R1_SOURCE_IDENTITY.json`.
Additional checkpoint documents/helpers were written after the stop and are
not original executed sources. The complete 117-file source archive is held
outside Git with byte count and SHA-256. Dependency paths in its identity table
are repository-relative; parent artifacts remain immutable.

## Raw evidence and offline checkpoint

The original remote R1 code/work tree, inputs and output binaries remain
retained separately from the repaired offline code. `RAW_MANIFEST_R1.json`
inventories every raw work-tree file by relative name, byte count and SHA-256.
Its identity table is not a claim that large database vectors, private runtime
configuration, raw binary outputs or CUDA profiles were uploaded to Git.

The interrupted guard's read-only telemetry child outlived its controller.
Its owner/starttime/command/open-log identity was checked before stopping only
that observer. Post-stop samples in its incomplete log are never attribution
evidence. A first archive failed on this changing file and remains retained as
rejected; the separate STABLE archive was made after the log stopped. Its
hash and byte count are in the raw manifest. Original inputs/reference caches
remain in the external parent snapshot, not in this measurement-only archive.

`checkpoint_r1.py --root "$ORIGINAL_R1_ROOT" --out "$NEW_EMPTY_CHECKPOINT"`
audits the literal 84-entry ledger, frozen commands/source/binaries, all 83
passed guard records and the offline recheck identities. It never runs CUDA.
It requires the original stopped work tree and separately retained hardened
offline rechecks; these are not manufactured by this script. The interrupted
sample is explicitly excluded despite passing output-only validation.

## Not a GPU resume recipe

The current `CONTRACT.json` is the historical R1 contract. Do not run it as a
new recovery or use R1's remaining budget as implicit permission. Fresh R2
authorization/registration, source snapshot and live resource admission are
pending. Its proposed maximum is 124 starts, cumulative maximum 208 including
the 84 R1 starts. No automatic retry, replacement or foreign-process signaling
is authorized by this checkpoint.
