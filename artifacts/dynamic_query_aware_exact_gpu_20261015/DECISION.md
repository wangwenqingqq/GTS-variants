# Decision — close ordering novelty; follow the update critical path

**Descriptive outcome:** query-robust in the tested synthetic stress, with an
update-dominated workflow; the eager-maintenance implementation additionally
regresses W2 service. This is **not** evidence for an unavoidable statistical
maintenance barrier or a newly established dynamic-specific research gap.
The outcome families in the research plan are overlapping descriptions, not
posthoc pass/fail thresholds.

## 1. Does the static PDX advantage remain?

Yes within the frozen GIST1M/D960/B1 exact-range scope. The table uses six-process
median query-mean ratios relative to same-window S1, not old static timings.

| W2 replaced | True mean drift (relative L2) | S1 ms/query | Frozen PDX ms/query | Frozen query reduction | Gain retained vs own zero mutation |
|---|---:|---:|---:|---:|---:|
| 0% | 0% | 1.144438 | 0.909261 | 20.55% | 100.00% |
| 5% | 1.1417% | 1.116264 | 0.882472 | 20.94% | 101.92% |
| 20% | 4.5643% | 1.061673 | 0.837628 | 21.10% | 102.69% |
| 35% | 7.9820% | 1.028613 | 0.816121 | 20.66% | 100.53% |
| 50% | 11.4168% | 0.993437 | 0.785420 | 20.94% | 101.90% |

At50%, frozen/S1 query ratio is0.790609, paired interval
[0.788303,0.792911]. Frozen PDX's own50%/0% latency ratio is0.863800.
Both self-ratio and relative advantage are reported because the live answer
population changes; average exact hits fall from205.9375 to142.09375/query.
These are32 repeated fixed query vectors, not32 independent new queries per
window or evidence about a shifting query distribution.

## 2. What degrades first: logical pruning, physical execution or maintenance?

No monotone query-latency collapse is observed. Frozen stage-coordinate visits
rise modestly from177.920194M to179.132866M/query (+0.68%), while S1 falls from
253.707194M to242.398802M. These are actual checkpoint reads, not ideal
first-crossing dimensions, all restoration bytes, or information lower bounds.
A small logical change must not be hidden by the favorable latency trend.
Physical traffic shows a **small deterioration, not a collapse**:

| W2 mutation | S0 GB/query | S1 GB/query | Frozen PDX GB/query | Delta PDX GB/query |
|---|---:|---:|---:|---:|
| 0% | 3.895977 | 1.119289 | 0.780090 | 0.780126 |
| 5% | 3.895996 | 1.113918 | 0.780566 | 0.777827 |
| 20% | 3.895745 | 1.099343 | 0.782565 | 0.777506 |
| 35% | 3.895746 | 1.084886 | 0.784210 | 0.784098 |
| 50% | 3.895506 | 1.069764 | 0.785922 | 0.777591 |

Frozen PDX DRAM rises0.75%; its advantage versus S1 narrows from30.30% to26.53%.
At50%, eager means recover1.06% of frozen PDX's DRAM, but do not recover their
service cost. There is one independent NCU process/cell and32 requests/window;
there is no process-level traffic CI. Copy engines are excluded. Kernel families,
read/write/L2 and all actual captures remain in `results/TRAFFIC.json` and its
normalized evidence. Lower absolute query time alone would have hidden this
small physical weakening.

Eager INC is an added critical-path policy: its mean calculation changes the
heuristic, not exactness, and is fully charged within update ACKs. Its small
query benefit does not justify its W2 service loss. Frozen PDX has zero refresh
frequency and zero standalone maintenance, without losing the measured query
advantage. A naive full-statistics rebuild would be a weak control here. The independent
maintenance profile captures2931 statistics kernels:199.271 ms summed kernel
duration and5.149728 GB DRAM. Duration-weighted selected-kernel SM throughput
is1.751% of peak and active warps19.076%, **not** service occupancy or an isolated
share of the218.118 ms primary tax. Cache-resident writes and copy engines are
not fully represented by that kernel DRAM table; requested data-copy bytes
cannot simply be added to it.

