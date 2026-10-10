# Block-aligned global safe certificates: offline design-space test

**Decision: CONDITIONAL, no GPU prototype.** Contiguous packing reduces physical
scatter, but the best <=4 shared-pivot bands still retain 87.7384% / 71.6047%
of block256 work (separately selected per snapshot). Stable local writes are
possible in the bounded ownership model; that does not clear the query gate.
See [DECISION](DECISION.md), which answers all five questions.

## Frozen workload and scope

- GIST: 1,000,000 FP32 vectors, D=960, L2, B1, two retained actual snapshots.
- 32 original range queries per snapshot, radius bits `0x3f34a3d8`.
- 48 main layout/strategy/P configurations per snapshot, P in 1/2/4/8.
  Block32/512 sensitivity reuses the same pivot sequences, never selects new ones.
- Global shared pivots were confirmed before measurement. Each query costs P
  distinct query-pivot distances plus 2*P*total_blocks scalar bound reads.
- CPU-only Ubuntu/GNU C++ 13.3, Python/NumPy 1.26.4; helper uses four threads,
  orchestration uses low priority and one BLAS thread. No GPU process or timing.
- Actual update intervals are **10I10D** and **20I20D**, independently initialized.
  Second interval has net 10 entering and 10 removed base occurrences; it is not
  mislabeled as 10I10D. 288 ownership/slack simulations, 9,216 post-update queries.

[CONTRACT](CONTRACT.json) was frozen before A–C. Automatic D admission was false,
and [the original deferred record](evidence/STATIC_UPDATE_DEFERRED.json) remains.
The user approved D as an extra diagnostic after seeing the 70–80% gray zone;
[D_CONTRACT](D_CONTRACT.json) was frozen before D. It does not relax GPU admission.
L1 sorts rows within leaves, L3 retains leaf order: their tree-candidate block
counts are equal because each leaf is wholly selected/rejected. They are not
four independent replications; exact layout permutations/hashes are retained.

## Evidence and gates

- [Layout table](layout/LAYOUT_RESULTS.md), [oracle table](oracle/ORACLE_BLOCK_RESULTS.md),
  [certificate table](certificate/CERT_SWEEP.md), [update table](update/UPDATE_LOCALITY.md).
- [Numerical proof](NUMERICS.md): outward real-norm intervals, radius inflation
  for ordered FP64 reference membership, strict separation; duplicates remain
  distinct occurrences. No reference/oracle in pivot choice or placement.
- [Static proof](evidence/STATIC_PROOF.json) binds original source/data/candidates,
  exhaustive references, selected pivots, all score/bound/layout hashes.
- [Static reconciliation](evidence/STATIC_VERIFY.json): fresh library recomputes
  all 48M distances bitwise and reconstructs every numeric row/summary.
- [D proof](evidence/D_PROOF.json), [closure](evidence/CLOSURE.json): exact original
  execution/source identities, actual trace and static inputs, all final member
  deltas and counts reconciled. Historical entry lacked explicit cross-proof
  binding; final closure supplies it, and the delivered entry now enforces it.
- [Source identities](evidence/SOURCE_IDENTITY.json) distinguishes historical
  drivers from post-run hardened delivered drivers. Do not claim the first
  runner already had the final entry gate. Arithmetic helper is unchanged.
- Curated static result JSON is byte-identical to raw. Compiler command paths
  in the verification receipt are portable; its raw receipt hash is retained.
  D numeric rows are unchanged; the overly broad historical `all_slots_checked`
  flag was corrected to `affected_slots_checked`. Untouched slots are preserved
  by construction. [Curation manifest](evidence/CURATION_MANIFEST.json) binds this.

## Reproduce without private host configuration

No dependencies, GPU, or benchmark framework need be installed. Use existing
NumPy, a C++ compiler/OpenMP, and optionally matplotlib for plots. Inputs are
resolved through the retained campaign's `INPUTS.json`, not hardcoded devices.
Keep raw evidence outside Git; `RAW` below is a fresh, non-existing directory.
The reference folder contains `initial/REFERENCE.json`, `first_rebuilt/REFERENCE.json`
and the hash-pinned `.f64` score files. `PRIOR_CAMPAIGN` contains the corresponding
`*_capture` and `*_cache` subdirectories from the baseline diagnostic. No new
exhaustive ground truth is required.

```sh
# Run from repository root; set the portable variables to retained inputs.
set -eu
SRC=artifacts/block_certificate_headroom_20261010
test ! -e "$EXECUTED_CODE"
cp -R "$SRC" "$EXECUTED_CODE"
nice -n 15 env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 python3 "$SRC/run.py" \
  --inputs "$INPUTS" --prior-campaign "$PRIOR_CAMPAIGN" \
  --references "$REFERENCES" --output "$RAW"
python3 "$SRC/test_certificate.py" --library "$RAW/distance.so" -v
python3 "$SRC/test_update.py" -v
# EXECUTED_CODE is the unchanged copy made before starting.
python3 "$SRC/verify.py" --run "$RAW" --inputs "$INPUTS" \
  --prior-campaign "$PRIOR_CAMPAIGN" --references "$REFERENCES" \
  --executed-code "$EXECUTED_CODE" --output "$RAW_VERIFY"
# D is a separately approved diagnostic, not automatic query-gate promotion.
nice -n 15 env OPENBLAS_NUM_THREADS=1 python3 "$SRC/update.py" \
  --run "$RAW" --maintenance "$MAINTENANCE" --references "$REFERENCES" \
  --static-verification "$RAW_VERIFY/VERIFY.json" --output "$RAW_D"
# Plots/tables regenerate from the curated JSON; no raw vectors or GPU required.
python3 "$SRC/report.py" --artifact "$SRC"
```

Retained raw vectors, masks, score tables, ownership arrays, frozen execution
copies and binaries are outside Git. Hashes and portable schema are published,
not the private machine map. Access to those retained data is required for a
full reproduction; this is not a self-contained dataset distribution.

## Publication and claim boundary

Ten delivered regression tests pass (six certificate/recipe, four ownership/binding).
Figures are PDF vectors plus PNGs, finite-query means without invented CIs.
No CUDA compile/sanitizer/profiler/stress/paired/sustained timing gate was run or
is claimed. Locality concerns **writes/ownership**, not total CPU work: insertion
still scans all block summaries. Layout movement/setup and certificate build
costs are not measured. End-to-end gain is **unknown**. This artifact adds no
production index, paper text, new novelty claim, matrix rerun, or P>8 search.
