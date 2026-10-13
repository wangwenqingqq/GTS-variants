# Gate4 — no distinct mechanism admitted

**Decision: `NO_DISTINCT_MECHANISM`.** The three frozen candidates do not supply
a non-incremental research mechanism. M2/M3 have positive logical-byte headroom;
their novelty rejection is **not** a claim that they cannot improve performance.
No CUDA implementation, new GPU/NCU run, external benchmark or manuscript edit
was made. Parent Gate3 remains **UNCLASSIFIED**, unchanged.

## Results and denominators

All data: initial **GIST1M, N=1,000,000, D=960, FP32 raw=3.840GB**.
M2 uses the frozen32 Gate2 range queries; M3 uses the first32 kNN events' source
rows from original Gate3 A, k8, self matches/duplicate occurrences retained.
Each CPU replay covers all32,000,000 query/object pairs. They are different query
pools; neither is a rerun of the mutated336-event service.

| Candidate | Cheap-kill evidence | Numeric gate | Research admission |
|---|---|---|---|
| M1 physical layout | Coordinate-sector overfetch saving **0%**; even deleting all other modeled payload yields **8.02%** | FAIL, <20% | KILL_M1; no layout implementation |
| M2 interval screen | Auxiliary representation **6.68%** raw; first-two-stage raw payload **0.846914 ->0.181146GB/query**, **78.61%** lower including full prefix rereads | PASS, <=25% and >=50% | KILL_M2; known interval filter/refine, no distinct principle |
| M3 unified k8 | Oracle-threshold ideal **3.840000 ->1.572236GB/query**, **59.06%** lower; frozen four-stage schedule **41.44%** lower | PASS, ideal >=40% | KILL_M3; shared progressive query primitive already has precedent |

**These are CPU counts and logical-byte/transaction models, not new measured
DRAM or GPU/E2E speedups.** M1's historical NCU comparison is separately labelled.
M2 charges256.526336MB codes/boundaries,214.490384MB code reads/query and a512KiB
query LUT; its prefix percentage is not a total-traffic percentage. The known
coordinate+code+LUT payload is0.564076GB/query before remaining control/state,
maintenance, sector and output costs.

### Material kNN caveat: the oracle threshold is not free

M3's primary headroom estimator supplies the final exact eighth-neighbor score
before scanning. With one predeclared, valid first256-row seed cutoff instead,
and all seed reads charged, ideal saving is only **37.25%**; frozen four-stage
saving is **17.20%**. This does **not** change M3's declared primary numeric pass;
it demonstrates why threshold acquisition/tightening, selection and control
must be charged in a deployable design. No adaptive-threshold GPU algorithm was
implemented or timed.

## Strongest novelty counterevidence

The [prior-art matrix](prior_art/PRIOR_ART_MATRIX.md) covers BOND, PDX/PDX-BOND,
VA-file, Faiss/cuVS exhaustive search, GPU/SIMD early exit and GPU compaction.
Live source review additionally found [Faiss FlatPanorama's shared core](https://github.com/facebookresearch/faiss/blob/1a9ddc60d2201c9a44dfca3acead6ee38fbe21dc/faiss/IndexFlat.cpp#L620-L755).
Its two query APIs share progressive filtering, changing the threshold source.
This is a mechanism precedent, **not** a same-contract performance comparison or
a proof of numerical parity with our ordered-FP64 oracle.

No winner passed the four-part admission rule. External comparisons are
[not executed](external/EXTERNAL_RESULTS.md); a conditional
[comparator contract](external/COMPARATOR_PLAN.md) is retained, not a queued job.
The negative conclusion is limited to these three frozen candidates, not all
future GPU-native representations or search mechanisms.

## Validation and evidence

- One sector model and one combined CPU population process,4 workers,nice10,
  **0 GPU starts**, no failure/replacement, no foreign process/GPU setting changes.
- Deterministic numerical/tie/tail fixtures and64 first4096-row query checks pass.
- M2: conservative bounds checked at128/256 for every pair; **0FN/0FP** after
  ordered exact fallback;6,590 returned range members and scores verified.
- M3: all32M complete ordered-FP64 scores freshly recomputed and bitwise equal
  to the hash-bound parent oracle; exact k8, cutoff ties and first crossings pass
  for both thresholds. No new GPU correctness/sanitizer gate is claimed.
- [Frozen contract](CONTRACT.json), [decision](DECISION.md),
  [claim ledger](CLAIM_EVIDENCE.md), [source identity](evidence/SOURCE_IDENTITY.json),
  [scalar query records](evidence/CPU_QUERY_RECORDS.json),
  [raw identity](evidence/RAW_IDENTITY.json),
  [saved-array recheck](evidence/RAW_RECHECK.json),
  [pinned upstream identities](prior_art/PINNED_SOURCE_IDENTITY.json),
  [execution closure](evidence/EXECUTION_CLOSURE.json).

Raw coordinates, codes, complete scores and per-pair arrays remain private,
outside Git. See [reproduction](REPRODUCE.md) and [validation scope](VALIDATION.md).
Retain the established range
operator/engineering evidence; do not promote it into a new-index thesis or
revive stage tuning to rescue14.41% into15%.
