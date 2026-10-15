# Claim–evidence ledger

Experiment: `GTSPP_20261015_DYNAMIC_QUERY_AWARE_EXACT_GPU_SEARCH`.
Parent: `11b401e551d42657e10c55765afb7b8a0ed7ac9e`; campaign date2026-10-15.
Hardware: one initially idle RTX PRO6000 Blackwell Server Edition/SM120,
matched NUMA, driver590.48.01, CUDA13.1, NCU2025.4.1.0; no settings changed.
Private placement/commands remain outside Git. CONTRACT and INPUT_IDENTITY bind
source, binary, input/reference, selected-function SASS and frozen analysis.
`RAW_MANIFEST` identifies original evidence; `RAW_CUSTODY` distinguishes copied
measurements from externally retained immutable inputs. No manuscript is edited.

| ID | Exact allowed claim | State | Scope / denominator | Evidence | Material counterevidence / limit |
|---|---|---|---|---|---|
| D1 | Frozen PDX retains roughly20.55–21.10% query advantage over S1 through the five W2 windows | measured | GIST1M/D960/B1,32 fixed repeated queries,6 process means/window | TIMING W2 comparisons/windows; PRIMARY_PROCESSES; FigureA | Synthetic feature permutation, one radius/query population; not all drift |
| D2 | At50% replacement/11.4168% true mean drift, frozen PDX query ratio is0.790609 versus S1 | partial | Same-window median ratio; paired95%CI [0.788303,0.792911] is a separate estimator | INPUTS; TIMING; DECISION table | No failure threshold located; not proof none exists |
| D3 | Frozen PDX kernel DRAM rises0.75% (0.780090→0.785922GB/query); its advantage over S1 narrows30.30%→26.53% | measured | All query kernels,one NCU process/cell,32 queries/window,no DMA/processCI | TRAFFIC; NCU_S2_STALE_W2; NCU_S1_W2; FigureB | Small physical weakening despite stable latency advantage; source coordinates are not DRAM |
| D4 | Ordinary eager maintenance adds218.117529ms W2 update tax while extra query savings are0.448679ms | measured | Medians of6 matched update/query total differences; update taxCI [202.355755,241.455177]ms | TIMING incremental_update_tax; PRIMARY_PROCESSES; SUMMARY; FigureC | Not isolated kernel cost or unavoidable maintenance; up-to512-row batches |
| D5 | Frozen PDX lowers W2 segmented service1.89%; eager PDX is10.49% slower than S1 | measured | Ratios of process medians;6/6 wins or6/6 losses; separate pairedCIs | TIMING; service primary records; FigureD | Excludes setup/client-input storage/offline validation/context teardown; not full process wall |
| D6 | Updates occupy91.14% of frozen W2 service; delete ACKs dominate insert ACKs | measured | Median of6 within-process shares; separately summarized kind totals | PRIMARY_PROCESSES; SUMMARY | Does not identify the CPU/API/GPU cause; not same denominator as arithmetic stack means |
| D7 | Eager selected statistics kernels are low-throughput on this GPU | partial | Independent profile;199.271ms diagnostic sum,1.751% peak SM throughput/19.076% active-warps duration-weighted | MAINTENANCE; MAINTENANCE_NCU | Not service occupancy, public latency or proof of optimal implementation |
| D8 | Complete members/fields, actual ownership and full final-state checks passed for all117 registered processes | measured | All nonselftest formal+warmup outputs; internalFP64 bits in qualification; bounded sanitizer/stress scope | QUALITY; QUALITY_RECEIPTS; STAGE_CENSUS; EXECUTION; private raw proofs | Public hashes/scalars do not re-execute private membership, every-byte target check, isolation or SASS |
| D9 | This stress does not establish a staleness-specific maintenance research gap | inferred | Negative hypothesis survives ordinary frozen-statistics control | D1–D6; PRIOR_ART; DECISION | Other datasets/shifts/query evolution may differ; absence here is not an impossibility theorem |
| D10 | The next cheap discriminating question is update-critical-path attribution | inferred | Recommendation,not a measured new mechanism or admitted S3 | D5–D7; service.cu delete/insert path | No extra GPU campaign is launched by this artifact; ordinary batched control comes first |

## Retained negative result and reopen condition

- **Target:** a dynamic-specific failure of known query-aware exact ordering.
- **Keeper/strong control:** same-campaign S1 plus frozen PDX (not an expensive
  full-statistics recomputation strawman).
- **Tested added mechanism:** ordinary eager sum/count updates, actual deleted
  device-vector gathering, mean delivery before ACK,1,979,648B extra device
  statistics storage; all update/synchronization costs charged.
- **Observed effect:** query advantage survives frozen statistics; eager W2 tax
  overwhelms its incremental query saving and regresses total service. Small
  frozen logical/physical weakening is retained, not rounded away.
- **Diagnosis:** update-heavy service dilution and a losing eager policy, not
  evidence that refreshing is necessary or universally expensive.
- **Do not revive:** do not present another ordering heuristic, faster mean
  refresh, generic dynamic support, or this one-data synthetic stress as novelty.
- **Reopen:** a preregistered shift must reproducibly defeat frozen ordering and
  cheap ordinary controls on the same complete service contract, followed by a
  fresh prior-art/novelty gate. New hardware/shapes/concurrency require new gates.

Compilation, selected SASS equality, sanitizers, finite stress, NCU traffic,
paired service timing, public scalar reconstruction and remote publication
are separate states. None substitutes for a missing other state. Formal10k
queries/process, the older100k-workflow contract,1M–1B dataset scaling and
production/concurrent/SLA robustness are not claimed by this delivery.
