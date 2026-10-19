# Fixed-batch shared-plan offline opportunity gate

**The strongest frozen simple control leaves 10.93% and 23.42% source-cost
headroom at B2/B4 within the fixed-chain family. B8 is unresolved: only 2.35%
extra saving is demonstrated; the optimistic maximum is 44.84%.** This is not
GPU speedup, physical DRAM traffic, or an admission of a new index mechanism.

| B | Independent GB/query | Strong simple GB/query | Oracle cost interval GB/query | Extra saving vs strong simple | Batched full scan GB/query |
|---:|---:|---:|---:|---:|---:|
| 2 | 0.814114808 | 0.753396888 | 0.671067576–0.671067576 | 10.9277%–10.9277% | 1.920003960 |
| 4 | 0.814114808 | 0.706752120 | 0.541218968–0.541218968 | 23.4217%–23.4217% | 0.960003960 |
| 8 | 0.814114808 | 0.617970648 | 0.340882040–0.603455032 | 2.3489%–44.8385% | 0.480003960 |

All values include the declared terminal pass and query/order inputs, and use
decimal GB. At B8 both the strongest simple schedule and best feasible oracle
schedule read more modeled source bytes than a one-pass batched full scan.
The lower bound might beat that control, but no such schedule is established.

- Data: inherited **1,000,000 × 960 FP32**, 3.84GB source payload; all32 fixed
  development queries, not an observed production distribution or held-out test.
- Fixed batches: B2/B4/B8, one seeded permutation, 28 batches, all125,000
  candidate8-row sectors/batch; same batch for every strategy. No grouping study.
- One1024B transposed-coordinate tile buffer; fixed per-query PDX zone chains.
  Original data are not transposed or changed: the layout is an explicit model.
- **28/28 CPU population processes passed; zero GPU starts**, no retries.
  Correctness here is trace identity and schedule replay, not new search outputs.

Read [the report](REPORT.md), [decision](DECISION.md), [claim ledger](CLAIM_EVIDENCE.md),
[frozen contract](CONTRACT.json), [pre-target clarifications](CLARIFICATIONS.json),
[prior art](PRIOR_ART.md) and [reproduction boundaries](REPRODUCE.md).
