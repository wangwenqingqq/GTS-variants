# ANNS dataset characterization — frozen contract

Status at registration: designed; no dataset metrics measured.
Experiment ID: anns_20260922_characterization_native_metric_v1.

## Scope and provenance

The input root is supplied explicitly at execution. Only SIFT-1M, Deep-1M,
GIST-1M, Word, and T-loc 1M are in scope. Larger variants and unrelated datasets
are not silently substituted. Inputs are read-only. Output is a new directory.
Record full SHA-256, byte size, modification time, headers, actual row counts,
Python/package versions, source hash, command, host and CPU environment locally.
Fail on malformed input, non-finite numeric input, or changed source metadata.
No GPU, training, system configuration changes, or existing-process termination.
Use low scheduling priority and two numerical-library threads at most.

## Data and metric semantics

- SIFT/Deep/GIST: little-endian float32 fvecs; validate every dimension marker.
  Use Euclidean distance on stored values, without normalization or whitening.
- T-loc: the 1M GTS text file, skip its `dimension count metric` header;
  parse values as float64 and retain the benchmark's raw-coordinate Euclidean
  metric. Distances are NOT kilometers. No coordinate-reference assumption.
- Word: the original strings after the metadata header; strip line terminators
  only, preserve case and punctuation; unit-cost Levenshtein distance. Length is
  measured in decoded Unicode code points. Record encoding and byte differences.
- Existing query files are external for the three vectors. Word/T-loc query IDs
  are an additional native query workload, not assumed representative of the base.

## Full-scan statistics

Numeric inputs: row/coordinate counts, non-finite counts, extrema, coordinate
mean/std, zero and negative fractions, constant dimensions, all-zero rows,
L2-norm distribution. SIFT/Deep/GIST additionally: Hoyer distribution and
relative near-zero fractions at 0.001, 0.01, 0.05 times each row's RMS amplitude;
report the thresholds and do not label these exact sparsity.
T-loc: exact duplicate fraction and multi-resolution 16/32/64/128 grids over the
observed bounding box (occupancy and normalized cell-count entropy); these are
bounding-box dependent, not physical global density measures.
Word: exact duplicate fraction, length distribution, character entropy, observed
bigram/trigram vocabulary and count entropy, and lexicographic-order fraction.
String character/gram entropies are representation descriptors, not embedding
sparsity or temporal entropy.

## Sampling and geometry

Three fixed seeds: 20260922, 20260923, 20260924. Each seed independently draws
50,512 distinct base indices uniformly: 50,000 references and 512 held-out base
queries. Retain IDs; remove self matches for the additional native query mode.
Compute exact distances to the SAMPLED reference set. These are not full-1M
nearest neighbors. Do not call seed ranges confidence intervals.

For each query retain mean/std distance, nearest distances up to rank 200,
RC at k=1/10/100 (mean distance / r_k), expansion r_(2k)/r_k at k=10/50/100,
the relative top-10 gap (r_11-r_10)/r_10, and tie fraction at the top-10 boundary.
Denominators that are zero are reported invalid, not stabilized by arbitrary
epsilons. For continuous numeric inputs calculate LID MLE at k=20/50/100:
`-k / sum(log(r_i/r_k))`. Zero-radius or zero-distance cases are invalid;
no dequantization. Word LID is not reported because discrete edit-distance ties
violate the continuous local model. Report mean, SD, P10/P50/P90 for query metrics.
Distance concentration is std(distance)/mean(distance), by query.

A uniform 10,000-row sample supplies centered covariance eigenvalues, PCA90/95,
top-PC variance share and covariance effective rank `exp(-sum(p log p))`.
The covariance is not standardized; zero-total-variance results are invalid.
Vector duplicate fraction is measured on the first 50,000-reference sample,
not extrapolated as the full-corpus duplicate fraction.

Hubness: one uniform 2,048-object sample, exact self-excluded kNN graph at k=10;
fractionally allocate the remaining neighbor slots among equal-distance ties.
Report incoming-count skewness and top-1%-object share. This is sample hubness,
not production query popularity.

## Query distribution and row-order diagnostics

Numeric native query/base discrepancy: biased nonnegative RBF MMD squared on
512 queries and 512 random base points; bandwidth squared is the median positive
pooled pairwise squared distance. Compare to 99 pooled-label permutations with
the same bandwidth. The p-value is exploratory (no familywise claim), and the
kernel scale differs across datasets. Never rank datasets by raw MMD alone.
Word: compare native-query versus random-base length distributions using the
descriptive two-sample KS distance; do not substitute edit distance into an RBF
kernel without checking positive definiteness.

Full row-order adjacent-object distances: P50/P95/P99 and a median ratio to
20,000 uniformly drawn distinct-object random pairs. Report excess-step fraction
above `median + 6 * 1.4826 * MAD` (null if MAD is zero); this threshold is a
predeclared descriptive heuristic, not an anomaly detector or significance test.
Window length: 5,000 rows; retain scalar mean/variance and normalized maximum
adjacent-window mean change (norm for vectors, each coordinate for T-loc, length
for Word). ACF1 and detrended FFT dominant-bin power share use eight uniformly
positioned 8,192-row windows and shuffled controls, with lags 2..1024 for the
largest positive ACF peak. These are file-order diagnostics only.
Temporal periodicity and arrival burstiness are N/A for all five static inputs:
no timestamp or verified time axis has been supplied. Feature-axis FFT is omitted.

## Validation and stopping

Before data runs, an executable self-test covers fvec parsing, Euclidean/edit
distance, Hoyer, duplicate/tie handling, LID invalids, MMD permutation behavior,
and a synthetic sinusoid versus shuffled control. All five datasets must finish,
or the delivery must identify missing results. Retain per-dataset progress and
errors. Inspect metric bounds, sample disjointness, counts, and source hashes.
No performance, novelty, or causal systems claim is inferred from characterization.
Do not overwrite a finished run; amendments and additional runs get new paths.

## Core references

- https://www.jmlr.org/papers/v5/hoyer04a.html
- https://research.google/pubs/on-the-difficulty-of-nearest-neighbor-search/
- https://mistis.inrialpes.fr/~girard/Fichiers/p29-amsaleg.pdf
- https://pure.itu.dk/ws/files/86422343/1.pdf
- https://doi.org/10.5281/zenodo.40328
- https://www.jmlr.org/papers/v11/radovanovic10a.html
- https://www.jmlr.org/papers/v13/gretton12a.html
- https://robjhyndman.com/papers/icdm2015.pdf
- https://barabasi.com/media/pub_imports/files/233.pdf
- https://link.springer.com/article/10.1007/s10618-019-00647-x
