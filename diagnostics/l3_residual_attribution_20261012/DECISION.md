# Decision

**PIVOT_DOMINANT: passed for both captured rebuilds under the frozen diagnostic
gate.** Residual churn concentrates in changed-pivot L3 subtrees; this is not an
isolated causal measurement of the L3 pivot's contribution.

| Gate | R1 | R2 |
|---|---:|---:|
| Changed-pivot share of residual common-object churn >=90% | 90.027580% | 92.268289% |
| Changed-pivot share of residual leaf churn >=90% | 90.026889% | 92.266542% |
| SAME within-group leaf churn <=10% | 3.941417% | 3.208044% |
| UNKNOWN parents | 0 | 0 |

**Material caveat: R1 barely passes.** Its changed-pivot object count exceeds
90% by only 80 objects; the leaf count is 26,115, versus the integer minimum
26,108. Thus the result is contract-specific, not strong evidence that 90% will
hold on new workloads. PRE-cohort object regrouping also passes (261,148/290,070),
so migration assignment is not what makes the POST-object estimator pass.

Same-pivot L3 retained objects have no encoded-key bit changes or common-only
relative-order changes. Full rank drift is at most 2 / 1 positions, with only
260 / 204 unique boundary crossings (0.03543% / 0.02830%). Their remaining leaf
churn is not zero: selected L4 pivots still change in 260 / 205 children. In a
descriptive hierarchy-local regrouping, these changed-L4-pivot children contain
2535/2893 and 2047/2313 of SAME-L3 changed leaves. This is further concentration,
not a new causal intervention or proof that boundaries can be ignored.

## Next action

Proceed to a **separate prior-art Gate 0**, before designing or implementing any
update-stable organization: dynamic VP/MVP trees, incremental metric trees,
persistent pivot/partition decisions and stable hierarchical partitioning.
The candidate thesis concerns maintaining partition-decision identity under
sparse updates, not merely freezing a pivot. Stop if prior work subsumes the
core idea without a non-incremental mechanism and decisive same-contract advantage.

Do not extend C4, freeze-all, modify production, or assume a performance gain.
Stable L3 pivots alone do not make every leaf stable: SAME-L3 leaf churn remains
3.94% / 3.21%, and even SAME-L4 children retain 358 / 266 changed leaves.

## Preserved negative evidence

R2 C1 changes 99,986 leaves versus C0 99,985. Root-only stabilization is
insufficient and inconsistent, not noise. The previous strict monotonic gate and
<=20% strong gate remain unmet; C3 still changes 29.008% / 29.909% of leaves.
This diagnostic pass does not retroactively change those decisions.

Scope: two frozen rebuilds, one N/D/dtype/tree contract, no external index or new
dataset, no latency, query correctness or production gate. Reopen attribution
after a changed workload, correspondence rule or structural contract; re-freeze
the estimator first. No new evidence is inferred for all GPU trees.
