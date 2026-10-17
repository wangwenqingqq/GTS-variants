# Reproduction and custody

## Independent CPU checks

From this directory,with non-optimized Python and NumPy:

```sh
python3 test_cpu.py --out /new/private/CPU_MODEL.json
c++ -std=c++17 -O2 -I../ownership_safe_gpu_update_20261015 test_generic.cpp -o /new/private/test_generic
/new/private/test_generic
c++ -std=c++17 -O2 -shared -fPIC oracle.cpp -o /new/private/oracle.so
python3 test_evidence.py --oracle /new/private/oracle.so
python3 test_bind.py --work /new/private/binding_fixture
python3 test_preflight.py --work /new/private/preflight_fixture
python3 trace.py --work /new/private/traces
```

Every output path must be new. No GPU is needed. Generic arbitrary-copy tests
use an entry-state snapshot,not an unsafe in-place arbitrary-copy executor.
Trace generation uses two fixed seeds and does not inspect physical plans to
select victims. W2 is identical for both seeds;do not count it as two independent
workload realizations.

## GPU study

The preparer is deliberately machine-local. It consumes a verified relocation
root containing the original registered compilation environment,immutable GIST
input,regenerated exact caches,and the frozen parent headers. It is not a new
dependency installer or a portable anonymous AE package. On another host,adapt
the compilation environment only in a new registration and requalify;never
change historical registrations or present different hardware as same-campaign
evidence. Large inputs and raw runs stay outside Git.

Create a new persistent work root with `cpu/` and `logs/`,then generate the
traces at `$WORK/cpu/traces`. Use the same reviewed source snapshot for all
stages:

```sh
python3 prepare.py --work "$WORK" --restore "$RESTORE" --gpu "$GPU" --numa "$NUMA"
# Inspect READY.json,STATIC.json,live GPU state and dependency identities first.
python3 campaign.py --work "$WORK" --stage qualification
python3 campaign.py --work "$WORK" --stage primary
python3 campaign.py --work "$WORK" --stage profile
python3 bind.py --work "$WORK"
python3 bind.py --work "$WORK" --check-seal
python3 analyze.py --work "$WORK" --out "$WORK/analysis"
python3 profile.py --work "$WORK" --out "$WORK/profile_analysis"
python3 bind.py --work "$WORK" --seal-derived
python3 export.py --work "$WORK" --restore "$RESTORE" --out "$WORK/public_data"
```

Do not run later stages after an incomplete/failed stage. Source,generated
source,binary,oracle and input identities are checked. A first failure creates
an immutable stop ledger,not an automatic retry. The maximal registered matrix
is368 target starts:96 qualification,252 primary,20 profiler. CPU preparation,
compilation and static inspection are distinct from target starts.

Timing uses one ordinary shared-GPU lock and the inherited two-sided PID/starttime
observer. No GPU settings are changed. Host-return ACKs include local plan
destruction. Primary service includes events+release,not offline exports.
Qualification,NSYS and NCU timings are never substituted for primary values.

`bind.py` independently recomputes the 338 GIST target quality checks, exact
368-job census/order, commands, guard identities, raw payload sets/digests,
source/build/input identities and dependency resolution before admitting
analysis. The original controller pinned checked-output/receipt digests at
target completion. Auxiliary guard files are additionally sealed after the
campaign, not falsely described as pre-pinned. Shared libraries and CCCL headers
have live pre-target hashes and a post-target content/ctime/resolution check;
per-process `/proc` mappings and all dynamically loaded plugins were not captured.
The closure also rejects extra physical guard/output/command/report entries and
binds every guard to the registered device and the pre-target actual GPU UUID.
`--seal-derived` independently reconstructs both analysis directories into a new
retained directory and requires byte-identical results before sealing the exact
derived inventory, analyzer source hashes and CLOSED proof identity. Curation
requires both seals; changed statistics or timelines are rejected.

The public source is not falsely labeled byte-identical to the measured source.
`evidence/SOURCE_BRIDGE.json` lists every difference. Fail-fast Python guards,
post-run closure admission, a reproduction-only receipt helper, and a deployment
label redaction do not change the generated CUDA adapter or recorded estimator.
The new receipt helper is CPU-fixture-tested; the complete public packaging
pipeline has not received an additional GPU campaign. Executed source hashes
and the private original sources are preserved separately.

## Figures

Use an already installed Matplotlib environment;do not install a new framework.
`plot.py` consumes the fixed analysis output and CPU census. `--style-root` may
point to an installed `paper_style.py`;that installation-owned helper is not
redistributed here. The script also supports its standalone print-safe style.
Figures require vector PDF/SVG,400DPI PNG,numeric CSV,and independent rendered
PDF/canvas QA. This is figure-file QA,not manuscript-page verification.

## Public versus private evidence

Public summaries contain scalar process observations,pointwise uncertainty,
logical raw-file manifests and source/binary hashes. They do not contain GIST
vectors,private host registrations,credentials,raw conversations or device
configuration. The persistent raw archive and its digest remain the source of
truth. A manifest proves identity,not public availability of a private archive.
No public full-service reproducibility beyond the stated inputs/environment is
claimed until those inputs are independently provisioned and requalified.

## Readable metric tables

`tables.py` uses public fixed process records and the exact raw pair CSVs for the
one descriptive quantile missing from the core analysis: replacement p50. It
requires exactly 252 pair members and verifies every size/SHA against the public
raw manifest before computing quantiles. The primary estimator is unchanged.
If the verified private raw archive is available, create a **new** pair-only
bundle without extracting or editing the original archive:

```sh
python3 - "$RAW_ARCHIVE" "$NEW_PAIRS_ARCHIVE" <<'PY'
import sys,tarfile
with tarfile.open(sys.argv[1],'r|gz') as src, tarfile.open(sys.argv[2],'x:gz') as dst:
    for member in src:
        if member.name.startswith('study/primary/outputs/') and member.name.endswith('.pairs.csv'):
            dst.addfile(member,src.extractfile(member))
PY
python3 tables.py --study . --pairs "$NEW_PAIRS_ARCHIVE" --out /new/private/tables
```

Every table cell is a median of six process summaries unless its heading/caption
explicitly says arithmetic mean. Service has one complete events+release total per process; ACK means average
operations within each process. The generic frozen “process means” shorthand
does not average or divide the complete service total. Operator p95 is a median of per-process p95s,
not a pooled percentile. Physical activities and NCU counters are diagnostic,
not primary latency. UNKNOWN fields are never zero-filled.

Do not append to sealed `logs/`, root-level files or checker snapshots after
closure. Leave validation stdout in the terminal or an external/new unsealed
logging directory. The retained derived-recheck directory is created only after
raw closure; changing a sealed source, input or raw file must fail admission.
