# Experiment record

| ID | Hypothesis | Contract | Keeper/candidate | Expected delta | Invariants | Evidence | Decision |
|---|---|---|---|---|---|---|---|
| gtspp_20261011_fixed3_current_par_full | Small canonical range leaves waste CTA/warp execution granularity | CONTRACT.json | P0/P1/P2 | range CTAs to ceil(leaves/3); exact distance work | BASELINE_AUDIT.md | pending | hypothesis |

Frozen before implementation and before new GPU runs. See DESIGN_CARD.md for
ownership, phase live state and ready edges. Failed attempts are retained and
never rewritten into passes.

Build attempt 1: failed static shared gate; see AMENDMENT_1.md. GPU processes: 0.

Qualification completed21 original GPU processes; mutable-log closing failure retained.
AMENDMENT_2 performed offline recovery without replacement. Remaining27 main processes
and 1 NCU probe completed. All gates closed; see evidence/CLOSURE.json and RESULTS.md.
Status: accepted scoped range prototype; thesis/external-baseline promotion withheld.
