# Claim–evidence ledger

| ID | Allowed claim | Evidence and denominator | Material boundary |
|---|---|---|---|
| C1 | Known PDX-BOND ordering captures 49.7383118161% of the restricted oracle gap | Prior CPU checkpoint logical/GAP_CAPTURE.json; complete 32M pairs | Diagnostic coordinate counts, not arbitrary-index lower bounds or a novel mechanism |
| C2 | Stage coordinate model is 711,680,776 B/query | Prior source/SOURCE_BYTES.json and STAGE_SURVIVORS.json | Logical source model; not DRAM and not complete restoration cost |
| C3 | All-kernel DRAM falls 30.3226569849% | evidence/DRAM.json, all 832 captured kernel records across two NCU processes | 32 queries/process, one process/mode, decimal GB; excludes DMA and supplies no process CI |
| C4 | Complete Host-ready latency falls 20.5529960122% | evidence/TIMING.json, median ratio of 6 process means/mode, 6/6 matched wins | Static resident GIST1M/D960/B1/range/fixed32 only; one-time preparation excluded |
| C5 | Paired geometric ratio CI excludes 0.97 | TIMING.json, paired ratio 0.7938580071195104, fixed-seed 20k round-bootstrap CI [0.7927909123873055,0.7949113365265615] | Not a confidence interval for the median-ratio estimator; n=6 matched process rounds |
| C6 | Correctness passed the frozen authority and native-field contract | QUALITY.json, QUALITY_RECEIPTS.json; all target requests include warmups; each full-N qualification bit-checks 7,711 internal FP64 hit scores | Native squared field is FP32-rounded then FP64-cast, not full-FP64 output; inherited field tolerance unchanged |
| C7 | Bounded sanitizer/stream stress passed | Six sanitizer processes, N4096 plus synthetic 100-iteration/two-stream/pointer-churn fixtures | Not full-N sanitizer, Graph, dynamic, or production sustained qualification |
| C8 | The comparator was freshly remeasured without CUDA-code drift | INPUT_IDENTITY.json and STATIC.json; five keeper normalized device functions match the historical keeper | Whole-container and selected-function identities are distinct; REG counts do not prove occupancy/latency causality |
| C9 | GPU budget and isolation closed without sample replacement | EXECUTION.json, 26 start receipts, RAW_MANIFEST.json, CUSTODY.json | Old preparation failure retained; NCU-only host routing repaired before first attempt; no foreign processes/settings modified |

## Attribution, cost and next gate

- Fewer stage survivors explain reduced coordinate traffic plausibly; independent
  scan events fall 1.040002002→0.802150003 ms/query. This is mechanism evidence,
  not a causal isolation of coalescing, registers, CPU arithmetic or CPU waiting.
- Online priority, sort, two order uploads, original-order subset/full replay,
  CUB, synchronizations and output are charged. One raw FP32 representation,
  240 B added device orders, and 3,840 B static Host means; no database replicas.
- All target outputs were checked in the private curator. The public verifier
  checks identities/scalars/receipt bindings; it cannot re-establish membership
  or SASS equality from hashes alone. Private raw archive and original data are
  required for independent full revalidation.

## Rejected thesis and reopening condition

**Rejected:** present another query-aware score/order/portfolio as a new GTSPP
mechanism to exploit the original→oracle gap. **Keeper/target:** P1 progressive,
GIST1M static range. **Observation:** known PDX-BOND adaptation already wins the
frozen end-to-end query gate with all online and restoration costs charged.
**Decision:** no novelty promotion; retain the positive baseline and this
negative novelty evidence together. Reopen only for a distinct mechanism and
decisive same-contract evidence against the now-stronger known-mechanism
comparator; dynamic maintenance alone is an unmeasured question, not novelty.

Forbidden extrapolations: all GPU trees have this redundancy; measured CPU
utilization fell; this solves dynamic insert/delete or 100k workflow; kNN/ANN
or FAISS/CAGRA lost; the official upstream package supplies this GPU adapter;
our ordering is novel; kernel-event/NCU durations are the primary latency.
