# Repaired GTS versus strong baselines

**Measured: R improves serial original A, but loses to native-batch exact scan
on all17 quality-valid workloads. One of18 workloads fails frozen exact IDs.**
Native Kokkos/ArborX was built and measured; low-dimensional results are mixed.
This is not an all-gates pass or a universal conclusion about metric trees.

- [Main18-row table, intervals, work counts and decision](REPORT.md)
- [Frozen contract](CONTRACT.md), [append-only amendments](AMENDMENTS.md)
- [Results and all process summaries](RESULTS.json), [raw samples](evidence/measured_20261025/raw_samples.csv)
- [Measured evidence](evidence/measured_20261025), [implementation card](DESIGN.md)
- [Experiment / claim ledger](EXPERIMENTS.md)

The original a9bc1c7 admission/no-Kokkos checkpoint records remain in `evidence/`.
They are historical. Current data are under `evidence/measured_20261025/`; no
old latency samples are reused. All task changes stay in this new directory.

## CPU-only verification of published measurements

From this directory, with Python3 and a C++17 host compiler:

```sh
python3 test_cpu.py
python3 test_campaign_v4.py
python3 test_analysis.py       # explicitly synthetic estimator regression only
python3 verify_evidence.py     # independent check of real published observations
```

The last command checks one GPU, 360 timed fresh processes, 1080 retained bundles,
six matched pairs, balanced relative orders, log-t confidence intervals, source
output hashes, 42 bounded sanitizer runs, 63 count runs and frozen input hashes.
The full retained binary outputs are external; their hashes are published.
`audit_full_outputs.py` rechecks every query, including beyond the first failing
query, against those external CPU/native files without GPU execution. Its result
is retained as `evidence/measured_20261025/FULL_OUTPUT_CPU_AUDIT.json`.

## Reproduce with the frozen inputs (do not recalibrate)

