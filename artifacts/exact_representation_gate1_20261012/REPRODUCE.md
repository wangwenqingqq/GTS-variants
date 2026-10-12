# Reproduction and evidence boundary

Use Python>=3.11, installed NumPy and a GCC-compatible CPU C++ compiler. No CUDA,
GPU profiler, new dependency or framework is required. The frozen build command
is in CONTRACT.json. One low-priority CPU worker is used.

Provide the privately retained non-padded B1 parent work directory, containing
REGISTERED.json and the original data/reference paths. The public parent
INPUT_IDENTITY.json must remain available in its repository location. The
runner verifies the complete3.84GB file hash,12-byte(D,N,metric) header, all32
reference hashes, original query order and exact radius before creating a new
private work directory. It refuses to overwrite an existing run.

```sh
PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  nice -n 10 python3 artifacts/exact_representation_gate1_20261012/run.py \
  --parent "$NON_PADDED_PARENT_WORK" --work "$NEW_PRIVATE_GATE1_WORK"
```

The CPU library is numerically qualified with duplicate, zero-distance,
inclusive/exact/adjacent-boundary, early/last-coordinate and nonfinite fixtures.
All32 original queries over the first4096 rows then pass bit and safe-crossing
checks before full-population execution. These qualification rows do not replace
any primary pair: the primary covers all32×1M pairs, in original query order.

The runner retains source/build/input hashes, registration, start, per-query
progress, full scores and per-pair required dimensions in private evidence. It
stops on the first failure, preserving completed output and failure records; it
never repeats a failed primary run automatically. Existing GPU processes and
settings are untouched; total GPU starts must remain0.

Public delivery contains only owned source, aggregated integer histograms,
scalar quality/hash receipts and plots. Full vectors, all per-pair dimensions,
ordered score arrays, complete result payloads, compiler binaries/logs and
deployment placement remain outside Git. The confidential manuscript is not
modified or uploaded.
