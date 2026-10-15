# Decision: copy/control granularity is the first target, not update arithmetic

Status: **attribution supported at the CUDA-runtime/API and transfer-activity
level**. CPU instruction-versus-wait attribution, exact physical DRAM/L2 traffic,
a deployable optimization and novelty remain unestablished. No GPU follow-up is
automatically admitted by this record.

## 1. Where is delete's main cost?

The B512 profile spends90.081% of whole ACK inside copy APIs, versus0.228% in
explicit stream-sync APIs. Native delete is1.407446 ms/ACK; the profiler raises
it to2.434500 ms/ACK (1.7297×). These fractions describe the profiled path only.
The source, mutation witnesses and timeline agree on one copy per moved row.
Full W2 issues500,000 delete copy calls for1.920 GB, versus977 insert calls for
the same payload. It is a fine-grained row-movement/control path, not an
identified application compute kernel. API time may contain waits and staging;
calling it90% CPU computation would be unjustified.

## 2. How do insert and delete differ?

Insertion uploads one contiguous B-row pageable Host batch, then assigns fresh
logical occurrence IDs. Deletion checks live unique IDs, repeatedly swaps the
current last physical row into a hole, updates two ownership maps and appends
transition witnesses. Each native batch ends with one required stream sync.
Later swaps can depend on earlier ownership transitions: a naive unordered
bulk-copy replacement is not semantically equivalent. Pure insert uses an
untimed pre-delete, so pure I/D initial states differ; replacement retains the
nested native ACK fields and an additional true pair ACK for a coupled control.

## 3. How busy is the GPU?

All nine micro profiles and full-service update ranges contain zero recorded
application update kernels and launches, consistent with the unchanged source.
DMA is nonzero: B512 delete DMA/ACK is24.430% in its independent profile; this
**overlaps**, rather than adds to, Host API time. The service query positive
control records1,895 kernels and1,895 launch APIs. Therefore “no update kernels”
is not “no GPU work”. Device-wide10kHz percent samples, quantized in1% steps,
are retained with their first-to-last-operator window; they are neither
per-ACK activity nor exact physical traffic. Scaled warp averages, raw signed
clock fields and exact DRAM/L2 bytes are deliberately not guessed.

## 4. Are fixed launch, sync and round-trip costs important?

Small batches do show substantial fixed cost: D/B1 has40.947% profiled explicit
sync fraction. D/B512 has only0.228%, while copy APIs dominate. There are no
application update launches to optimize. Each native ACK has one explicit
stream wait, but a wait is not a PCIe round trip; async APIs may themselves
block. Eliminating only the visible stream wait is therefore a weak large-B
hypothesis. CPU event accounting is about one core-equivalent, but includes
runtime, driver waits/spinning and background threads; it is not a CPU
arithmetic profile or a complete scheduling trace.

## 5. Does batching amortize cost?

Yes, within the changed request-granularity contract: native B1→B512 µs per
point falls6.494→0.548 for I,8.259→2.749 for D and7.213→1.668 for R (R counts
both delete and insert points). B32→B512 delete barely improves2.851→2.749,
unlike the much larger B1 reduction. Batch size amortizes the ACK/wait, but
not the per-moved-row copy submissions. This is a measured batch trend, not
a same-contract optimized service speedup or an arrival-SLA result.

## 6. Which research target is justified next?

**Ownership-safe copy/control coarsening** is the first cheap falsification
target, not a new update arithmetic kernel. Native I/B512 payload rate7.009 GB/s
is near the measured pageable-H2D reference median7.236 GB/s. D/B5121.397 GB/s
is far below the isolated disjoint-D2D733.880 GB/s reference, but that reference
has different dependencies and is not an attainable bound. This combination
makes fine-grained orchestration more plausible than raw bulk-bandwidth
saturation; it does not isolate pure CPU dispatch from copy-engine/driver
backpressure. Before implementation, derive and test a dependency-safe row
movement schedule on CPU and check the nearest prior art. Ordinary copy
batching alone is not a defensible contribution.

## 7. Is there a reproducible dynamic-specific bottleneck?

There is a reproducible **implementation- and workload-specific** dynamic
critical path: B512 D is slower than I in all6 rounds, paired ratio4.7289 with
95%CI[4.2277,5.0546]; full W2 update/service share is91.149%. Frozen PDX saves
20.842% query median time, but service median saves only1.524%, and the paired
service interval[0.942238,1.022047] crosses1. Thus no service improvement is
confirmed in this campaign. Serial ACK visibility makes updates occupy the
critical path; it does not measure an alternative concurrent scheduler or
prove overlap is safe/beneficial. Do not generalize this to all GPU trees.

## Hypothesis / negative-evidence ledger

| Target | Evidence and added costs | Decision | Reopen condition |
|---|---|---|---|
| Application update arithmetic | No explicit/recorded update kernels; query positive control visible | Not the first target for this path | A different admitted update algorithm executes dominant kernels |
| Explicit stream wait alone at large B | D/B512 profiled sync0.228%, profiler perturbs ACK1.7297× | Weak standalone explanation, not rejected for B1 | Same-contract attribution shows hidden or explicit waits dominate |
| Raw bulk bandwidth alone | Equal payload,511.77× different full-service copy counts; D far below disjoint bulk reference | Insufficient explanation; exact DRAM bytes unknown | Same-contract physical traffic/backpressure evidence changes attribution |
| New dynamic storage/async index | Not implemented or evaluated | Unknown, no novelty/product admission | Cheap prior-art and dependency-safe falsification passes first |
| Service speedup from current query change | Median favorable; paired95%CI crosses1 | Inconclusive in R2 | A new predeclared independent same-contract campaign resolves interval |

All NSYS completeness warnings remain recorded. Required phase/API/byte counts
are independently bound, but internal driver/OSRT/scheduler completeness is
not established. This is the strongest material limit on causal wording.
