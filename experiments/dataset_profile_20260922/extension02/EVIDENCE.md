# Extension evidence ledger

## Initial source admission state (seven-dataset checkpoint)

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

## Supplementary admission and nine-dataset completion

On 2026-09-22 the previously identified older-GTS Protein and ChEMBL files were
explicitly approved; see `SUPPLEMENTARY_ADMISSION.md`, registered before the
supplementary run. `run04_supplementary` executes the unchanged source, helper,
contract, package versions, CPU-only policy, and matched sample budgets of
`run03_primary`. No primary result is replaced. The combined validation record
contains nine unique datasets; all nine raw-to-summary checks pass.

The initial pending-source row above is historical, not the current completion
state. Supplementary representation descriptors are now **measured** for the two
exact file hashes. Their neighborhood evidence remains **partial** relative to
full-corpus search because the reference sets are sampled. Their upstream
UniProt/ChEMBL release and fingerprint generator remain **unknown**. Temporal
periodicity and performance claims remain **unknown** for all nine datasets.

### Supplementary findings and material exceptions

- Protein has 39,630 unique sequences among 52,799 rows: 13,169 excess duplicate
  rows (24.94176%). A largest exact-match group has 114 rows. Under three sampled
  runs, zero r10 makes RC10 undefined for 17/11/20 of 512 queries, respectively;
  reported RC means use only valid queries, with all exclusions disclosed.
- ChEMBL has 97.649913% zero bits, mean 48.12978 active bits per 2,048-bit row,
  and 48,137 unique fingerprints. Repeated fingerprints do not establish repeated
  molecules without molecular identifiers.
- The registered robust step thresholds are 250.39 for Protein and about
  1.203414 for ChEMBL. These exceed their distance upper bounds of 100 and 1.
  Their measured zero exceedance rates are therefore uninformative about
  abruptness; they must not support a "no abrupt changes" claim. Preserve the
  estimator and raw evidence; report adjacent-distance quantiles rather than
  tuning a threshold after seeing these results.
- Independent re-reading confirmed the full duplicate counts and bit sparsity.
  A scalar dynamic-programming oracle checked 32 real sequence pairs, and SciPy
  Jaccard independently checked three real queries against all 20,000 sampled
  ChEMBL references. Both source hashes were independently rechecked.
