# Build-time certification: D0 differentiation

**Decision: D0_KILL. The only complete retained B1 (Z) is graph-equivalent to strongest ordinary C2. Stop this differentiation thesis before implementation.**

The strongest control already uses the native physical-row permutation and child intervals; no extra million-entry owner map, endpoint permutation, or standalone reduction launch is necessary. C2 can delete a coordinate reread, but still produces the full directed certificate and materializes its level endpoints. This is a design/novelty decision, **not** a measured performance rejection or a proof that every future certificate algorithm is impossible.

Plan dated 2026-10-12; record completed 2026-10-13 (Asia/Shanghai). Parent commit `04c4e0d7d891ce348c2e29bbd5a4e65bf0834b6a`. Task limits: **GPU processes 0, CPU/GPU prototypes 0, timing runs 0**. No kernel/source implementation, external rerun, paper edit or hardware operation. Contract was written before candidate selection. Physical-row identity in that contract means the sidecar address in this frozen compact base/build, not an immutable identity across rebuild compaction; there is no cross-rebuild certificate cache.

## Record

- [B0 dependency/arithmetic/lifetime graph](B0_GRAPH.md), [strong C2](C2_GRAPH.md), [one retained B1 Z](B1_GRAPH.md).
- [X/Y/Z table and selection](CANDIDATES.md), [scoped numerical kill test](NUMERIC_KILL_TEST.md).
- [Source-level cost model](COST_MODEL.md), [mechanism-only primary-source mini-gate](PRIOR_ART_MINI_GATE.md).
- [Decision and reopen conditions](DECISION.md), [prototype stop record](NEXT_PROTOTYPE.md), [claim/evidence calibration](CLAIM_EVIDENCE.md).
- [Contract](CONTRACT.json), [machine graphs](evidence/GRAPHS.json), [costs](evidence/COSTS.json), [decision](evidence/DECISION.json), [keeper hashes](evidence/KEEPER_SOURCES.json), [primary hashes](evidence/PRIMARY_SOURCES.json).

## Validate the record (no CUDA required)

From the repository root, Python 3 standard library only:

```sh
python3 research/build_time_certification_d0_20261012/scripts/validate.py
python3 research/build_time_certification_d0_20261012/scripts/validate.py --check-local-sources
```

The first checks the public record, normalized graph equivalence, integer accounting, source-linked inherited counts and exact rational witness; it is not a CPU distance/index prototype. The second additionally checks retained private keeper and downloaded primary bytes. Those private copies, original plan and publication receipts are ignored under `local/`, not distributed. A clean public checkout can validate the record, but cannot rerun unpublished dataset captures or establish runtime correctness/performance.

Inherited overlap comes from the hash-pinned [construction/refit diagnosis](../../diagnostics/construction_refit_pair_overlap_20261012/README.md), not a new GPU run. Prior generic/GPU-only novelty rejection remains intact in the [previous Gate 0](../build_time_certification_gate0_20261012/README.md). Publication is confined to this directory's named record files; no default-branch merge is authorized.
