# Early-pivot causal diagnosis

Initial registration state: designed; measurements pending at registration. Completed evidence is appended below. This is a counterfactual construction probe, not a production index or a novelty claim.

| Experiment | Hypothesis | Contract | Keeper / intervention | Invariants | Raw evidence | Decision |
|---|---|---|---|---|---|---|
| early-pivot R1/R2 | Freezing early split pivots preserves downstream leaf organization | CONTRACT.json | Frozen P2; C0, root-only C1, gated C2/C3 | Same POST FP32/live input, native arithmetic/sort/split; membership-based correspondence | Private complete replay audits and manifests | Pending at registration |

The causal unit is a selected split-pivot occurrence. The root TN.pid is -1; a split's selected pivot is stored on its children. Decision levels 0..4 are distinct from node levels 1..5. PRE includes the old published base, including tombstones. Comparisons retain both full PRE membership and common-live denominators.

## Design card

The kernel change is only a validated optional physical-pivot pointer load by thread 0 of each scoring CTA. The same pivot is selected in all tiles of a parent. The Host prepares overrides before launch and synchronizes through the existing fence. Native coordinate, key, sort, and nodeSplit code stays unchanged. No new shared state, barriers, warp ownership, launch dimensions, packing, query path, or production dispatch. Device override buffer has one int per allocated node; Host owns allocation/update/release. Existing scoring CTA owns shared pivot and output distance keys; existing nodeSplit owns children.

Phase live set / ready graph: Host membership correspondence -> override H2D complete -> scoring shared pivot -> existing CTA fence -> distance keys -> existing device fence -> unchanged Thrust sort -> unchanged nodeSplit -> existing fence -> Host audit. No useful-work reduction or performance win is predicted. Extra correspondence/capture work is deliberately outside any performance denominator.

## Gate 0

This tests a specific cause in an existing frozen index, not the novelty of fixed pivots. Stable-pivot design and paper drafting are prohibited here. A positive result must still pass a separate dynamic metric-tree / stable-partition prior-art kill test before mechanism work.

## Measurement gates

The initial six-process budget includes two PRE native replays to obtain exact level-wise keys/ranks/ties absent from old snapshots. PRE and POST C0 must match saved native construction state. Two C1 replays follow only after both pass. Additional C2/C3 doses need explicit immutable gate records. No end-to-end or profiler run is required or claimed.

## Pre-measurement repairs (retained privately)

A compile attempt failed on two differently typed variables sharing one C++ `auto` declaration. A subsequent launcher failed before executing the binary because the command used a relative executable name not in PATH. The complete logs, source copies, and failed-launch registration are retained. No GPU construction occurred in these attempts. Paths are now resolved before command construction. The root correspondence intersection count was corrected before the first admitted construction. The six actual initial GPU processes remain the declared budget; no failed evidence is relabeled as a pass.

## Completed experiment

C0 native PRE/POST: all four byte gates pass. C1: 84.875% / 99.986% leaf churn, including R2's one-leaf regression. The root partitions become almost identical under common-occurrence correspondence, but L1 selected pivots remain unstable. C2 was admitted by this rapid early-level divergence; it gives 59.734% / 58.533% churn, a >=30 pp reduction on both, so C3 was admitted. C3 gives 29.008% / 29.909%, with 111/111 actual freezes admitted on both. Ten actual GPU construction processes, one failed pre-binary launcher; no extra service, profiler or GPU validation process.

Implementation status: structurally validated diagnostic. Mechanism status: substantial scoped causal support with a root-only exception. Thesis impact: strict full-dose GO and <=20% STRONG_GO are not met; no production or novelty promotion. Full byte input identity and actual device-pivot choices were independently closed on CPU. Raw order, rejected/root-only observations, complete keys and snapshots remain retained.

CPU-only postprocessing was extended without changing GPU construction: include inherited pivot in canonical topology exports, verify per-parent sort membership, separate full-membership identity from correspondence movement, label exact encoded-key ties correctly, replace repeated membership scans with an equivalent bool mask, and cover rank/boundary evidence at all five construction levels with sparse correspondence. Original C1/C2 summaries are retained; primary leaf/object and early-level pivot results are unchanged.
