# Dynamic query-aware exact GPU search

**The known PDX-BOND ordering survives this synthetic mutation stress with its
initial statistics frozen. The remaining W2 bottleneck is the update workflow,
not an observed staleness-induced loss of query advantage.** Ordinary eager
mean maintenance is correct but unnecessary for preserving the measured gain
here; its extra update cost outweighs its small additional query saving.

This is an exploratory failure-mode study, **not a new search algorithm, a
new ordering mechanism, or a manuscript submission**. The immutable parent is
`11b401e551d42657e10c55765afb7b8a0ed7ac9e`.

## Strongest control first

Same-campaign total-service medians, segmented **events + complete
service-owned release**; six independent processes/system/workload:

| Workload | S0 full safe (ms) | S1 progressive (ms) | PDX frozen (ms) | PDX delta (ms) | Frozen vs S1 |
|---|---:|---:|---:|---:|---:|
| W0 read-dominant | 430.469 | 192.821 | 154.036 | 155.534 | 20.11% lower |
| W1 mixed | 431.358 | 193.876 | 156.232 | 156.720 | 19.42% lower |
| W2 synthetic shift | 2030.696 | 1784.018 | 1750.230 | 1971.073 | 1.89% lower |

W2 frozen/S1 service ratio is **0.981061**, six/six paired wins; the separate
paired-geometric bootstrap 95% interval is **[0.973483, 0.981470]**. This is a
small but confirmed same-contract service benefit, not a kernel-only result.
W2 delta/S1 is **1.104850**, six/six slower; paired interval
**[1.090452, 1.111086]**. No favorable query-only number overrides that loss.

At 50% original-object replacement, true mean drift is **11.4168% relative L2**.
Frozen PDX still lowers query latency by **20.94%** versus S1: 0.785420 versus
0.993437 ms/query. Its retained relative gain is **101.90%** of its own
same-campaign zero-mutation advantage. This is not a proof of universal drift
robustness, and no failure threshold has been located. All-kernel query DRAM is
0.780090→0.785922 GB/query for frozen PDX: a **0.75% increase**, not perfectly
unchanged traffic. Its DRAM reduction versus S1 narrows from30.30% to26.53%,
while its query-latency advantage stays intact.

## Scope

- GIST1M: **1,000,000 × 960 FP32**, raw **3.84 GB**, B1 exact inclusive range.
- 32 fixed inherited query vectors, repeated across five windows; 160 formal
  queries/process plus eight initial excluded warmups.
- W0: 16 replacements,32 point updates; W1:64 replacements,128 point updates.
- W2:500,000 replacements,1,000,000 point updates in977 replacement batches
  (1954 update ACKs), followed by queries at0/5/20/35/50% mutation.
- W2 rotates each incoming vector's dimensions by480, a norm-preserving
  **synthetic feature-semantic change**, not natural GIST evolution.
- One raw device representation, fresh logical occurrence IDs, dense swap-delete,
  serialized ACKs; live N returns to1M after each replacement pair. No query
  occurs between a delete batch and its paired insert.
- S2_STALE never refreshes. S2_INC uses ordinary eager sum/count deltas and
  charges actual deleted-device-row gather, arithmetic and mean delivery to ACK.
  Neither policy is an S3 contribution.

S0 is the explicitly identified exact-safe full960 instantiation, **not** the
historical unchecked FP32 B1 scan. S1 and both PDX policies retain the parent's
selected search-function SASS. Static historical timings are context, never
cross-campaign denominators.

## Maintenance is a policy cost, not an intrinsic barrier

W2 eager maintenance adds **218.118 ms** median matched-round update ACK tax
(95% interval **[202.356,241.455] ms**) relative to frozen PDX. Its additional
query saving is only0.449 ms across160 requests (median matched-round saving).
The tax is0.218 microseconds amortized per point update at batch≤512, not an
individual low-latency update result. Frozen PDX needs no such maintenance in
this test and remains exact regardless of ordering staleness.

An independent maintenance capture records977 gather and1954 mean kernels,
5.149728 GB kernel DRAM and199.271 ms summed diagnostic kernel duration.
Duration-weighted selected-kernel SM throughput is1.751% of peak and active
warps19.076%; neither is whole-service GPU utilization. Do not subtract this
profiler duration from primary ACKs or add its traffic to copy-request bytes.

For frozen W2, updates consume **91.14%** of service time (median within-process
share), versus7.7% query share. Delete ACKs account for about1.317 s and insert
ACKs0.279 s. This motivates a future update-critical-path attribution, not
another ordering heuristic. A Host submission/synchronization explanation is
an inference to test, not established by CPU user time or copy-request bytes.

## Validation closure

**117/117 registered GPU starts passed, zero failures or replacements:**
32 qualification,72 primary,12 all-query NCU andone maintenance NCU. Every
measured/warmup answer has complete native members/fields, actual transitions
and final maps are independently replayed, and each target process compares
every final device-vector byte outside timing. Qualification additionally
checks internal ordered-FP64 score bits and all four modes under memcheck,
racecheck and synccheck. Scope of sanitizer/stress is stated in QUALITY.json;
there is no concurrent/Graph/production promotion.

`evidence/STAGE_CENSUS.json` closes the exact command/file families and start
ledger. Public verification reconstructs72-process statistics, every normalized
profiler capture and117 receipt bindings without new CUDA starts. Raw private
membership/SASS/isolation must not be confused with publicly re-executed gates.

## Reading and reproduction

- [Decision and five required answers](DECISION.md)
- [Claim/evidence boundaries](CLAIM_EVIDENCE.md)
- [Frozen scope](EXPERIMENT_SCOPE.md), [contract](CONTRACT.json),
  [known-mechanism kill test](PRIOR_ART.md), [ownership design](DESIGN.md)
- [Metric denominators](METRICS.md), [reproduction](REPRODUCE.md),
  [postmeasurement audit](AUDIT.md)
- `results/TIMING.json`: frozen process estimators and all comparison intervals.
- `results/TRAFFIC.json`: all-query kernel DRAM/L2 by mutation window.
- `results/MAINTENANCE.json`: independent update-kernel diagnosis and paired tax.
- `results/SUMMARY.json`/`.csv`: insert/delete cost, finite-query tails,
  throughput, request bytes, nested spans and memory.

Four figures (PDF/SVG/400DPI PNG plus numeric CSV):

| Figure | Message | Uncertainty |
|---|---|---|
| [A: query vs mutation](figures/query_vs_mutation.pdf) | Frozen ordering retains its query advantage | Six process means; p10–p90 |
| [B: DRAM vs mutation](figures/dram_vs_mutation.pdf) | Physical traffic must be checked separately from logical coordinates | One NCU process/cell; no process CI |
| [C: gain vs update tax](figures/gain_vs_update_tax.pdf) | Eager policy costs grow with update intensity without a corresponding query gain | Paired 95% intervals; three workload points, not Pareto |
| [D: service composition](figures/service_composition.pdf) | W2 service is update-dominated | Arithmetic process means; total SD; no double-counted maintenance |

Publication contains task-owned code, normalized metrics, identities and
figures only. Raw data, full answers, placements, environments, binaries,
profiler containers and the confidential manuscript are not uploaded.
