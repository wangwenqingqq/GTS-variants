# Nine-dataset characterization: registered extension

Experiment ID: anns_20260922_characterization_native_metric_v2.
Registration status: designed, before extension measurements. This is descriptive
characterization, not a novel algorithm or performance claim. The original v1
contract, implementation, and 50,000-reference results remain immutable.

## Inputs and metric

Reuse the original five exact files and their full-scan statistics only after
matching their full SHA-256. Add T-loc 10M (header `2 10000000 2`) and Vector-200K
(`300 200000 5`) from the explicitly supplied primary root. Protein
(`100 52799 6`, original strings) and ChEMBL (`2048 50000 8`, binary fingerprints)
require an explicitly supplied supplementary root; no automatic fallback.
The similarly named ASCII-token `protein_200k.txt` is NOT interchangeable.
Record source hashes and source-root roles, without publishing private paths.

Distances: Euclidean on stored SIFT/Deep/GIST and raw T-loc coordinates;
unit-cost Levenshtein for Word/Protein; angular distance in degrees
`acos(clip(dot/(norm_a*norm_b),-1,1))*180/pi` for Vector; binary Tanimoto
`1-intersection/union` for ChEMBL, with empty/empty distance zero. Vector's
metric ID 5 was verified in native benchmark code: it is not `1-cos`.
Zero-norm angular inputs fail validation. Numeric arithmetic uses float64;
this is a mathematical metric audit, not bitwise reproduction of GPU float32.
The exact fingerprint generator/release is not established merely by the file
name or header. Do not infer molecular identity from identical fingerprints.

## Matched geometry

All datasets use 20,000 references and 512 disjoint uniform base queries for each
seed 20260922, 20260923, 20260924. Draw 20,512 distinct IDs with NumPy default_rng.
This replaces neither v1 nor its sample plans. Retain every selected ID and
per-query nearest-200 radii, means/std, RC1/10/100, expansion10/50/100, top-10 gap,
tie fraction, CV, and self-exclusion counts. Same formulas/invalid policy as v1.
Report LID20/50/100 only for continuous numeric distances, including angular;
omit Word, Protein, and binary ChEMBL. Report invalid counts and observed seed
ranges, not confidence intervals. Native query IDs use min(512, available)
queries with self exclusion; Vector has only 100 supplied query IDs.
No cross-dataset latency/pruning ranking is implied by distance ratios.

## Full-scan and representation descriptors

Reuse immutable v1 full, covariance, hubness, and row-order summaries for the
first five datasets, linked to their result hashes. Additional datasets use the
same full-scan definitions and 10,000-row PCA / 2,048-row hubness / 20,000 random
pair budgets as v1 (sampling seed 8402). Spatial occupancy is bounding-box
dependent, not coordinate sparsity. Vector gets exact zeros, Hoyer, relative
near-zeros, coordinate moments and norms; PCA describes stored coordinates and
is NOT intrinsic angular dimension. ChEMBL additionally gets bit prevalence,
mean binary marginal entropy and active-bit-count distribution; zero fraction
is bit sparsity. ChEMBL PCA is a linear representation diagnostic, not Tanimoto
dimension. Protein gets lengths, symbol/2-gram/3-gram entropies and duplicates;
these are not coordinate sparsity. Full duplicates are audited for new text
datasets (T-loc coordinates, vector rows, protein strings, fingerprint rows).

Adjacent distances scan every file neighbor in its native metric. Robust excess
step rate, adjacent/random median ratio, block mean shifts, detrended ACF and
FFT with shuffle controls keep v1 definitions. Scalar signals are coordinates
for T-loc, stored norm for Vector, sequence length for Protein, active-bit count
for ChEMBL. No timestamp exists: temporal periodicity and arrival burstiness
remain N/A. Ordered-file diagnostics must not be called temporal dynamics.
New native-query discrepancy is descriptive KS distance on sequence length,
vector norm, or bit count; T-loc also uses the v1 Euclidean RBF MMD test.

## Resources and validation

Read-only inputs, CPU only, at most two BLAS/OpenMP threads, low scheduling/I/O
priority, task-owned output directory, no shared-service changes. Record local
hardware/software/source/contract hashes and logs. Reject malformed headers,
rows, nonfinite inputs, nonbinary fingerprints, changed source metadata, and
insufficient cardinality. Never overwrite a result directory.
Before measurement, test angular axes/scale/zero norms, Tanimoto empty/disjoint/
identical vectors against SciPy Jaccard, edit-distance fixtures, ties, sample
disjointness and parser failure cases. After measurement, independently validate
NPZ-to-JSON agreement, counts, radii ordering, metric bounds, source identity and
all nine coverage (or explicitly report missing datasets). Visually inspect
rendered tables/plots before publication; no raw input objects are published.

## Evidence ledger (registered)

| Claim | Initial state | Required evidence | Allowed scope |
|---|---|---|---|
| Added datasets differ in representation sparsity and neighborhood geometry | unknown | Full scans plus three matched sampled runs | Exact supplied versions only |
| File order has local structure | unknown | All adjacent distances versus fixed random pairs and shuffle controls | File order, not time |
| Real-time periodicity or arrival burstiness | unknown | Timestamped/arrival workload, not supplied | Not identifiable from these static inputs |

Definitions and literature references from v1 continue to apply. Additional
distance definitions are checked against the native implementation, not inferred
from broad dataset names. See also SciPy's cosine definition (which differs from
the native angular metric): https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.cosine.html
and the Tanimoto fingerprint convention: https://chembl.gitbook.io/surechembl/chemical-search/similarity-search-tanimoto-coefficient-and-fingerprint-generation
These external pages do not establish the provenance of the local files.

## Pre-acceptance numerical amendment

Initial angular fixtures using only axis-aligned vectors missed a cancellation
problem: acos of a rounded cosine made some exact duplicates nonzero. The
initial run is retained as unpromoted evidence. Before the accepted rerun, use
the equivalent stable chord form `2*asin(||unit(a)-unit(b)||/2)` in degrees,
without a distance epsilon; exact duplicates retain exact zeros. Native-query
scalar norms are promoted to float64 before reduction. Query fingerprints are
checked before and after use, not only after use. Add random 300D duplicate
fixtures and a two-row nonbinary parser fixture. Sampling and metric semantics
are unchanged. Rerun the complete primary set with the corrected source.
