# Claim–evidence ledger

Experiment: `GTSPP_20261013_dynamic_progressive_gate3`; parent commit `6baaa376a4b7afe3192ab3ba1b4269993856d479`; measurement date 2026-10-13. Hardware/software identities are in `evidence/ENVIRONMENT.json`; source/binary/input/library bindings in `evidence/INPUT_IDENTITY.json`; raw identities and per-process receipts are retained. Numeric wording below uses the tables, not a different estimator.

| ID | State | Exact scope/denominator and strongest allowed wording | Evidence | Counterevidence/limit |
| --- | --- | --- | --- | --- |
| G3-RANGE | measured | Six paired fresh A processes: complete range ACK total median is 53.35% lower, 2.143573x | timing/TRACE_A.json; operations/raw/A; quality receipts | Different pool than Gate2; no dynamic DRAM profile |
| G3-SERVICE | measured | A events + native/device/live-map release median is 14.41% lower | timing/TRACE_A.json; TIMING_BOUNDARY.md | Not entire process wall/complete Host teardown; setup and offline proof excluded |
| G3-UPDATE | measured | Forty insert/delete ACK totals retain the same sub-ms magnitude; ratios 1.036157/0.961227 | updates/UPDATE_ROBUSTNESS.json; operation records | Fixed D960/capacity; not asymptotic O(1) or unlimited churn |
| G3-QUALITY | measured | Complete member/field/multiplicity and final-state checks pass for all 22 successful formal/qualification processes | correctness; evidence/QUALITY_PROCESSES.json | Update map validity uses induction, not actual full export each mutation; sanitizers are N65 fixtures |
| G3-MEMORY | measured | No D1 O(ND) persistent vector copy; D1 adds 32,031,488 query-workspace bytes | memory | Both keep CPU input; sampled device peak is not exact owned peak; CPU RSS unknown |
| G3-STAGE | partial | Fixed32 diagnostic pool changes by at most 0.0007 pp per query/prefix over A checkpoints | updates/STAGE_ROBUSTNESS.json | Descriptive, separate process, no B/long-update stability gate |
| G3-KNN-LIMIT | inferred | Unchanged kNN dominates measured D0 event time and limits current total savings | operation attribution | Measured component shares, not a causal new kNN experiment |
| G3-ADMISSION | inconclusive | UNCLASSIFIED: ratio 0.855934141 >0.85; stop without B | CONTRACT.json; analyze.py; DECISION.md | Six wins/CI do not waive the primary threshold |
| G3-B | unknown | Frozen update-heavy B has no GPU evidence | timing/TRACE_B.json | Must not report zero errors or latency |
| G3-THESIS | rejected | No current paper-thesis promotion; partial-distance and cheap-update principles already precedented | PRIOR_ART.md; NOVELTY_CLOSURE.md | No distinct non-incremental mechanism/same-contract external advantage |

No claim for dynamic DRAM reduction, progressive kNN, universal GPU-tree redundancy, 10k queries, 100k events, 1B vectors, capacity rollover, CUDA Graphs or production dispatch is supported by this campaign. Preserve current measurements and failure records; do not relabel an incomplete gate as GO.
