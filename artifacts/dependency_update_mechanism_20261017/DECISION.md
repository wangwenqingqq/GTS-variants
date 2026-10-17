# Decision: B — ENGINEERING_STRONG

## Implementation status

The six-way bounded study completed all 368 registered GPU targets with no failed
attempt or retry. Complete query/state, sanitizer, static-query identity, physical
activity binding, independent raw closure and derived-result reconstruction
passed. This is an experimental artifact, not a production dispatch change.

## Mechanism status

- **Measured structural fact:** 1M Recent4 eliminates 43.8377% of native row
  assignments in the performance trace; W2 eliminates none.
- **Measured engineering fact:** generic DSE gives 2.736–2.874x paired complete
  service speedup over the same-campaign Native path across four fixed traces.
- **Measured nonexclusive increment:** relative to generic waves on the same
  standard-library executor, Recent4 composition reduces service 8.61%
  [7.95%,9.22%] and Delete ACK 29.09% [26.97%,30.21%]. This bundles row elimination,
  wave collapse and different CPU planning; it is not a pure byte-effect estimate.
- **Rejected tested Tail specialization:** generic propagation and Tail generate
  exactly the same final plans, while Tail+Thrust increases complete service
  time 2.58%–6.40% and Delete ACK 9.01%–22.67% versus generic DSE+Thrust.
  All four paired intervals exclude a Tail win. Construction/certificate costs
  are higher; destructor and remaining ACK costs are charged, not hidden.
- **Inconclusive executor increment:** custom/Thrust same-Tail-plan service
  intervals cross one for every family. A kernel-level win is not established
  as a full-service benefit.

## Thesis impact

A-level `MECHANISM_SUPPORTED` is **not admitted**. This is not merely “similar to
DSE”: a concrete arbitrary-copy generic implementation reproduces the exact
assignment set and is faster under the same strict service contract. The bounded
prior-art audit did not establish an identical entire service elsewhere, but
absence of such a finding is uncertainty, not a novelty certificate. No manuscript
claim or distinct ownership-algorithm thesis is promoted.

C-level structure without payoff is not the whole story: generic composition does
pay in the dense synthetic trace. D-level production applicability remains
unknown because no real application update trace was supplied; it is not asserted
that every application lacks dependence. B is the appropriate primary label.

## Retained negative evidence and reopen conditions

| Target | Counterevidence and added costs | Boundary / reopen condition |
|---|---|---|
| Tail planner vs generic DSE | Same final plans; charged construction/destructor costs; service regressions in all four fixed traces | Do not rescue algorithm novelty with another indexed-copy kernel. Reopen only for a concrete nonincremental mechanism difference and cheap same-contract falsification. |
| Safe CUDA copy batching | W2 Host copy APIs fall 500,000→977 but GPU memcpy activities remain 500,000; service CI crosses parity | Not a universal API rejection. Reopen if a new implementation actually changes device granularity under the same semantics. |
| Custom final-row executor | Same-plan service intervals cross parity | Reopen only if a newly measured executor bottleneck can change the full denominator, not to package a tiny kernel win as novelty. |
| High churn as dependency proxy | Uniform-live re-deletes 106,972 fresh occurrences but eliminates only 131 assignments | Measure within-batch physical dependencies directly; do not label event count as distinct-original replacement fraction. |

## Next action

Measure the within-batch cancellation distribution in **real application traces**
and whether generic composition pays for its complete service cost. This study
does not automatically authorize another GPU matrix or a different thesis.

Confidence is strong for these fixed traces/processes and limited for other
hardware, datasets and application distributions. All intervals are pointwise,
process-conditional and based on six matched rounds, not six workload seeds.