Use fresh scratch on the authorized Linux GPU host. No script downloads private
input data. Provide the exact Words/Tloc fixtures in CONTRACT.md and frozen
oracle files, or regenerate only the oracles using the frozen query IDs/radii.
The recorded compiler was GNU13.3, CUDA13.1.115 / sm120. Original GTS is from
[ZJU-DAILY/GTS at3bac1b7](https://github.com/ZJU-DAILY/GTS/tree/3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639/Source%20Code/GTS),
not this backup repository's modified top-level source. Provide its `include/`
and `src/` as `$ORIGINAL_GTS`; `prepare_cuda.py` verifies all eight SHA256 pins.

Set `$SCRATCH` to a new task-owned directory and `$WORDS` / `$TLOC_F32BIN` /
`$WORDS_ORACLE` / `$TLOC_ORACLE` to retained fixture paths:

```sh
mkdir "$SCRATCH"
mkdir "$SCRATCH/fixtures" "$SCRATCH/bin" "$SCRATCH/logs" "$SCRATCH/runs"
cp "$WORDS" "$SCRATCH/fixtures/words.txt"
cp "$TLOC_F32BIN" "$SCRATCH/fixtures/tloc.f32bin"
cp evidence/calibration.json evidence/*.cal.json evidence/*.cal.qid \
   evidence/*.test.qid "$SCRATCH/fixtures/"
cp "$WORDS_ORACLE" "$SCRATCH/fixtures/words.oracle"
cp "$TLOC_ORACLE" "$SCRATCH/fixtures/tloc.oracle"
cp evidence/CPU_ORACLE.json "$SCRATCH/FROZEN_CPU_ORACLE.json"
c++ -std=c++17 -O3 -pthread oracle.cpp -o "$SCRATCH/bin/oracle"
```

If complete oracles are unavailable, omit their two `cp` commands and generate
from the **frozen** calibration file, not `fixtures.py freeze` or test results:

```sh
python3 - "$SCRATCH" <<'PY'
import json,subprocess,sys
from pathlib import Path
p=Path(sys.argv[1]).resolve()
for name,v in json.loads((p/'fixtures/calibration.json').read_text())['datasets'].items():
    data='words.txt' if name=='words' else 'tloc.f32bin'
    subprocess.run([str(p/'bin/oracle'),'test',name,str(p/'fixtures'/data),
                    str(p/f'fixtures/{name}.test.qid'),str(p/f'fixtures/{name}.oracle'),
                    *map(str,v['radii'])],check=True)
PY
```

Verify **every** frozen input before building/running (also enforced by the
campaign); no regenerated radius or changed oracle is accepted:

```sh
python3 - "$SCRATCH" <<'PY'
import hashlib,json,sys
from pathlib import Path
p=Path(sys.argv[1])
m=json.loads((p/'FROZEN_CPU_ORACLE.json').read_text())
for name,v in m['files'].items():
    if not name.startswith('fixtures/'):continue
    h=hashlib.sha256()
    with (p/name).open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    assert h.hexdigest()==v['sha256'],name
assert hashlib.sha256((p/'fixtures/calibration.json').read_bytes()).hexdigest()==m['calibration_sha256']
print('PASS frozen fixtures')
PY
```

## Builds, admission, gates and six rounds

Compile-only commands do not execute GPU queries. `build_native.sh` clones exact
Kokkos/ArborX commits and installs only in `$SCRATCH/deps/install`, never system
locations. It requires internet to fetch those primary-source dependencies, an
available GNU compiler/CMake/CUDA toolkit, and user write permission.

```sh
bash build_cuda.sh "$SCRATCH" "$ORIGINAL_GTS"
bash build_native.sh "$SCRATCH"
python3 make_bounded.py "$SCRATCH"
cp campaign_quality_support_v4.py quality_campaign_v4.py "$SCRATCH/"
```

`quality_campaign_v4.py` is the **measured entry point**. The support module is
hash-pinned as measured, including its older unused diagnostic entry point;
do not use that entry point to substitute for the quality-aware campaign.
The active controller needs Linux `pidfd_open` / `pidfd_send_signal` and
`compute-sanitizer`. It uses the existing per-device lock namespace
`/tmp/gtspp_gpu{index}.lock` plus `$SCRATCH/campaign.lock`. Those shared advisory
lock files must already be provisioned with appropriate user access; do not
silently create a different lock namespace and race another campaign.

Eligible physical cards are0/1/4/5/6/7 (initial preference5). All arms use one
admitted UUID for a complete epoch. No compute applications, utilization0% and
memory<=256MiB are required before launch; polling continues through execution.
Foreign activity invalidates/retains the entire epoch and restarts all six
rounds after a fresh admission, not a replacement observation. No foreign
process is signaled and no GPU settings are changed. Process identity and
pidfd-bound signaling prevent an ordinary stale/reused PID from being killed.

```sh
python3 "$SCRATCH/quality_campaign_v4.py" "$SCRATCH" \
  > "$SCRATCH/logs/quality_campaign.log" 2>&1
EPOCH=$(cat "$SCRATCH/logs/active_epoch.txt")
python3 analyze_campaign.py "$EPOCH" "$SCRATCH/analyzed"
python3 audit_full_outputs.py "$SCRATCH" "$EPOCH" "$SCRATCH/full_output_audit.json"
```

The full/gates/count phases are run fresh in the same epoch before formal time.
Output failure excludes that arm from timing, remains explicit in all18 rows,
and blocks full-matrix acceptance. No automatic radius adjustment, precision
adapter or post-hoc tolerance relaxation exists. The standalone full-output
CPU audit currently asserts the **recorded** 60pass/3shared-boundary-failure
outcome; a different result requires investigation, not editing a receipt.

`collect_evidence.py` curates this retained campaign's paths/logs/hashes for
publication; it is a measured-layout curator, not a general data downloader or
license to publish restricted raw inputs. Generated sources and binary hashes
are compiler/path sensitive; numerical outputs and frozen fixture hashes are
separately bound. All reproduced GPU observations must come from a new idle,
locked complete campaign, never be mixed into the published epoch.

## Important limits

A/R are serial bundles, not demonstrated native Q1024 GTS throughput; R/A is not
against the old author-V2 Q32≈237ms path. One frozen Tloc boundary fails strict
ID equality. Sanitizers use bounded N2000 fixtures, not full-data memcheck.
Native ArborX's comparable active-thread denominator is unavailable and stays
null. Deep1M, per-fix attribution, profiler decomposition and controlled-clock
experiments were not run. No source/evidence overwrite or main merge occurred.
