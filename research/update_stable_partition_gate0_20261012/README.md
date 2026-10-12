# Update-stable partition decisions: Prior-Art Gate 0

**Decision: KILL the generic stable-partition thesis, not GTS++ as a whole.**
The proposed mechanism is already substantially present in dynamic metric
indexing: retain historical decisions/state, admit updates locally, and repair
structure under an explicit condition. EGNAT's ghost hyperplanes and dsa-tree's
thresholded fake-node cleanup are the strongest controls. A GPU suffix, a new
churn measurement, or combining familiar policies does not establish an
independent mechanism. See [the scoped decision](NOVELTY_DECISION.md).

**Material caveat:** this is a literature-based conceptual substitution test,
not proof that either prior implementation can be ported unchanged to packed
GTS, or that it meets GTS's quality/maintenance targets. EGNAT's tolerance-based
quality rebuild is a proposed option rather than an evaluated calibrated policy.
The present evidence cannot rule out an independently specified GPU co-design.

## Frozen scope and result

- Baseline: `9da7faa63fce8d01b2323fefd56ffbac6b24c4c8`.
- [Contract](CONTRACT.json): CPU/web only; **GPU processes started = 0**.
- Reviewed: **14 primary papers + 1 pinned official source file**; four families.
- No kernel, GTS source, workload, threshold, paper prose, or GPU host changed.
- No latency/speedup/correctness experiment; existing L3 evidence only establishes
  motivation and attribution, not novelty or an isolated causal fraction.
- Search date: 2026-10-12. This is nearest-work triage, not an exhaustive survey.

## Read order

1. [Search scope and source limitations](SEARCH_SCOPE.md)
2. [Mechanism-ranked matrix](PRIOR_ART_MATRIX.md)
3. [Complete evidence cards](EVIDENCE_CARDS.md)
4. [Five nearest controls](NEAREST_WORK.md)
5. [Decision and counterarguments](NOVELTY_DECISION.md)
6. [Next-action boundary](NEXT_MECHANISM.md)
7. [Claim-evidence ledger](CLAIM_EVIDENCE.md)

Machine-readable [sources](evidence/SOURCES.json), [cards](evidence/CARDS.json)
and [decision](evidence/DECISION.json) retain scope, locators and hashes.
Downloaded papers, full extracted texts and fetch receipts remain outside the
publish set; no third-party source content is redistributed.

## Runnable integrity check

From the repository root:

```sh
python3 research/update_stable_partition_gate0_20261012/scripts/validate.py
```

This checks source/card coverage, metadata, document links, the baseline result
hash and the scoped decision. It does **not** automate the scientific judgment.
The [publication gate](PUBLICATION_GATE.md) states the exact upload boundary.

**Next action:** stop implementation of the current thesis. Triage range
traversal/verification or a genuinely different physical-maintenance mechanism;
do not initiate that experiment under this zero-GPU task.
