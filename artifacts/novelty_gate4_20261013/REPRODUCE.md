# Reproduction and privacy boundary

This artifact is a CPU diagnostic, not an optimized GPU search implementation.
Use an existing checkout containing the parent artifacts. No upstream setup
script, new dependency, hook or benchmark framework is needed. Requirements:
Python with NumPy, g++ with OpenMP, IEEE little-endian FP32/FP64. Parent software
was Python3.12.3/NumPy1.26.4/g++13.3.0.

`REPO`, `PRIVATE`, `DATA` and `GATE3_WORK` are **operator-supplied paths**, never
hardcoded credentials or machine placement. DATA is the original GIST1M binary
identified in CONTRACT.json. GATE3_WORK is the preserved parent execution root
with its hash-bound `cache/*.f64` and `inputs/A.source.json`. Full score caches
can be regenerated with the parent's ordered oracle and must match the recorded
identities; do not substitute native FP32 library scores.

```sh
cd "$REPO"
ART=artifacts/novelty_gate4_20261013
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/check_artifact.py"
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/model.py" --output "$PRIVATE/M1.json"

# No GPU is visible; fresh task-owned work directory, one bounded process only.
env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=4 \
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  timeout 1200s nice -n 10 python3 "$ART/run.py" \
  --data "$DATA" --gate3 "$GATE3_WORK" --work "$PRIVATE/cpu"
```

The runner validates shape/data/cache/source identities before compile, runs
the small fixtures and64 subset checks, then executes one fixed population
replay. Failure/timeout stops the process; preserve the new work and do not
automatically repeat it. Never change a keeper, query, stage or gate to recover.
The registered campaign does not authorize an additional population run; the
commands above describe independent reproduction, not an automatic rerun here.

Use the delivery entry point `run.py`; it rejects Python `-O`/`-OO` and nonzero
`PYTHONOPTIMIZE` before importing the frozen assertion-based checks. The measured
population used the frozen `replay.py` under ordinary, unoptimized Python. The
guard is a post-measurement entry-point hardening, not a population rerun or a
change to the measured algorithm/source identities.

The published source directory subsequently gained reports/curation helpers;
the original measurement source set is explicitly listed in SOURCE_IDENTITY.json.
The runner records all current input files for an independent reproduction.
After successful reproduction, curate reports into a **fresh outside-repository
directory**. The source inputs stay in the original checkout so their registered
hashes remain verifiable; neither delete nor replace the existing reports.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$ART/analyze.py" \
  --cpu "$PRIVATE/cpu" --m1 "$PRIVATE/M1.json" --output-dir "$PRIVATE/reports"
```

The new directory receives JSON reports only, not a copy of the input source.
Exclusive writes deliberately refuse to replace published or prior evidence.

To run the small numerical/accounting check only, compile `replay.cpp` using
the exact CONTRACT.json compiler flags into a private `replay.so`, then:

```sh
env PYTHONDONTWRITEBYTECODE=1 CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=4 \
  OPENBLAS_NUM_THREADS=1 python3 "$ART/run.py" --binary "$PRIVATE/replay.so"
```

M1 is reproducible without raw data. M2/M3 need authorized original coordinates
and parent caches. Public scalar histograms/counts and hashes support result
reanalysis, not fresh coordinate verification without those inputs. Private
per-pair bounds, full scores, crossing witnesses, codes, launch/build logs and
placement stay outside Git. Actual CPU diagnostic reads include the all-row
bound/oracle checks; logical candidate bytes are **counterfactual consumption**,
not a measurement of those diagnostic reads or its64-second wall time.
