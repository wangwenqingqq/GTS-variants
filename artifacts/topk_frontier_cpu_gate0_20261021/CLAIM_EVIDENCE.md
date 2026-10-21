# Claim/evidence ledger

| ID | Claim | State | Scope/denominator | Evidence | Counterevidence/allowed boundary |
|---|---|---|---|---|---|
| T1 | Deletion can raise kth distance and reopen old strict-bound cutoff decisions. | measured | N4096,Q64,fixed ten-way tree,edit distance,targeted atomic deletes. | results/*/FRONTIER.csv,EPISODES.csv;full outputs under raw seal. | Not every replacement raises tau;integer ties matter. Fixed metric bounds themselves remain valid. |
| T2 | Ordinary saved-frontier repair matches the future-tau oracle in all eight cells. | measured | New edit calls,same saved-score cache/tree/cut. | COSTS.csv,QUERY_WORK.csv,SUMMARY.json. | Oracle is not arbitrary cross-query proof/index optimality;all new outputs already had cached scores,so cached-survivor initialization already gives the true final tau numerically. Low-cache unknown-threshold discovery is not stressed. |
| T3 | Large stale-node overlap implies reusable cross-query distance work. | unknown | Different query-conditioned computations. | No executing shared-certificate candidate. | Node/ID overlap alone does not prove sharing or performance. |
| T4 | The fixed-tree cached-score repair family is stopped by the near-oracle gate. | inferred | Both targeted episodes,both primary datasets;integer10*online<=11*oracle. | CONTRACT.json,results/SUMMARY.json. | Initial pair coverage89.25%/99.97%;not a bounded-memory/full-self-join rejection. |
| T5 | A new GTS++ mechanism beats the strongest ordinary baseline by5x end-to-end. | unknown | No candidate/native full comparison. | no evidence | Do not claim. GPU starts0,novelty NOT_ADMITTED,full performance NOT_EVALUATED. |
| T6 | Emitted output members/order/scores are correct under frozen exact top-k semantics. | measured | 60 method streams,81600 triples,10 exhaustive reference streams. | evidence/*PROOF.json,POSTPROCESS_TESTS.json,source/input/binary seal. | Full membership reference shares edit primitive;independent DP validates581 fixture pairs and5803 emitted score pairs,not all candidate memberships. |

Experiment:GTSPP_20261021_TOPK_FRONTIER_CPU_GATE0. Source provenance is SOURCE_FREEZE.json plus MANIFEST.json;environment is evidence/ENVIRONMENT.json. Raw evidence is sealed before postanalysis and retained privately. Public artifact validation and independently read remote commit verification are distinct delivery gates.