## 3. Can update/statistics cost cancel query savings?

Yes for the measured eager policy, not for every possible implementation.

| Workload | Point updates/query | INC−frozen update tax (ms) | 95% paired tax interval (ms) | Amortized microseconds/point update |
|---|---:|---:|---:|---:|
| W0 | 0.2 | 0.288496 | [0.272854,0.318213] | 9.01548 |
| W1 | 0.8 | 0.997877 | [0.981502,1.111552] | 7.79591 |
| W2 | 6250 | 218.117529 | [202.355755,241.455177] | 0.21812 |

The W2 rate uses up to512 rows/batch, so its amortized point cost cannot be
compared to single-row latency without that qualifier. There are977 replacement
batches and1954 update ACKs, notone million independent synchronized batches.

W2 INC saves only0.448679 ms of query ACKs relative to frozen PDX (median of
six paired total-query differences) but adds218.117529 ms of update ACKs.
Its service is12.62% slower than frozen PDX and10.49% slower than S1. The
latter loses in all six pairs, paired ratio interval[1.090452,1.111086].
Frozen PDX itself still lowers W2 service by1.89%, all six wins, interval
[0.973483,0.981470]. Its roughly21% query gain is diluted because updates
already occupy91.14% of total service. These intervals describe the paired
geometric estimator; the stated percentage is from the declared median ratio.

## 4. Is there a mutation/drift threshold?

**No threshold was located**, not “the threshold exceeds50%” universally.
The five tested checkpoints cover0–50% distinct original-object replacement
and0–11.4168% true live-mean drift under one synthetic coordinate permutation.
Frozen query advantage stays about20.55–21.10%, not a monotone deterioration.
A threshold might occur under other data geometry, queries, selectivity, growth,
update locality, or more severe/different drift; none was tested here.

W0/W1 are stationary small-mutation controls; W1's queries span mutation windows,
not one constant snapshot. W2 is deliberately update-heavy and bursty. These
three points do not locate an optimal policy, production update rate, SLA,
concurrent service capacity, or a universal refresh schedule.

## 5. Has a dynamic-specific research gap survived the cheap controls?

**No.** The hypothesized staleness failure was not reproduced, and the ordinary
frozen-statistics control avoids the measured eager tax. Exact output never
requires a fresh mean. Thus “static known mechanism + dynamic failure + no
cheap existing solution” has not been established. Extra engineering or a
small mean-refresh speedup cannot rescue that thesis.

### Implementation, mechanism and thesis are separate

- **Implementation:** serial dynamic adapters with complete occurrence-ID output
  and ordinary eager sum/count maintenance are validated under the declared
  bounded shapes/workflows. No growth/concurrency/Graph/production admission.
- **Mechanism:** known PDX ordering remains useful with frozen statistics for
  this synthetic stress. Eager maintenance is a correct but losing W2 policy.
- **Thesis:** close query-aware ordering as a novelty source on this evidence.
  The next question is update-critical-path attribution, not S3 in this delivery.

### Next falsifiable step; not automatically executed

First profile the existing strongest frozen-PDX W2 update path: Host mapping,
per-row swap copy submission, transfer/synchronization and actual GPU work.
Delete ACKs take about1.317 s versus0.279 s insert ACKs. Compare an ordinary
batched update control before inventing a data structure or asynchronous
statistics. Preserve complete logical occurrences, exact answers, all payload
costs, final state and the same events+release denominator. A CPU-user-time
observation alone does not prove which call is responsible.

Reopen a statistics-specific direction only if a new preregistered shift
reliably destroys the frozen control's query/traffic advantage and cheap
ordinary refresh controls fail on the same whole-service contract. New shapes,
datasets or concurrent/SLA claims require fresh qualification and novelty gates.
