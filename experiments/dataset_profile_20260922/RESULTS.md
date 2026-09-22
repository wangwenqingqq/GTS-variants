# Dataset characterization results

Completed under `CONTRACT.md`, native-metric version 1. Inputs are read-only.
**Scope:** full scans for elementary statistics; exact search over 50,000 sampled references, 512 held-out queries, and three fixed seeds for geometry. These are not full-corpus nearest neighbors.
No normalization or whitening was applied. No GPU was used. Seed ranges are not confidence intervals.

## Main comparison

| Dataset | N | Dimension / length | Exact zero (%) | Hoyer mean | PCA95 | LID50 median* | RC10 mean* | Expansion10 median* | Adjacent/random median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SIFT-1M | 1,000,000 | 128 | 22.992 | 0.447 | 72 | 20.317 | 2.185 | 1.036 | 0.8979 |
| Deep-1M | 1,000,000 | 96 | 0.000 | 0.223 | 77 | 19.986 | 1.808 | 1.036 | 1.0009 |
| GIST-1M | 1,000,000 | 960 | 0.004 | 0.146 | 291 | 41.044 | 1.732 | 1.017 | 0.9560 |
| Word | 611,756 | 1–32 chars | N/A | N/A | N/A | N/A | 2.533 | 1.000 | 0.4000 |
| T-loc-1M | 1,000,000 | 2 | N/A | N/A | 1 | 2.018 | 390.730 | 1.420 | 0.0076 |

*Main geometry entries are the median of the three seed-level estimates. PCA uses 10,000 rows; file-order distance summaries use every adjacent pair and 20,000 random distinct-index pairs. Spatial zero-coordinate counts are not interpreted as sparsity.

## Sampling sensitivity

| Dataset | RC10 mean: seed min–max | LID50 median: seed min–max | Expansion10 median: seed min–max |
|---|---:|---:|---:|
| SIFT-1M | 2.169–2.218 | 19.757–20.442 | 1.035–1.037 |
| Deep-1M | 1.783–1.812 | 19.564–20.030 | 1.036–1.037 |
| GIST-1M | 1.681–1.747 | 39.917–41.682 | 1.017–1.018 |
| Word | 2.432–2.546 | N/A | 1.000–1.000 |
| T-loc-1M | 388.644–396.691 | 1.993–2.019 | 1.419–1.430 |

## Native-query workload versus uniform base queries

| Dataset | Uniform RC10 mean* | Native-query RC10 mean | Native mean nearest distance | Discrepancy check |
|---|---:|---:|---:|---|
| SIFT-1M | 2.185 | 2.203 | 221.52 | RBF MMD²=0.00087382; permutation p=0.92 |
| Deep-1M | 1.808 | 1.810 | 0.68581 | RBF MMD²=0.001177; permutation p=0.93 |
| GIST-1M | 1.732 | 1.670 | 1.1408 | RBF MMD²=0.0022763; permutation p=0.08 |
| Word | 2.533 | 2.771 | 2.4062 | Length KS distance=0.2461 |
| T-loc-1M | 390.730 | 192.443 | 0.31934 | RBF MMD²=1.2045; permutation p=0.01 |

MMD is a bandwidth-dependent exploratory within-dataset test with 99 label permutations; raw MMD magnitudes are not a cross-dataset ranking. The Word and T-loc native query-ID files select IDs 0–999; these prefix workloads must not be treated as uniformly sampled queries.

## Dataset-specific structure

### SIFT-1M
- Norm mean/SD: 508.643 / 0.658575.
- Relative near-zero fractions (0.001 / 0.01 / 0.05 × row RMS): 22.9920% / 22.9920% / 32.8549%.
- Duplicate fraction in the 50,000-object sample: 0.00064.
- Covariance effective rank: 27.755; first-PC share: 32.681%.
- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness 1.798; top-1%-object share 4.966%.
- Adjacent distance P50/P95/P99: 504.449 / 657.571 / 684.163.
- Excess-step fraction above the predeclared robust threshold: 0.000000.
- File-order l2_norm: median detrended ACF1 0.1085, shuffled control 0.0029; maximum 5,000-row mean shift 0.843 global SD.

### Deep-1M
- Norm mean/SD: 1 / 3.27839e-08.
- Relative near-zero fractions (0.001 / 0.01 / 0.05 × row RMS): 0.0791% / 0.7908% / 3.9601%.
- Duplicate fraction in the 50,000-object sample: 4e-05.
- Covariance effective rank: 64.618; first-PC share: 7.412%.
- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness 1.372; top-1%-object share 3.882%.
- Adjacent distance P50/P95/P99: 1.38143 / 1.50434 / 1.54373.
- Excess-step fraction above the predeclared robust threshold: 0.000000.
- File-order l2_norm: median detrended ACF1 -0.0016, shuffled control 0.0008; maximum 5,000-row mean shift 0.077 global SD.

