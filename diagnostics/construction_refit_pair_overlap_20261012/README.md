# Construction–refit pair overlap diagnosis

**Conclusion: exact identity overlap is 100% in both rebuilds, but existing nominal construction outputs are not admitted as the frozen numeric-refit interval certificate. Decision: `NO_GO_REUSE`, limited to direct reuse of those existing outputs.**

This is a CPU-only diagnosis of GIST N1M/D960/FP32, current P2, the same 336-event trace and rebuilds at steps 48 and 216. No new GPU process, instrumentation, cache, fusion, kernel change or performance claim.

- [Frozen contract](CONTRACT.json), [baseline/provenance audit](BASELINE_AUDIT.md).
- [Pair and owner schema](PAIR_SCHEMA.md), [results](RESULTS.md), [decision and reopen condition](DECISION.md).
- [Claim/evidence ledger](CLAIM_EVIDENCE.md), [source/numeric/lifetime audit](evidence/NUMERIC_LIFETIME.md).
- [Input hashes](evidence/INPUT_MANIFEST.json), [machine-readable results](summary/RESULTS.json).

## Reproduce

Python 3.9+ and installed NumPy suffice; no CUDA installation is required. Run from the repository root. The analyzer reuses the hash-pinned canonical-tree checker from the earlier causal diagnosis; it verifies its hash **before importing it**.

```sh
python3 diagnostics/construction_refit_pair_overlap_20261012/scripts/analyze.py --self-test
python3 diagnostics/construction_refit_pair_overlap_20261012/scripts/analyze.py \
  --capture-root "$INPUTS/captures" \
  --snapshot-root "$INPUTS/snapshots" \
  --source-root "$INPUTS/frozen_source" \
  --prior-root "$INPUTS/prior" \
  --output "$OUTPUT/new-analysis"
python3 diagnostics/construction_refit_pair_overlap_20261012/scripts/validate.py
```

The four input roots must contain the exact relative files/bytes/hashes in `evidence/INPUT_MANIFEST.json`. The prior root contains `QUALITY.json`, `PRIOR_COUNTS.json`, `SOURCE_AUDIT.json`. The capture root contains `runs/R{1,2}_C0`, including stage audit arrays and C0 final outputs/decisions. The snapshot root contains original `POST_R1` and `POST_R2`. Inputs and derived pair lists are retained privately; they are **not bundled in Git** and are not synthetic fixtures. Public scripts plus manifests do not imply an independently downloadable dataset bundle.

The output directory must not already exist. Every actual task is materialized as a lossless ordered occurrence pair with a canonical-owner dictionary reference; all counts must match captured production metadata and source-exact loops. No timer is used as a performance denominator. Large task lists and intermediate analysis versions remain private; the final analysis payload hashes are retained in `evidence/DERIVED_MANIFEST.json`.
