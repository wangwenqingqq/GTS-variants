# Static ANNS dataset characterization

This experiment describes the stored SIFT-1M, Deep-1M, GIST-1M, Word, and T-loc
1M datasets. It is not a search-system benchmark or a new algorithm claim.
See `CONTRACT.md` for the definitions frozen before measurement and `RESULTS.md`
for the complete outcome. Native distances are unchanged: Euclidean distance
for numeric inputs, and unit-cost Levenshtein distance for original strings.

## Reproduce

Use Python 3.12. The profiling run used NumPy 1.26.4, SciPy 1.14.1 and RapidFuzz
3.14.1. Plotting additionally requires Matplotlib; the retained rendering used
3.11.2. Install in an isolated environment rather than changing shared runtimes.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install numpy==1.26.4 scipy==1.14.1 rapidfuzz==3.14.1 matplotlib==3.11.2
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
.venv/bin/python validate_results.py
.venv/bin/python profile_datasets.py --root "$ANNS_DATA_ROOT" --out runs/new_run
.venv/bin/python validate_results.py --run runs/new_run
.venv/bin/python summarize.py runs/new_run --out rendered
```

The run directory must not already exist. `--datasets` supports bounded
single-dataset reruns, but the complete-run validator requires all five datasets.
No source file is rewritten. A failed run preserves its error and completed
dataset records. On shared systems, use a low-priority CPU job; no GPU is needed.

## Input layout

```text
$ANNS_DATA_ROOT/
  sift1m/sift_base.fvecs, sift_query.fvecs
  deep1m/deep1M_base.fvecs, deep1M_queries.fvecs
  gist1m/gist_base.fvecs, gist_query.fvecs
  word/word.txt, word_qid.txt
  T-loc/1_million_location_gts.txt, tloc_1m_qid.txt
```

Exact input hashes appear in the result records. Sources and libraries require
their respective licenses; no raw dataset objects are distributed here.

## Evidence and limits

- Elementary numeric statistics scan all stored values. Word and T-loc duplicate
  fractions are full-data counts; vector duplicate fractions use 50,000 objects.
- Geometry uses exact distances to 50,000 sampled references, not the full 1M
  corpus. Each of three seeds draws 512 disjoint held-out base queries. Native
  queries are an additional workload, not pooled into the uniform estimates.
- Per-run NPZ files retain sample indices and per-query metrics. A portable
  hash/size manifest identifies the raw evidence; small JSON summaries and
  validation records are included. Host-identifying metadata stays outside the
  public bundle. Sampling is reproducible from seeds and input hashes.
- There is no verified time axis. Row-order adjacency, ACF and spectral peaks are
  explicitly not claims of temporal periodicity. Request-arrival burstiness is
  not estimable without arrival records. Feature-index FFT is not performed.
- The fixture validation includes a streaming-boundary check and independent
  direct-distance checks. The full validator checks all five result sets,
  sample disjointness, statistics against per-query evidence, and metric bounds.
- This analysis does not measure pruning rates, execution speedups, model quality,
  or establish a causal explanation of a retrieval system's performance.