### GIST-1M
- Norm mean/SD: 2.50566 / 0.69612.
- Relative near-zero fractions (0.001 / 0.01 / 0.05 × row RMS): 0.0037% / 0.0125% / 0.1639%.
- Duplicate fraction in the 50,000-object sample: 0.00148.
- Covariance effective rank: 77.631; first-PC share: 19.995%.
- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness 3.539; top-1%-object share 10.386%.
- Adjacent distance P50/P95/P99: 1.7914 / 2.76742 / 3.50061.
- Excess-step fraction above the predeclared robust threshold: 0.001752.
- File-order l2_norm: median detrended ACF1 0.1360, shuffled control -0.0026; maximum 5,000-row mean shift 0.198 global SD.

### Word
- Mean length: 10.3140; character vocabulary: 77.
- Character / bigram / trigram entropy (bits): 4.4644 / 8.1880 / 11.5578.
- Exact full duplicate fraction: 1.63464e-06.
- Lexicographically nondecreasing adjacent pairs: 99.9998%.
- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness 1.187; top-1%-object share 3.949%.
- Adjacent distance P50/P95/P99: 4 / 10 / 15.
- Excess-step fraction above the predeclared robust threshold: 0.000845.
- File-order length: median detrended ACF1 0.5242, shuffled control 0.0025; maximum 5,000-row mean shift 1.045 global SD.

### T-loc-1M
- Exact full duplicate fraction: 0.
- Coordinate ranges: [(-83.99355935, 64.99125706), (-176.99795195, 177.99636472)].
- Raw-coordinate Euclidean distance is retained for benchmark consistency; these are not kilometers.
- 16×16 bounding-box grid: occupancy 37.89%; normalized count entropy 0.5599; largest-cell share 19.453%.
- 32×32 bounding-box grid: occupancy 22.66%; normalized count entropy 0.5723; largest-cell share 7.199%.
- 64×64 bounding-box grid: occupancy 13.70%; normalized count entropy 0.5894; largest-cell share 5.128%.
- 128×128 bounding-box grid: occupancy 9.38%; normalized count entropy 0.6161; largest-cell share 2.663%.
- Covariance effective rank: 1.168; first-PC share: 96.400%.
- Sample hubness (2,048 objects, k=10, fractional tie handling): incoming-count skewness -0.132; top-1%-object share 1.963%.
- Adjacent distance P50/P95/P99: 0.512808 / 0.940512 / 1.09063.
- Excess-step fraction above the predeclared robust threshold: 0.000515.
- File-order coordinate_0: median detrended ACF1 0.4479, shuffled control -0.0047; maximum 5,000-row mean shift 0.436 global SD.
- File-order coordinate_1: median detrended ACF1 0.9975, shuffled control 0.0004; maximum 5,000-row mean shift 1.553 global SD.

## Interpretation limits

- File-order autocorrelation, jumps, and spectral peaks do not establish temporal periodicity. No timestamp or verified time axis is present; temporal periodicity and arrival burstiness remain N/A.
- LID is a continuous local-distance estimator. It is omitted for Word; quantization, ties and duplicates in numeric datasets are retained and invalid estimates are explicitly counted.
- Relative contrast, neighbor expansion, LID and hubness are geometric descriptors, not measured latency, pruning efficiency, or causal explanations of system performance.
- Duplicate fractions for vectors are sample-only. Full duplicate fractions are available only for Word and T-loc.
- Deep vectors have almost exactly unit norm (SD about 3.28e-8); norm-series ACF and spectral diagnostics mainly concern numerical normalization residuals, not semantic vector dynamics.
- T-loc PCA95=1 and local LID near 2 are compatible: the former describes global variance concentration, while the latter describes sampled local distance growth.
- Inspect the complete per-dataset JSON for distribution quantiles, invalid counts, all three LID neighborhood sizes, source hashes, and spectral window results.

## Provenance

| Dataset | Input SHA-256 |
|---|---|
| SIFT-1M | `21f66e2975057b5728ba56de1c825bac4f4d89d596609ae985741c6242631816` |
| Deep-1M | `4f418cbd3d87183ad2965fbf85b921c16b3702e973ad585edc4c791380abde90` |
| GIST-1M | `73418110328f5aa522d9f6b0cd9115a6c515dc44e3c48420e506ddeddbdbdbc0` |
| Word | `72091b6cdd29532d44790ad049afa58eb8582957061fcf5c98b28b9b30c81c1c` |
| T-loc-1M | `a9c71ead1bdab0f254abfcdc8b947db56e3af50c571b3b5ad9fbe607fddb8677` |
