# Claim-evidence ledger

| ID | Exact scoped claim | State | Evidence / oracle | Counterevidence / allowed wording |
|---|---|---|---|---|
| E0 | Four standalone native controls reproduce saved construction order and every active TN/empty byte | measured | Native gates + prior pinned snapshots + closure | Says nothing about a production candidate |
| E1 | For both fixed POST live sets, C2 reduces exact leaf churn by >=30 pp | measured | RESULT.json, full inverse-pack closure, independently verified actual decisions | 59.734% / 58.533% churn remains |
| E2 | C3 preserves 70.992% / 70.091% of PRE leaves | measured | 70,992 / 70,091 exact sorted-occurrence signatures of 100,000 leaves | Not <=20% churn; no runtime saving measured |
| E3 | Early pivot/order decisions contribute substantially to recursive structural amplification here | inferred | Native → early-pivot interventions; localization to next unfrozen level | Root-only R2 does not help; not the sole cause or a universal tree property |
| E4 | Strict all-dose monotonicity holds on both rebuilds | rejected | R2 C1=99,986 changed leaves vs C0=99,985 | Retain the one-leaf negative result; no noise waiver |
| E5 | Counterfactuals are production-correct, faster, or novel | unknown | No query/Graph/sanitizer/stress/performance/prior-art mechanism evidence | Prohibited wording: speedup, production stable-tree solution, novel fixed-pivot mechanism |

Scope: N1M D960 FP32, current frozen P2 construction, two specific rebuild windows on one verified SM120 GPU. Contracts and provenance are in CONTRACT.json and evidence/REMOTE_CLOSURE.json. No generalized claim about every GPU tree is supported.
