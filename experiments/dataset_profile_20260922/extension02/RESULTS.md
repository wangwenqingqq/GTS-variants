# Extended dataset comparison

**Coverage: 7/9 requested datasets measured and validated.**
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
| Protein | — | Source confirmation pending | — | — | — | — | — |
| ChEMBL | — | Source confirmation pending | — | — | — | — | — |

*RC10 is the median across seeds of the per-query mean RC10; LID50 is the median across seeds of the per-query median LID50. Spatial coordinate zeros and string alphabets are not coordinate sparsity. LID is omitted for discrete strings and binary fingerprints.

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

Adjacent distances cover every neighboring row; the random comparison uses 20,000 distinct-index pairs. Excess steps exceed median + 6 × 1.4826 × MAD (N/A for zero MAD): a descriptive heuristic, not an anomaly test. Expansion is median r20/r10. PCA uses 10,000 stored-coordinate rows, not standardized features. Binary/Angular PCA is a representation diagnostic, not native-metric intrinsic dimension. Hubness uses 2,048 objects and fractional ties.

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

Seed ranges are observed sampling sensitivity, not confidence intervals. Native query comparisons exclude matching base IDs. Vector provides only 100 query IDs and is not silently expanded to 512. Native workloads need not represent uniform base queries.

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

Eight detrended 8,192-row windows per scalar, with fixed shuffled controls. **Temporal periodicity and arrival burstiness are N/A for every dataset: no timestamp or verified time axis is supplied.** Deep norm variation is almost entirely numerical normalization residue and must not be interpreted as semantic dynamics.

## Limits and provenance

- These describe stored representations and sampled neighborhoods, not index speed or causal pruning efficiency.
- T-loc uses raw-coordinate Euclidean distance, not kilometers. Its grid occupancy depends on the observed bounding box.
- Equal reference count controls sample density budget; it does not emulate the full 1M or 10M search index.
- Vector uses the benchmark angular metric, not 1−cos. Coordinate PCA and Hoyer still describe stored amplitudes.
- Full scans, PCA, hubness, and order summaries for the first five datasets are reused only after input SHA verification; all their 20k-reference geometry and native-query diagnostics are freshly measured.
- Full duplicate rates are available for new text datasets. Original vector duplicate estimates remain the original 50k sample, not full-corpus rates.
- Protein/ChEMBL versions require confirmation when absent from the primary input root. No similarly named version is silently substituted.

| Dataset | Source role | Input SHA-256 |
|---|---|---|
| SIFT-1M | primary | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| Deep-1M | primary | `4f418cbd3d87183ad2965fbf85b921c16b3702e973ad585edc4c791380abde90` |
| GIST-1M | primary | `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0` |
| Word | primary | `72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c` |
| T-loc-1M | primary | `a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677` |
| T-loc-10M | primary | `bf0f3eda7dfd66cc4b414adacd00e5495217d86e29c20bf9c57f1f4ded3adc31` |
| Vector-200K | primary | `9279dc99863783c38387552714c0ecbeac092aec9cae752782a905c17d8e1e57` |
