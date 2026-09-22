# Extended native-metric dataset comparison

The requested comparison contains nine datasets. Accepted coverage and any
missing source decisions are explicit in `RESULTS.md`; absent rows are not
estimated. The original five-dataset experiment in the parent directory remains
unchanged. This extension refreshes every included dataset's geometry at a
matched 20,000-reference budget, including the original five.

## Reproduce

Use the parent experiment's Python environment (NumPy, SciPy and RapidFuzz), with
Matplotlib only for rendering. No GPU or new indexing library is required.

```sh
export OPENBLAS_NUM_THREADS=2 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
python extension02/validate_extended.py
python extension02/profile_extended.py \
  --root "$PRIMARY_DATA_ROOT" --previous-run "$V1_RUN" \
  --out "$NEW_PRIMARY_RUN" \
  --datasets SIFT-1M Deep-1M GIST-1M Word T-loc-1M T-loc-10M Vector-200K
python extension02/validate_extended.py \
  --run "$NEW_PRIMARY_RUN" --previous-run "$V1_RUN"
python extension02/summarize_extended.py --runs "$NEW_PRIMARY_RUN" --out "$REPORT"
```

Run these commands from the parent experiment directory. `V1_RUN` is the
original raw output of `profile_datasets.py`, with `<dataset>/results.json`.
Source files must exactly match its recorded hashes; no raw data is in Git.

Only after confirming the supplementary versions, run:

```sh
python extension02/profile_extended.py \
  --root "$PRIMARY_DATA_ROOT" --supplementary-root "$SUPPLEMENTARY_DATA_ROOT" \
  --previous-run "$V1_RUN" --out "$NEW_SUPPLEMENTARY_RUN" \
  --datasets Protein ChEMBL
python extension02/validate_extended.py \
  --run "$NEW_SUPPLEMENTARY_RUN" --previous-run "$V1_RUN"
python extension02/summarize_extended.py \
  --runs "$NEW_PRIMARY_RUN" "$NEW_SUPPLEMENTARY_RUN" --out "$REPORT"
```

Supplementary paths are `dna_barcode/protein.txt` (52,799 raw strings, length
limit 100) and `chembl/chembl_50k.txt` (50,000 binary 2048-bit fingerprints).
The alternative ASCII-token `protein_200k.txt` and ChEMBL-10K are different
versions and are not substituted. The precise fingerprint generator and
upstream release remain unverified; report the measured file hash, not a
presumed standard release.

## Interpretation and evidence

- `CONTRACT_EXTENDED.md`: registered semantics, budgets, and numerical amendment.
- `results/*.json`: portable accepted aggregate results; no raw objects.
- `VALIDATION.json`, `EXECUTION.json`: acceptance coverage and redacted provenance.
- `RAW_EVIDENCE_MANIFEST.json`: hashes of task-local sample IDs, per-query radii,
  initial unpromoted run, logs, and validation evidence. Large/raw evidence stays
  outside Git; the manifest does not imply it is downloadable from this repo.
- `EVIDENCE.md`: claim boundaries, numerical correction, and source status.
- `extended_summary.pdf` / `.svg`: vector plots; `.png`: preview.

Native metric ID 5 is **angular distance in degrees**, not the often-used
`1-cos` function. Metric ID 8 is binary Tanimoto; ID 6 is unit-cost edit distance.
Distance definitions were checked against the native benchmark source. The
stable chord form of angular distance preserves exact duplicate zeros without
introducing an epsilon. Results characterize mathematical distances in float64,
not the rounding behavior or timing of GPU kernels.

Spatial coordinate zeros and string symbols are not feature sparsity; omit those
entries. Discrete fingerprints and edit distances do not get continuous LID.
File adjacency, abrupt steps, autocorrelation and spectral peaks are not a time
axis: temporal periodicity and arrival burstiness remain unidentifiable.
