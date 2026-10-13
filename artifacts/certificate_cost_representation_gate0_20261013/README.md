# Certificate-cost representation Gate0 — stopped before training

**Prior-art gate: SUBSUMED (broad core thesis). Execution: STOP_BEFORE_TRAINING.**
The plan's admission-only final label is `NO_GO_CERTIFICATE_TRAINING`; its
empirical three-way quality/cost gate is **NOT_EVALUATED**, not a failed result.

The [prior-art audit](PRIOR_ART.md) identifies a direct trained-prefix exact-search
precedent, HN. An independent derivation and 1,600 exact-rational descriptor pairs
show that its stated fixed-energy bound translates into prefix squared-L2
rejection; 6,400 strict-cutoff checks, including equality, pass.

**This does not prove identical losses or superiority.** HN constrains energy;
the proposed softplus uses another training objective. The fixture establishes
a bound-level overlap on the HN subspace only. Whether P1 beats MRL while retaining
quality remains unknown. A comparison only against MRL would not establish the
claimed distinction from this newly found prior art.

## What executed

| Gate | Status / denominator |
|---|---|
| Primary-source review | Completed; paper/version and official-code identities retained |
| Algebraic cheap test | 5 dimension/prefix shapes ×5 energy fractions ×64 synthetic pairs; 0 identity mismatches / false rejections in the fixture |
| CIFAR-100 training/evaluation | **Not executed**: 0 training processes, 0 measured CIFAR queries |
| GPU kernels/system integration | Not implemented; 0 GPU/NCU starts |
| Performance / quality gate | Not evaluated; metrics and seed comparisons are null, not zero |

The requested CIFAR-100/ResNet-18/512D design, all three seeds and lambda choices
are retained in CONTRACT.json and training/*.json. No optimizer, epoch budget,
split, margin or training cutoff schedule is silently invented or launched after
the novelty stop. The open operational/decision issues are explicitly recorded.

There are no training curves or quality/cost plots: inventing them for an early
stop would be misleading. [Figure status](figures/README.md) records their absence. The
quality, certificate and mechanism JSON files are explicit not-executed receipts.
Existing Gate3/Gate4 results, raw data, checkpoints, manuscript, foreign processes
and GPU settings remain unchanged.

Read [decision](DECISION.md), [claim boundaries](CLAIM_EVIDENCE.md),
[reproduction](REPRODUCE.md), [validation scope](VALIDATION.md) and
[execution closure](evidence/EXECUTION_CLOSURE.json).
The next admissible action is a new, genuinely distinct design/contract—not an
automatic training job or continued loss tuning under the rejected broad thesis.
