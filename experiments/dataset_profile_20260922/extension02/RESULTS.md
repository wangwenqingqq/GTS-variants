# Extended dataset comparison

**Coverage: 9/9 requested datasets measured and validated.**
All neighborhood comparisons use 20,000 sampled references, 512 disjoint uniform base queries, and three fixed seeds. Distances are exact within the sample, not the full corpus. The original 50,000-reference experiment remains separate and unchanged.

## Matched comparison

| Dataset | N | Representation | Distance | Exact zeros (%) | Hoyer mean | LID50* | RC10* |
|---|---:|---|---|---:|---:|---:|---:|
| SIFT-1M | 1,000,000 | 128 | Euclidean | 22.9920 | 0.447 | 19.109 | 2.070 |
| Deep-1M | 1,000,000 | 96 | Euclidean | 0.0000 | 0.223 | 18.614 | 1.708 |
| GIST-1M | 1,000,000 | 960 | Euclidean | 0.0035 | 0.146 | 37.603 | 1.685 |
| Word | 611,756 | 1–32 chars | Levenshtein | N/A | N/A | N/A | 2.257 |
| T-loc-1M | 1,000,000 | 2 | Euclidean | N/A | N/A | 1.989 | 246.425 |
| T-loc-10M | 10,000,000 | 2 | Euclidean | N/A | N/A | 1.981 | 241.512 |
| Vector-200K | 200,000 | 300 | Angular-degrees | 0.0002 | 0.214 | 22.707 | 1.366 |
| Protein | 52,799 | 30–100 chars | Levenshtein | N/A | N/A | N/A | 4.432 |
| ChEMBL | 50,000 | 2048 | Tanimoto | 97.6499 | 0.868 | N/A | 1.539 |

*RC10 is the median across seeds of the per-query mean RC10; LID50 is the median across seeds of the per-query median LID50. Spatial coordinate zeros and string alphabets are not coordinate sparsity. LID is omitted for discrete strings and binary fingerprints.

## Sequence and fingerprint descriptors

| Dataset | Mean sequence length | Symbols | Symbol entropy (bits) | Bigram entropy (bits) | Trigram entropy (bits) | Full duplicate fraction (%) |
|---|---:|---:|---:|---:|---:|---:|
| Word | 10.314 | 77 | 4.464 | 8.188 | 11.558 | 0.00016 |
| Protein | 73.492 | 24 | 4.176 | 8.318 | 12.393 | 24.94176 |

Duplicate fraction is 1 − unique-object count / row count: excess copies, not all rows belonging to a repeated group.

ChEMBL: mean active bits 48.130 / 2048; P10/P50/P90 = 30/46/67. Mean per-bit marginal entropy 0.1229 bits; constant bits 0; empty fingerprints 0; full duplicate-fingerprint fraction 3.72600%.
Identical fingerprints do not prove identical molecules. Sequence symbol/gram entropy and per-bit marginal entropy describe different representations; neither is temporal entropy.

## Order sensitivity, abruptness, and representation dimension

| Dataset | Adjacent/random median | Excess steps (%) | PCA95 | Effective rank | Expansion10* | Hub top-1% share (%) |
|---|---:|---:|---:|---:|---:|---:|
| SIFT-1M | 0.89792 | 0.00000 | 72 | 27.755 | 1.038 | 4.966 |
| Deep-1M | 1.00087 | 0.00000 | 77 | 64.618 | 1.038 | 3.882 |
| GIST-1M | 0.95599 | 0.17520 | 291 | 77.631 | 1.019 | 10.386 |
| Word | 0.40000 | 0.08451 | N/A | N/A | 1.000 | 3.949 |
| T-loc-1M | 0.00762 | 0.05150 | 1 | 1.168 | 1.429 | 1.963 |
| T-loc-10M | 0.00774 | 0.00519 | 1 | 1.166 | 1.431 | 2.036 |
| Vector-200K | 0.99725 | 0.00000 | 265 | 237.239 | 1.030 | 5.059 |
| Protein | 0.40000 | 0.00000† | N/A | N/A | 1.059 | 5.584 |
| ChEMBL | 0.98616 | 0.00000† | 1258 | 619.464 | 1.076 | 4.317 |

Adjacent distances cover every neighboring row; the random comparison uses 20,000 distinct-index pairs. Excess steps exceed median + 6 × 1.4826 × MAD (N/A for zero MAD): a descriptive heuristic, not an anomaly test. Expansion is median r20/r10. PCA uses 10,000 stored-coordinate rows, not standardized features. Binary/Angular PCA is a representation diagnostic, not native-metric intrinsic dimension. Hubness uses 2,048 objects and fractional ties.

† The registered robust threshold reaches or exceeds the metric upper bound, so a zero exceedance rate is uninformative about abruptness, not evidence of smoothness. Thresholds and quantiles are retained below; no post-hoc threshold replacement is made.

| Dataset | Adjacent P50 | Adjacent P95 | Adjacent P99 | Robust threshold |
|---|---:|---:|---:|---:|
| SIFT-1M | 504.449 | 657.571 | 684.163 | 1249.491 |
| Deep-1M | 1.381 | 1.504 | 1.544 | 1.964 |
| GIST-1M | 1.791 | 2.767 | 3.501 | 4.264 |
| Word | 4.000 | 10.000 | 15.000 | 21.791 |
| T-loc-1M | 0.513 | 0.941 | 1.091 | 2.191 |
| T-loc-10M | 0.512 | 0.938 | 1.079 | 2.184 |
| Vector-200K | 86.715 | 92.257 | 94.390 | 109.228 |
| Protein | 28.000 | 76.000 | 82.000 | 250.390 |
| ChEMBL | 0.886 | 0.951 | 0.976 | 1.203 |

