# Claim–evidence ledger

Experiment: `anns_20260922_characterization_native_metric_v1`.
All claims are descriptive; no algorithm or performance promotion is made.

| ID | Claim | State | Scope and denominator | Evidence | Caveat / allowed wording |
|---|---|---|---|---|---|
| C1 | SIFT has 22.991971% exactly-zero coordinates, Deep 0%, and GIST 0.00353625%. | measured | All coordinates in each stored 1M base file; no normalization | Per-dataset `results/*.json`, `full.zero_fraction`; input SHA-256 and full-scan validation | Exact zeros, not threshold sparsity. Does not describe strings or geographic density. |
| C2 | Median seed-level LID50 medians are 20.317 (SIFT), 19.986 (Deep), 41.044 (GIST), and 2.018 (T-loc). | partial | Three 50,000-reference / 512-held-out-query samples; exact distances within each sample | `geometry_runs`; per-query NPZ hashes in raw manifest | Sampled local geometry, not full-corpus LID or a latency prediction. Invalid zero-distance cases are counted, not dequantized. |
| C3 | Word row order is nearly lexicographic; T-loc has very strong adjacent-row locality. | measured | Word: all 611,755 adjacent pairs. T-loc: all 999,999 adjacent pairs versus 20,000 random distinct-index pairs | `Word.json` full lexical statistic; `T-loc-1M.json` row-order ratio | Word nondecreasing fraction 99.9998%; T-loc distance-median ratio 0.0076. This is file order, not time. |
| C4 | Word/T-loc native query-ID files enumerate 0–999; T-loc's native query sample differs from uniform base samples under the registered MMD check. | measured | 512 native queries and 512 random base objects, fixed RBF bandwidth, 99 label permutations | `native_id_range`, query file hashes, `native_query_mmd` | Exploratory p=0.01 at the available permutation resolution. Prefix selection is not uniform; no population-level cause inferred. |
| C5 | Temporal periodicity or request burstiness exists/does not exist in these datasets. | unknown | No timestamps, verified time axis or arrival trace supplied | No evidence | Neither presence nor absence is established. ACF/spectral diagnostics are restricted to stored row order. |
| C6 | T-loc's global variance is mostly one-directional although local estimated dimension is near two. | partial | PCA on 10,000 uniformly sampled rows; local geometry under C2 | `covariance_sample.pc1_share` = 0.9640016821; LID50 distribution | Global covariance concentration and local neighbor-distance growth measure different properties. |
| C7 | A dataset feature causes a pruning, latency or throughput advantage. | unknown | No retrieval-system performance measurements | No evidence | No speedup, causal mechanism, or algorithm superiority claim is permitted. |

## Negative and limiting evidence

- Word edit-distance discreteness gives a zero median top-10 relative gap and
  unit median r20/r10 in all three seeds. A continuous LID estimate is therefore
  deliberately not reported. Reopen only with a justified discrete-space method.
- Deep norm SD is about 3.28e-8 around a mean of one. Norm-series spectra mainly
  characterize tiny normalization residuals; do not interpret them as semantic
  vector dynamics. Reopen with a meaningful observed signal and an explicit axis.
- The existing Word/T-loc prefix query workloads do not provide random-query
  coverage. Keep these results separate from the uniform-query characterization.
- Five-dataset validation passed; characterization does not satisfy GPU
  correctness, sanitizer, stress, sustained-workload or end-to-end timing gates,
  which are not applicable to this CPU-only descriptive experiment.
