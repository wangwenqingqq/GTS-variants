# Claim-evidence ledger

Experiment: **GTSPP_20261013_PROGRESSIVE_LOSSLESS_GATE0**. Contract and source
hashes were registered before the population replay, on base commit
`1f71ad70b5dbf839ff6bf2360b0a1197aecc8006`. The live raw-array audit is a read-only
verification of the same run, not a second replay. Date: 2026-10-13.

| ID | Exact claim / denominator | State | Evidence and quality | Material limitation / allowed wording |
|---|---|---|---|---|
| L0 | No inspected primary work directly demonstrated the complete dense-FP32 single-lossless-source/progressive/exact-distance-bound conjunction | inferred | PRIOR_ART.md; evidence/SOURCE_IDENTITIES.json | Finite search coverage, not absence proof or novelty confirmation. Several constituent primitives and the broader abstraction are established. Admission only allowed a cheap test. |
| L1 | All 960M database coordinate bits recover from one 3,840,000,064-byte layer source | measured | correctness/RECOVERY.json; representation/FORMAT.md; source/binary registration | Original data retained separately for audit. Candidate has no raw database input. Scope is one fixed layout/database plus explicit corner fixtures, not GPU legality. |
| L2 | All 32M frozen range memberships have zero FN/FP; all 6,917 full-decode scores match original oracle bits | measured | correctness/RANGE_QUALITY.json; evidence/QUERY_RESULTS.json; hashed private arrays and offline audit | Complete IDs and row-occurrence multiplicity checked. No kNN, updates, larger population, or CUDA validation. |
| L3 | Mean distinct incremental source payload is 1,025,475,825 B/query | measured | model/STAGE_COUNTS.json; model/REQUIRED_BITS.json; model/LOGICAL_BYTES.json | Replay-count-derived ideal bytes, not actual CPU/GPU traffic. Extra metadata and state disclosed separately. |
| L4 | Source payload is 1.0104914732926336x the dimension-progressive model, exceeding both 0.70x GO and 0.85 GB conditional thresholds | rejected | comparison/DIM_PROGRESSIVE_BASELINE.json; evidence/DECISION.json; frozen parent SHA | Claimed byte advantage is rejected. Prior model and present replay have the same N/D/query/radius; no fresh GPU comparator measurement. |
| L5 | The first two bit layers alone cost 959,956,485 B/query because 99.990934375% of pairs survive four bits | measured | first two STAGE_COUNTS rows, exact pooled 32M denominator | This is the decisive fixed-schedule byte floor, not a lower bound on all possible lossless codecs. |
| L6 | Coarse exponent intervals explain the measured four-bit survivor floor | inferred | ORDER_MAPPING.md; INTERVAL_DECODER.md; L5 | Mechanism-level interpretation for this layout and pool. No assertion that every bit-prefix method has the same survivor curve. |
| L7 | Candidate reduces measured GPU DRAM or host-ready latency | unknown | no evidence; Gate1 NOT_RUN, GPU/NCU counts zero | No GPU, end-to-end, stability, sanitizer, or sustained-workload claim is allowed. |

Negative evidence is retained in DECISION.md with the workload, stronger comparator,
rejected mechanism, added costs, effect, diagnosis, and reopen condition. The report
does not turn the 73.2949% logical reduction relative to full scan into a contribution
or an end-to-end improvement.
