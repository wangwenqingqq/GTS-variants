# Claim-evidence ledger

| Claim | State | Exact scope / denominator | Evidence | Allowed wording / counterevidence |
|---|---|---|---|---|
| Current P range has one-leaf CTA; FULL kNN differs | measured | pinned 25-file P | KEEPER_PINS, BASELINE_AUDIT | PAR range only |
| Fixed3 preserves exact work/results | measured | 128 ranges and full 336-event outputs; D128/D960 real unit | evidence/WORK, CLOSURE, UNIT_PAYLOAD_CLOSURE | all declared fixtures/processes; not arbitrary shapes |
| Fixed3 lowers leaf execution cost | measured |two reverse NSYS processes, inclusive leaf time | evidence/MECHANISM | about 2.1x leaf-local; not public latency |
| Current-P whole workflow accelerates | measured |six paired complete 336-event native.trace processes | evidence/FORMAL_SUMMARY | P0/P2=1.171413 [1.166083,1.175006],6/6 wins |
| Packing increment survives small CTA control | measured |same complete denominator | evidence/FORMAL_SUMMARY | P1/P2=1.173815 [1.169506,1.177715],6/6 |
| CTA shrink alone accelerates current P | inconclusive |same complete denominator | P0/P1 evidence | no confirmed benefit: 0.997954 [0.994428,1.001761] |
| Lane fill improves | inferred |counter membership plus source mapping | WORK / design |31.24996% ->91.81504% active-CTA slot ratio; NOT hardware occupancy |
| DRAM/L2/issued-warp savings or pure scheduling-only cause | unknown |NCU denied; query staging also changes inherently | MECHANISM | no such claim |
| External superiority / new thesis / universal GPU-tree result | unvalidated |not tested; prior-art mechanism | NOVELTY_GATE / DECISION | not promoted; prior strong external gap remains |

Provenance:2026-10-11, pinned sm_120 GPU1/NUMA0; exact measurement and continuation
registrations, all raw order and rejected attempts in the archived manifest.
Public UUID/recipe views differ only as documented in PUBLICATION_VIEW.
