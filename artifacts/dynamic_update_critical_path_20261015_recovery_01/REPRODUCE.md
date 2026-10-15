# Reproduction and evidence custody

## Public CPU-only verification (no GPU starts)

Use ordinary Python3 (not `-O` or `PYTHONOPTIMIZE`) with NumPy. From the repository
root, choose a new output directory **outside this artifact**:

```sh
export PYTHONDONTWRITEBYTECODE=1
A=artifacts/dynamic_update_critical_path_20261015_recovery_01
python3 "$A/verify.py" --out "$OUTPUT_DIR"
python3 "$A/test_protocol.py" --out "$CPU_TEST_DIR"
```

`verify.py` checks the exact public whitelist/hashes, immutable31-file stopped
checkpoint and73-file parent artifact (plus both G4 records), executed source
identities, generated adapter, selected-search SASS receipts, all124 quality/guard
bindings and source-derived job census. It reconstructs all84 primary-process
statistics, the12 native service ledgers,11 normalized trace tables and all
reported derived values. It also runs19 negative phase/API/per-ACK evidence
tests. Search output membership, original NSYS parsing, final vectors and
SASS extraction are **not** reexecuted by public scalar verification.

`test_protocol.py` compiles only a CPU replay helper with an available C++17
compiler:27 replay cases,27 corrupt-witness rejections,14 field/accounting
negatives, native-source roundtrip, delete-lifetime checks in both TRACE modes
and owned guard/observer cleanup under controlled PID/group SIGINT. It is not
a proof of cleanup after arbitrary SIGKILL or machine failure.

For figures, use the same Python environment with Matplotlib installed:

```sh
python3 "$A/verify.py" --out "$PLOT_VERIFY_DIR" --plot
# Or regenerate only figures in a new directory:
python3 "$A/plot.py" --data "$A" --out "$FIGURE_OUTPUT_DIR"
```

The figure script uses standard Matplotlib, no runtime/system skill files.
Numeric CSVs must match exactly. PDF/PNG/SVG metadata and fonts can vary across
Matplotlib/font versions; compare numerical content rather than binary figures.
Final rendering used Python3.13.12, NumPy2.4.3, Matplotlib3.11.0; measurement-side
curation used Python3.12.3/NumPy1.26.4. Public aggregate checks allow1e-12 floating
roundoff across these environments, **not looser search correctness**.

## Author-side immutable raw replay (no GPU re-execution)

Raw custody and the2,953 measured-work file hashes are in
`evidence/RAW_CUSTODY.json` and `evidence/RAW_MANIFEST.json`. The private stable
archive includes original executed source snapshots, raw outputs, isolation
receipts, all11 .nsys-rep/SQLite captures, and retained failed/CPU-only revisions.
Its SHA256 is
`b6d660721a035d1b8c49b2d9719cd7f9324101670e561f703e8ea3a05133f75d`
and size537,999,414 bytes. Every measured-work payload was rehashed after local
transfer; none is being inferred solely from a tar exit status. Parent data,
reference files and binaries remain separately input-hash-bound.

For the historical raw check, restore the **original executed source snapshot**
at its registered layout and add the hardened offline helpers identified by
`evidence/POSTPROCESSING.json`. Preserve the original documentation for the
strict historical source check: `PUBLIC_SOURCE_BRIDGE.json` explains the one
public-only placement phrase redaction. Do not substitute a public redacted
scope file and claim it is byte-identical to the executed snapshot.

```sh
python3 "$OFFLINE_SOURCE/curate.py" --work "$MEASURED_WORK"   --refused-record "$PRESERVED_REFUSAL_RECORD" --out "$NEW_CURATED_DIR"
python3 "$OFFLINE_SOURCE/derive.py" --curated "$NEW_CURATED_DIR"   --work "$MEASURED_WORK" --out "$NEW_DERIVED_DIR"
python3 "$OFFLINE_SOURCE/test_evidence.py" --trace "$IMMUTABLE_INSERT_TRACE"
```

This was completed after measurement: all124 output checks passed again; exact
inner phase multisets and chronological mutation-derived API/byte counts passed.
The last command also removes/duplicates an inner phase **in memory** and checks
rejection against a real hash-bound trace, without modifying the database.
All original NSYS warnings remain present and disclosed.

## Fresh GPU replay is a new campaign, not a retry

**Do not run this automatically.** The209-start authorization is exhausted.
A future replay requires a fresh resource check/registration and explicit launch
budget. Author dependencies are the immutable parent raw inputs/references and
S1/frozen-PDX binaries from parent commit
`d4e196f38aa8242e547e3dea3d9311650bb9ef10`; public hashes alone do not supply
restricted/large data. Keep data outside Git. Choose an actually idle same-model
single GPU and its NUMA node, inspect active users/processes, and never signal
foreign processes or change GPU settings.

The preserved preparation interface is:

```sh
python3 "$A/prepare.py" --parent "$PARENT_RAW" --work "$FRESH_WORK"   --gpu "$GPU" --numa "$NUMA_NODE"
```

It records generated sources, full build commands, binary/library hashes and
selected-kernel SASS/resources without starting CUDA targets. The staged runner
is `campaign.py --work "$FRESH_WORK" --stage qualification|primary|timeline`, in
that order; first failure stops, no automatic replacement. Its Nsight command
and every source-derived target command are hashed in the raw ledger. A public
rebuild registers current source bytes, not the historical physical placement.

NSYS2025.5.2 traces CUDA/NVTX/OSRT, disables CPU sampling/context switches and
CUDA-event trace, uses gb20x GPU metrics at10kHz and cudaProfilerApi capture.
Profiling requires suitable privileges already supplied by the owner; no host
permission or hardware settings are changed by this artifact. Primary ACKs
are separate no-profiler processes, never substituted by diagnostic times.
