# E1 production-input preparation, v3

## Changes and rationale

`prepare_inputs_v3.py` creates new, immutable prepared-input directories. It does
not edit `CONTRACT.md`, the frozen input audit, an evaluator, any source corpus,
or an existing workload. No measured result is produced by this script.

- For T-loc, Word, Protein and ChEMBL, draw 1,000 source rows with NumPy
  PCG64(seed=20261026), `choice(replace=False)`. Remove **every** corpus row
  feature-identical to any drawn query. Reset PCG64 to the same seed and
  permute the retained source rows; the first floor(N/10) are arrivals and the
  remainder are the initial base. The manifest records actual post-exclusion N.
- Preserve ANN-Benchmarks native queries for SIFT/GIST/Deep. Exact feature
  overlaps block preparation by default. The separately gated
  `--exclude-ann-corpus-overlap --amendment-reference ...` path is available
  **only after a specific user-approved amendment**; its existence does not
  authorize using it. The known GIST/Deep collisions are not silently repaired.
- Equality treats +0/-0 as equal, rejects nonfinite numeric features and preserves
  Latin-1 text bytes. Query source maps, excluded source maps, base/arrival maps,
  payload arrays, workload files and source files are SHA256-pinned.
- Prepare the entire 10K/100K, 442/811/181, random/skew matrix, including L2 k=10.
  Capacity-infeasible loads remain visible as `contract-infeasible`. IDs are
  stable, sequential and never reused; deletion samples a currently active ID.
  No arrival is synthesized or repeated to fill a deficient workload.
- Word/Protein skew is length, bytewise lexical order, then original source row;
  ChEMBL is popcount with original arrival-permutation tie order; T-loc uses
  64 cells per coordinate and row-major cell order. SIFT/GIST/Deep skew requires
  separately frozen, full-source-row k-means labels, k=64 and seed=20261026.
  Missing labels produce `preparation-blocked` skew rows, never a random-order
  substitute. The companion `<labels.npy>.manifest.json` must contain `k`,
  `seed`, `corpus_sha256` and `labels_sha256` matching the inputs; include solver,
  software version and fit scope in that provenance for review.
- Save corpus payloads once per order. The `case` subcommand materializes one
  selected legacy `E1CASE1` binary on demand, verifies prepared-file hashes,
  and refuses blocked/infeasible rows. This avoids duplicating multi-GB GIST
  payloads across every matrix row.

The existing case format gives base stable IDs `[0, nb)` and arrival stable IDs
`[nb, nb+na)`. Its physical ID differs from the immutable original source-row ID;
row maps preserve the correspondence for each arrival order.

## Validation performed

```bash
python3 -m unittest discover -s dasfaa_e1/tests -p test_prepare_inputs_v3.py -v
python3 -m py_compile dasfaa_e1/prepare_inputs_v3.py
```

Six CPU-only fixture tests pass. They cover complete duplicate exclusion,
deterministic splits, the strict ANN gate, explicit-amendment enforcement,
+0/-0 equality, exact event counts, fresh IDs, active deletion, snapshots,
capacity failures, all implemented skew orderings, byte-preserving Latin-1,
end-to-end binary headers/payload/event format, immutable-input tamper rejection,
and preservation of all blocked workload rows.

## Execution interface

All remote invocations, including preparation and case materialization, must
be wrapped by the shared guard and recorded before any GPU execution:

```bash
python3 "$GUARD" --log "$LOG/prepare_word.jsonl" --rss-max-gb 16 \
  --mem-available-min-gb 48 --timeout-s 900 -- \
  env OMP_NUM_THREADS=32 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python3 dasfaa_e1/prepare_inputs_v3.py prepare \
    --data-root "$DATA" --dataset word --out "$NEW_OUTPUT/word"

python3 "$GUARD" --log "$LOG/case_word.jsonl" --rss-max-gb 16 \
  --mem-available-min-gb 48 --timeout-s 900 -- \
  python3 dasfaa_e1/prepare_inputs_v3.py case \
    --prepared "$NEW_OUTPUT/word" --load-id 100000_442_random_k8 \
    --out "$NEW_CASE/word_100000_442_random_k8.bin"
```

Each output path must be new; do not overwrite old evidence. A generated
manifest means `prepared-not-evaluated`, not correctness, sanitizer or timing
success. Root retains launch/admission ownership and the no-retry stop rule.

## Not completed here

No remote command, GPU task, full real-data preparation, k-means fit, sanitizer,
or timing was run by this worker. Query-before-insert calibration/traces and
P1 1M-operation traces remain explicitly pending; no scope is inferred from the
prepared mixed-load matrix. Larger ChEMBL/Protein sources are not admitted by
this change. Original native-query ID files are only provenance for approved
corpus-holdout datasets and are not reused as their new queries.
