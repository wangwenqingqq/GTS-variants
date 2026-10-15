# Dynamic query-aware exact GPU search — frozen first campaign

**Question:** does the known static PDX-BOND benefit survive mutations and
statistics drift, after charging ordinary low-cost incremental maintenance?
There is no S3, ordering sweep, or novelty admission. Prior static numbers are
context, never denominators for dynamic ratios. The contract precedes code and
measurement; sources/binaries/inputs are registered again before each stage.

## Systems and hypotheses

- S0 is an exact-safe full-coordinate scan, not the old unchecked FP32 cutoff.
  It instantiates the existing safe progressive kernel at 0→960, one stable
  selection and complete output. This is a new explicitly identified control,
  not a relabeling of the historical strengthened B1 timing.
- S1 retains the frozen progressive schedule and raw representation.
- S2_STALE retains the approved PDX-BOND criterion and initial mean forever.
  Staleness changes order, not correctness; it does not require a rebuild.
- S2_INC uses the same search kernels plus ordinary sum/count maintenance.
  Real deleted device vectors are gathered before overwrites, reduced by one
  owner per dimension, and the FP32 mean is delivered to Host before ACK.
  No free Host-vector mirror or offline fresh statistics feed live queries.

Positive hypothesis: drift destroys useful PDX ordering or maintaining it costs
more than query savings. Negative hypothesis: frozen means remain useful, or
ordinary O(D×batch) delta aggregation preserves gains cheaply. Both receive the
same exactness, frozen queries, live data and end-to-end denominator. Even a
measured failure of this adapter would not prove a mechanism-level impossibility.

## Workloads and limits

All primary runs start at GIST1M/D960/B1 and use the inherited 32 immutable
query vectors and inclusive radius. A query remains valid if its original
database occurrence is deleted. Each of five windows uses all 32 queries;
W1 interleaves two queries after each replacement pair, so its x-axis represents
a mutation window, not one constant snapshot. Eight initial warmups are not
timed. Queries and mutations are serial; there is no concurrency or SLA claim.

| Workload | Replacements at successive windows | Update form | Meaning |
|---|---|---|---|
| W0 | 0,4,8,12,16 | Single-row delete/insert | Read-dominant stationary control |
| W1 | 0,16,32,48,64 | Single-row pair then two queries | Balanced point-operation mixed control |
| W2 | 0,50k,200k,350k,500k | Up to 512 rows/batch, queries after bursts | Update-heavy controlled synthetic drift |

W0/W1 insert unchanged existing vectors with new occurrence IDs. W2 inserts
the victim's original vector with its 30 coordinate zones circularly rotated
by 15. It is norm-preserving but changes feature semantics: a **synthetic
stress**, not a naturally observed GIST evolution. It is frozen independently
of query outcomes and latency. If its actual drift is weak, that is reported,
not tuned away. Mutation fraction counts distinct original objects replaced;
point updates/query, batch ACKs/query and measured updates/s are distinct.
Live N returns to its initial value after each pair. Intermediate deletes are
visible at their ACK, but this client issues no query between a delete batch
and its matching insert batch. There is no growing-corpus qualification.

## Costs and measurement

Incremental means use the exact inherited FP32 mean as an anchor, with FP64
delta sums. They are not claimed bitwise equal to a fresh NumPy FP32 reduction.
The anchored formula is independently checked; true live FP64 means are an
offline drift diagnostic, never a free live-query input. All mean gathering,
sum kernels, transfers, synchronization and Host work are charged inside
update ACKs. Query priority/sort/uploads and ordered score restoration remain
inside complete Host-ready query timing.

Service time is explicitly **events + release**, excluding the common offline
answer/state validation and serialization interval. Unlike the older Gate3
boundary, service-owned retained Host containers are destroyed inside release.
Immutable client request/input storage and process context teardown remain
excluded. Standalone maintenance outside updates is zero; incremental
maintenance is nested in update ACKs, so charts never add it twice. The direct
end-to-end update-tax estimator is the paired INC−STALE update ACK difference;
an inclusive Host tail is not mislabeled isolated GPU statistics time.

Six fresh matched rounds alternate all-system order and retain every query and
operation sample. Independent NCU processes capture all query kernels at every
window, not profiler durations as public latency. One additional INC/W2 NCU
process captures maintenance kernels. Copy-request bytes are not DRAM traffic;
query DRAM excludes DMA, and no process-level DRAM CI is invented.

The bounded budget is 117 GPU processes, no retries: 32 qualification,
72 primary, 12 query NCU, one maintenance NCU. Any first failure stops the
campaign; successes/failures/unexecuted jobs remain append-only. The current
campaign tests trends on 160 formal queries/process and cannot replace formal
10k-query, 100k-event, multi-dataset, asynchronous or production acceptance.
