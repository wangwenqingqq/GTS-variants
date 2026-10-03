# Original GTS kNN experiment deliveries

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