Adjacent quantiles use each dataset's native distance units, not a common physical scale. For Protein, distance cannot exceed the longest stored sequence (100); for binary Tanimoto it cannot exceed 1. These bounds explain their flagged zero exceedance rates.

## Sampling sensitivity and native-query workload

| Dataset | RC10 seed range | LID50 seed range | Invalid LID50 / 512 by seed | Native queries | Native RC10 mean |
|---|---:|---:|---|---:|---:|
| SIFT-1M | 2.055–2.097 | 18.955–19.201 | 0/1/0 | 512 | 2.084 |
| Deep-1M | 1.679–1.708 | 18.484–18.974 | 0/0/0 | 512 | 1.711 |
| GIST-1M | 1.639–1.690 | 37.094–38.179 | 0/0/0 | 512 | 1.631 |
| Word | 2.192–2.284 | N/A | N/A | 512 | 2.550 |
| T-loc-1M | 239.341–251.002 | 1.980–1.990 | 0/0/0 | 512 | 119.888 |
| T-loc-10M | 237.597–242.184 | 1.975–1.986 | 0/0/0 | 512 | 78.282 |
| Vector-200K | 1.351–1.367 | 21.973–23.186 | 0/0/0 | 100 | 1.345 |
| Protein | 4.282–4.552 | N/A | N/A | 512 | 4.083 |
| ChEMBL | 1.513–1.548 | N/A | N/A | 512 | 1.520 |

Seed ranges are observed sampling sensitivity, not confidence intervals. Native query comparisons exclude matching base IDs. Vector provides only 100 query IDs and is not silently expanded to 512. Native workloads need not represent uniform base queries.

| Dataset | Zero-nearest queries (%) by seed | Invalid RC10 / 512 by seed |
|---|---|---|
| SIFT-1M | 0.000 / 0.195 / 0.000 | 0 / 0 / 0 |
| Deep-1M | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| GIST-1M | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| Word | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| T-loc-1M | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| T-loc-10M | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| Vector-200K | 0.000 / 0.000 / 0.000 | 0 / 0 / 0 |
| Protein | 21.875 / 22.656 / 25.195 | 17 / 11 / 20 |
| ChEMBL | 3.125 / 4.102 / 3.516 | 0 / 0 / 0 |

Zero-distance and invalid-radius cases are retained, not stabilized by an epsilon. RC summaries use valid queries only.

## File-order correlations, not temporal periodicity

| Dataset / scalar | Median ACF1 | Shuffled ACF1 | Median dominant-bin power share |
|---|---:|---:|---:|
| SIFT-1M / l2_norm | 0.1085 | 0.0029 | 0.0063 |
| Deep-1M / l2_norm | -0.0016 | 0.0008 | 0.0023 |
| GIST-1M / l2_norm | 0.1360 | -0.0026 | 0.0044 |
| Word / length | 0.5242 | 0.0025 | 0.0224 |
| T-loc-1M / coordinate_0 | 0.4479 | -0.0047 | 0.1834 |
| T-loc-1M / coordinate_1 | 0.9975 | 0.0004 | 0.2655 |
| T-loc-10M / coordinate_0 | 0.0131 | 0.0089 | 0.0024 |
| T-loc-10M / coordinate_1 | 0.7221 | -0.0028 | 0.2066 |
| Vector-200K / l2_norm | 0.0105 | 0.0029 | 0.0020 |
| Protein / length | 0.7369 | -0.0063 | 0.0879 |
| ChEMBL / active_bits | 0.2062 | -0.0067 | 0.0056 |

Eight detrended 8,192-row windows per scalar, with fixed shuffled controls. **Temporal periodicity and arrival burstiness are N/A for every dataset: no timestamp or verified time axis is supplied.** Deep norm variation is almost entirely numerical normalization residue and must not be interpreted as semantic dynamics.

## Limits and provenance

- These describe stored representations and sampled neighborhoods, not index speed or causal pruning efficiency.
- T-loc uses raw-coordinate Euclidean distance, not kilometers. Its grid occupancy depends on the observed bounding box.
- Equal reference count controls sample density budget; it does not emulate the full 1M or 10M search index.
- Vector uses the benchmark angular metric, not 1−cos. Coordinate PCA and Hoyer still describe stored amplitudes.
- Full scans, PCA, hubness, and order summaries for the first five datasets are reused only after input SHA verification; all their 20k-reference geometry and native-query diagnostics are freshly measured.
- Full duplicate rates are available for new text datasets. Original vector duplicate estimates remain the original 50k sample, not full-corpus rates.
- Protein/ChEMBL use the explicitly admitted supplementary-root files when present. The upstream release and fingerprint generator remain unverified; no similarly named version is substituted.

| Dataset | Source role | Input SHA-256 |
|---|---|---|
| SIFT-1M | primary | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| Deep-1M | primary | `4f418cbd3d87183ad2965fbf85b921c16b3702e973ad585edc4c791380abde90` |
| GIST-1M | primary | `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0` |
| Word | primary | `72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c` |
| T-loc-1M | primary | `a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677` |
| T-loc-10M | primary | `bf0f3eda7dfd66cc4b414adacd00e5495217d86e29c20bf9c57f1f4ded3adc31` |
| Vector-200K | primary | `9279dc99863783c38387552714c0ecbeac092aec9cae752782a905c17d8e1e57` |
| Protein | supplementary | `c082541fa5b0725193cd34a6c6457f6aa823524d99c302e38034f6d8639eae40` |
| ChEMBL | supplementary | `125f5d8887a8786646b34e278ff71137420bf40b2ba7649031bf1295143eb45c` |
