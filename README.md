# Original GTS experiment deliveries and evidence alignment

This publication branch contains only task-owned experiment deliveries. It has
a fresh, standalone commit chain and does not inherit older repository traces,
data or history. Existing repository branches, history and visibility are not
changed. This is not a remediation of any exposure in older public history;
affected credentials still require revocation or rotation by their holder.

## Round 1: original GTS versus native GPU Faiss-IVF

- [Results](diagnostics/native_knn_faiss_ivf_20261003/RESULTS.md)
- [Reproduction and validation scope](diagnostics/native_knn_faiss_ivf_20261003/README.md)
- [Claim/evidence ledger](diagnostics/native_knn_faiss_ivf_20261003/EVIDENCE_LEDGER.md)

The frozen development-selected 100% points miss final100% on all eight shapes.
The later fixed all-list IVF control reaches100% tie-aware recall, with a
non-paired timing comparison and deterministic tie-breaking exception on GIST.
No production GTS++ improvement is measured here.

## Round 2: original GTS baseline recheck

- [Results](diagnostics/original_gts_compare_20261003/RESULTS.md)
- [Replay and pending comparator identity](diagnostics/original_gts_compare_20261003/README.md)

Four single-process original-GTS checks pass full-ID/field validation at K8,
B1/32, GIST/Deep1M and32 already-seen queries. This is a baseline-only pilot;
an optimized comparator had not yet been measured at that checkpoint. The
later P7 static executor and U0 update validation are linked below; neither is
a unified range/kNN/update keeper.

## Next campaign: mandatory 10,000-query comparisons

- [Detailed 10k stability and complete-workflow experiment plan](diagnostics/next_campaign_20261004/PLAN_10K.md)
- [Execution recovery: failure isolation, workflow attribution, and real 10k comparisons](diagnostics/next_campaign_20261004/EXECUTION_RECOVERY.md)
- [Later P7 static kNN evidence](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/unified_knn_e2e_20261003/RESULTS.md)
- [Later original-GTS U0 update evidence](https://github.com/wangwenqingqq/GTS-variants/blob/7bce3679c3e32e77fa25cf7842805926509e1412/diagnostics/claim_closure_20261003/RESULTS.md)

The new document is **plan only**, not a completed GPU campaign. It requires
original GTS, a qualified stable query version, native Flat, native IVF and
native CAGRA on actual fresh10k queries, with matched B1/B32 and separately
optimized bulk batching. It also covers range stability and every operator in
query/insert/delete/compaction/rebuild. Static query qualification, native
multiset updates and future new-vector arrivals remain separate contracts.

The recovery document amends execution roles and failure isolation after the
published qualification stop at `86cb65f`. It preserves the frozen plan and
negative results; it is not a new GPU run or a completed comparison. Native
IVF/CAGRA verification must not depend on repairing a rejected Flat adapter.

## Evidence alignment: query and update lifecycle

- [Extended P4 evidence ledger](diagnostics/batch_tree_inheritance_20261002/EVIDENCE_LEDGER.md)
- [Curated-source provenance](diagnostics/batch_tree_inheritance_20261002/CONVERGENCE_SOURCE.json)

This extension links existing public reports, retains external counterevidence
and version-specific qualification gates, and does not add a new GPU run.
Mechanism experiments are complete at their registered scopes; a unified
search/update candidate is not complete.

## Publication provenance

[PUBLICATION.json](PUBLICATION.json) identifies the original local checkpoint
and exported path. Experimental sources, contracts, numeric results, curated
evidence and collection hash manifests are preserved; only publication-status
prose is adjusted for this standalone branch.

Original GTS is attributed to [ZJU-DAILY/GTS](https://github.com/ZJU-DAILY/GTS),
revision `3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`. Upstream headers are not
redistributed by these directories; preparation verifies caller-supplied source
against pinned hashes. Existing rights are preserved and no new license is
imposed on upstream or derived source. Dataset/index/result binaries and raw
profiler environment captures are excluded. Replay the delivered fixed queries;
new development campaigns may need the prior-query inventory recorded in their
metadata and must not silently change exclusions.
