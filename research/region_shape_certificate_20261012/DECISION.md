# Decision: PROJECTED_SHAPE_CERTIFICATE_KILLED

## Gate result

All three new shapes have negative hard6 gains at both ancestors and at the leaf.
K1 passes (every new L3/L4 gain <5pp); strong, signal and leaf-only gates do not.
Exact Fraction comparisons reproduce this decision. An80B ellipsoid is marked
metadata-heavy, but the terminal K2 condition requires >128B and is not applicable
to a frozen matrix whose maximum is80B. No >128B candidate was invented.

| Shape | L3 hard gain over AABB | L4 hard gain | L5 hard gain |
|---|---:|---:|---:|
| Centroid ball | -22.8859pp | -28.4997pp | -26.0680pp |
| Approximate minimax ball | -22.5336pp | -24.3016pp | -19.5157pp |
| Diagonal ellipsoid80B | -14.9832pp | -15.3949pp | -9.9029pp |

All safety requirements pass, including full stored-shape coverage and all384
independent original-vector pairs. This is a measured mechanism rejection for
these explicit replacements, not a numerical failure disguised as a kill.

## Strongest supporting evidence and attribution

The replacements are not systematically tighter than AABB. Hard6 L4 median dead
gaps are0.658675 AABB,1.330130 centroid ball,1.175170 minimax ball,0.798996 ellipse.
At L4, centroid/minimax create no new hard-region threshold crossings and lose
1,708,700 /1,457,000 object-query prunes. Ellipse adds200 but loses923,200, a net
loss923,000 object-query prunes against the identical hard denominator5,995,500.
Do not equate a smaller enclosing ball radius with better query selectivity.

The point-set diagnostic is separate from the three-shape result. Its optimistic
hard6 ceilings are1,780,000/5,960,000=29.8658% at L3 and
2,371,500/5,995,500=39.5547% at L4. For ANY enclosing region in this fixed PCA8,
Euclidean distance to that region cannot exceed distance to its contained nearest
projected point. Thus even an ideal enclosing shape cannot pass the45% ancestor
gate on these frozen queries. This is a theoretical containment inequality plus
measured finite-workload projected distance upper envelopes, not a fifth deployed
certificate and not a universal upper bound on linear representations.

Canary359924's L4 ceiling is103,000/999,200=10.3082%, versus AABB70,500/999,200=
7.0556%. It cannot achieve the proposed30% rescue through this fixed Euclidean
enclosure mechanism. Keep canary distinct from a result-selected worst query.

The all-pair hard6 L4 summed-distance decomposition attributes85.0319% of the
AABB distance-gap sum to original-to-projected nearest-distance loss. Remaining
14.9681% is geometry plus certificate numerical margin, with the projected-error
interval width reported separately. This is not CPU/GPU/runtime attribution or
an alignment-gap percentage; the components sum using signed values without
clipping, not nonadditive medians.

## Material caveats and reopen condition

- Minimax uses one predeclared64-step heuristic, not an exact optimal sphere;
  failed approximate centers do not kill every ball construction.
- The ellipsoid is diagonal and centroid-centered, not full covariance/MVEE.
- Only eight queries/six hard queries, P2 partition and this particular PCA8 are
  covered. No global bound on alternate projections or nonlinear certificates.
- No GPU, timing, full search/recall validation, formal256 or end-to-end speedup.
- Ball48B is lower metadata cost but loses pruning; ellipse80B violates the64B
  matched budget. Efficiency per byte is only a relative proxy.

Do not revive these replacements unchanged or port them to GPU as a presumed
speedup. Reopen for an independently novel mechanism escaping the fixed PCA8
distance ceiling, with new predeclared contracts and decisive same-contract
evidence. Changing a projection is a new experiment, not repair of this result.

## Execution/publication checkpoint

Attempt1's raw results and source archive are retained privately, unvalidated
because of receipt/wording audit findings. Attempt2 corrects those issues but is
superseded by final attempt3, which explicitly reconstructs independent signed
AABB endpoints too. Accepted attempt3 rebuilds and remeasures all12cells and all
384 pairs; all metadata/truth/bound arrays and complete summaries are bit-identical
to attempt2. No formula, sample, threshold or gate was selected after seeing
outcomes. The accepted source
freeze and raw hashes are in evidence. Publication includes only this task's
code, curated derived statistics, proofs/counts and rendered figures; raw vectors,
metadata caches, private placement/invocation and other historical work are not
part of the upload. Commit and remote verification are reported at delivery.
