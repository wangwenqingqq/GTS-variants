# Decision and claim-evidence map

## Frozen rule outcome

**CERTIFICATE_ROUTE**, on the pooled visited-object estimator fixed before
measurement:

| Metric | Exact count / denominator | Value |
|---|---|---:|
| M1: certificate headroom | 6,101,120 / 7,167,340 visits | 85.123909% |
| M2: truth-retained partition floor | 600 / 7,167,340 visits | 0.008371% |
| M3: perfect leaf-truth residual | 600 / 8,000,000 query-object pairs | 0.007500% |
| Threshold-only headroom among visits | 1,065,620 / 7,167,340 visits | 14.867719% |

M1 exceeds 30% and is at least twice M2; neither Route B condition holds.
Seven queries independently meet A. Query 90208 is INSUFFICIENT_EVIDENCE under
the per-query rule, because its M1 is 17.469203%, not because it favors B.
No rule, query, epsilon, margin, or estimator was changed after measurement.

## What this does and does not diagnose

**Measured:** most pooled visited leaves contain no object within U*, yet even
the current full path bound at U* cannot reject them. Six high-visit queries
have M1 at least 96.770198%; merely supplying the exact answer radius is not
enough for these cases. Current-certificate information loss is therefore real
under this fixed terminal partition and exact arithmetic.

**Material exception:** on query 90208, 82.521767% of actual visited work is
threshold-only headroom, not new-certificate headroom. Query 660835 is also
threshold-sensitive (55.485209% of visits). A blanket assertion that candidate
quality is irrelevant is contradicted by this subset. The negative memo/G2
results from the previous campaign do not exclude every possible candidate
strategy.

**Structural limit:** every leaf has ten objects. All eight queries have exactly
eight objects at/below U* and only one object equal to the K-th squared score.
Consequently a perfect leaf oracle has residual at most 80 objects regardless
of many aspects of partition quality. Observed residuals are 70 or 80, in seven
or eight leaves. Calling this a general exoneration of partition/layout would
overstate the experiment. In particular, this does not test the quality of
larger ancestor regions or the cost of expressing their geometry compactly.

**Causal scope:** the intervention freezes the original terminal object sets
and replaces a bound with exhaustive object truth, while conditioning on an
independent U*. It establishes oracle count headroom, not an implementable
counterfactual. The larger question of why the full 32-query mean is 94.927844%
is only partially diagnosed by this selected eight-query slice (89.591750%).
No population confidence interval is inferred from stratified selection.

## Three separate decisions

1. **Implementation:** offline exporter/analyzer passed its declared gates;
   no new GPU/index implementation was produced or admitted.
2. **Mechanism:** the native certificate leaves substantial conditional
   pruning headroom. A stronger *cheap* certificate remains **unknown**.
3. **Thesis:** no novelty or speedup claim. Generic oracle truth and multi-pivot
   bounds are not a new research contribution merely by being packaged here.
   A nearest-prior-art novelty kill test is required before promoting a new
   mechanism or starting expensive GPU work.

## Claim-evidence map

All rows refer to `region_truth_diagnosis_20261011`, based on b800019, verified
2026-10-11; hashes and exact contracts are in the adjacent evidence directory.

| ID | Claim and scope | Status | Evidence / gate | Counterevidence and allowed wording |
|---|---|---|---|---|
| RT1 | M1=85.123909% of 7,167,340 visits on the frozen eight queries | measured | aggregate/per-query CSV; exact native replay; 128 independent region checks | Seven of eight meet A. Say conditional oracle headroom, not measured scan elimination. |
| RT2 | Existing bounds at fixed U* leave 76.271500% of N on this subset | measured | exact path-bound classification; same tree and margins | Threshold alone explains most visited work for two selected low-visit queries. Do not generalize the fraction to dev32. |
| RT3 | Perfect leaf truth leaves 0.007500% of N | measured | 60 retained query-leaf pairs, 600 weighted objects; independent score gate | Leaves contain only ten objects. Do not infer that partition quality is good. |
| RT4 | Perfect residual is at most max-leaf-size × count(score<=K-th)/N | theoretical | ownership invariant and tie-aware counting; measured per-query count=8 | Conditional bound, not deployable speedup. |
| RT5 | An affordable 16/32/64-byte certificate removes this work | unknown | no evidence | No new metadata or certificate computation has been implemented/measured. |
| RT6 | This explains CPU load, CPU/GPU I/O, all GPU trees, or all 32 queries | partial | selected G0 leaf-work decomposition only | No new resource profile, traffic measurement, or cross-index comparison. |
| RT7 | Region size drives the retained fraction | inconclusive | size audit: all 100,000 leaves are size 10 | Figure 4 has no x variation; a size-effect claim is unsupported. |

## Next action, not executed in this round

Only after a novelty check, propose a bounded C0/C1/C2 offline cost/pruning test
using the same inputs and exact safety contract. Include certificate bytes per
region, query-time pivot work, bound evaluation work, and avoided distance bytes;
compare incremental savings **against the same current-certificate radius**,
not against an intentionally loose radius. Preserve the threshold-only term.

Stop if C1/C2 cannot remove at least the plan's 10% theoretical work threshold;
freeze its exact denominator before collection. Even if counts pass, no GPU
implementation promotion until metadata/evaluation cost is plausibly below
saved work. Do not use the oracle M1 as the prediction for a realizable scheme.

Reopen partition diagnosis if upper-level or different-size region evidence
shows large truth retention, or cheap safe summaries fail despite this oracle
headroom. Do not keep extending a subsumed certificate mechanism merely to
rescue a paper narrative. C1/C2, repartitioning, formal256 and 10K remain unrun.
