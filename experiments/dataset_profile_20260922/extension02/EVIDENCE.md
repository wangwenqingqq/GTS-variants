# Extension evidence ledger

## Source admission

The primary-root inventory contains the original five datasets, T-loc 10M and
Vector-200K. Protein and ChEMBL were not found under that root. Candidate
supplementary files have headers `100 52799 6` and `2048 50000 8`; use is pending
source-version confirmation unless a supplementary accepted run is explicitly
listed in `VALIDATION.json`. File names do not establish a particular UniProt or
ChEMBL release. No alternative is silently substituted.

Native metric mapping was checked against the benchmark's `search.cuh`, SHA-256
`efb9678c76f42786c0f9da26e5c21c114c1fa02ca6272b302617ce1f74b93e9d`:
ID 5 is angular degrees, ID 8 is binary Tanimoto (empty union maps to zero), and
ID 6 is unit-cost Levenshtein. This verifies metric semantics, not upstream data
provenance or the correctness of all GPU search/pruning paths.

## Negative evidence and numerical correction

The initial extension run used direct acos of a floating-point cosine. It was
not promoted. A remote 300D fixture with 32 exact duplicate query/reference
pairs reported only 14 zero nearest distances: 18 erroneous positive nearest
distances caused RC1 and LID to be treated as valid. The corrected chord form
reports all 32 as zero and all 32 RC1/LID estimates invalid, without an epsilon.
The initial source, contract, outputs and logs remain outside Git with hashes
in the raw evidence manifest. Reopen only on a demonstrated counterexample to
the corrected duplicate semantics; do not restore acos based on speed alone.

Two additional fixes precede acceptance: native-query norm diagnostics now
reduce in float64, and query fingerprints are checked before and after use.
The binary parser fixture now reaches the nonbinary guard rather than failing
prematurely on a single-row shape. The complete primary set was rerun after all
fixes; no initial-run aggregate is mixed into the accepted comparison.

## Claim boundaries

| Claim | State | Evidence / denominator | Allowed wording |
|---|---|---|---|
| Representation descriptors for accepted rows | measured after validation | Every input row; source SHA verified | Properties of these exact stored files |
| Native-metric neighborhood geometry | partial relative to full-corpus geometry | Three 20k-reference, 512-query exact sampled searches | Matched sampled-reference descriptors, not full-index neighbors |
| Row-order locality / abruptness | measured after validation | All adjacent rows versus 20k random pairs; fixed robust threshold | File-order properties, not arrival dynamics |
| Temporal periodicity and arrival burstiness | unknown | No timestamps or verified time axis | N/A, not evidence of absence |
| System speed, pruning efficiency, or causality | unknown | No index/search latency experiment | No performance conclusion |
| Protein / ChEMBL candidate versions | unknown until source admission | Headers only, unless accepted supplementary run exists | Do not infer measured metrics from the candidate inventory |

The authoritative acceptance list and result hashes are in `VALIDATION.json`.
PCA and hubness budgets are separate from the 20k-reference geometry budget.
The first five datasets' unchanged v1 full-scan/PCA/hubness/order summaries
are reused by source and result hash, while their geometry is freshly measured.
Seed ranges quantify observed sampling sensitivity and are not confidence
intervals. The numerical fixtures, source identity checks and raw-result
consistency tests do not constitute an ANN performance benchmark.
