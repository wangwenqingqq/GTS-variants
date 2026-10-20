# Fixed-batch future-blind Gate 1: input freeze checkpoint

**Gate 1A only.** This directory freezes 128 new query identities, radii, B2/B4/B8
membership, evaluation rules and stopping conditions. The accompanying execution
checkpoint replays the original 32 development queries. No held-out distance,
query order, rejection depth, oracle path or candidate result is generated.
No GPU, reusable index, service or manuscript work is included.

## Material clarifications

- The parent has **one radius**, FP32 bits `0x3f34a3d8`, or
  `0.705625057220459`; squared threshold `0x1.fddb427319000p-2`.
  Its empirical distribution is a point mass, not a tunable set of radii.
  Every new query inherits that value. A multiradius result is outside scope.
- FANOUT already serves every query with the same currently ready tile, even
  after earlier divergence. Merely adding "rejoin" does not define a distinct
  candidate. Candidate mechanisms and parameters are **not frozen yet**.
- For oracle cost `O in [L,U]` and positive saving `F-C`, conservative gap
  capture is `(F-C)/(F-L)`, not the optimistic `(F-C)/(F-U)`.
- These are held-out identities on the **same GIST1M snapshot**, not another
  dataset or an arrival trace. Database-row queries retain self-matches.

## Files and phases

`GATE1_CONTRACT.json` is the immutable protocol; `QUERY_SELECTION.json` contains
the 128 identities and all 112 batches: 64 B2, 32 B4, 16 B8. Identity-only seeded
hash sampling excludes all original32 IDs. One nested permutation is used for
all batch sizes. Selection never reads vector coordinates or outcomes.
`SOURCE_FREEZE.json` binds the executable checkpoint and inherited authorities.

`gate1a.py replay` exports the frozen vectors privately and replays the original
28 combinatorial cases using the unchanged Gate0 preparation, solver and checker.
No source-model cost is relabeled as measured DRAM or end-to-end latency.
The Gate0 artifact's historical weaker primary remains unchanged; **FANOUT** is
the prospective Gate1 control. B2/B4 strong residuals are 10.9277478194% and
23.4216703871%; B8 is unresolved and no evaluated feasible B8 schedule beat one
batch full scan in Gate0.

Next is Gate1B, not Gate2: design at most two genuinely distinct ready-only
candidates using old32 only, test frontier noninterference, then select **one**
primary candidate and freeze its implementation, all parameters and baseline.
Only then can a separately registered one-shot Gate1C read held-out features.
There is deliberately no held-out evaluation subcommand in this checkpoint.

All six B2/B4 conditions are conjunctive, including worst-batch loss and full
source cost versus a shared full scan. B8 is exploratory and not pooled into
the decision. Undefined intervals, missing evidence and information leakage
cannot be converted into a pass. A source-model GO would not establish novelty,
GPU speedup, stable cross-dataset compatibility, or profitable recipe indexing.

The prior-art admission remains the bounded CPU falsification in the
[Gate0 assessment](../fixed_batch_dag_gate0_20261019/PRIOR_ART.md), not a new
claim that shared-query plans or DAGs are novel.
