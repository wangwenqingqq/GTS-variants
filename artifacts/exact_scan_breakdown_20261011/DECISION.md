# MEMORY_BOUND, with arithmetic inflation — not near roofline

**The fixed native complete-range workload is memory-dominant, not independently
CPU-control-dominant; it still has a material library execution-shape gap.** The
coordinate-read control costs **75.9188%** of full query ACK, the selected native
kernel sustains **1159.547 GB/s** versus the same-campaign reachable streaming
reference **1525.477 GB/s** (**76.0121%**), and the count-to-full signed contrast is
only **0.7510%**. These pass the frozen MEMORY_BOUND gate. NEAR_ROOFLINE fails:
76.0% is below 85%, and the distance-minus-read contrast is 23.3365% of full ACK.
This is a scoped diagnosis, **not a new optimization or end-to-end speedup**.

## Evidence and denominator

GIST **1,000,000 vectors, D960, FP32 storage, L2, B1**, original 32 range queries,
initial snapshot, radius bits 0x3f34a3d8. Six fresh processes per primary case;
median of process mean query intervals, p10/p90 retained; six forward/reverse
rounds for the diagnostic controls. Unchanged native keeper: **3.354495ms/query**,
**107.345354ms/32-query continuous pass**. Later FULL_OUTPUT control calls the
same Scan::range and yields bit-identical answer payloads: **3.315706ms/query**,
**106.104722ms/pass**. Their stages are not genuinely paired and no speedup is
claimed between them. Setup/context/warmup/disk are excluded and recorded.

One independent NSYS static capture places **97.6855%** of Host query spans in
GPU-active interval unions. cudaMemcpyAsync's 106.007287ms inclusive API duration
has 104.596661ms GPU overlap; it is not independent CPU work to add to the GPU.
The exposed Host gap is 2.501523ms across 32 queries. No measured static allocation
or free API is observed. Input reads and distance arithmetic are fused; the
breakdown never fabricates them as additive exclusive bars.

## Important counterevidence: useful work is not executed work

The useful scalar L2 model is 2.879G operations/query. Native DISTANCE_ONLY and
FULL_OUTPUT main-kernel captures both record 61.44G predicated-on FADD and 61.44G
FFMA, giving **184.32G executed FP32 proxy FLOPs**, approximately **64.02x** the
useful model. FP64 add/mul/FMA counters are 0 in this selected distance function.
Its measured DRAM traffic is 3,853,073,152B, close to 3.84GB logical vector payload;
SM throughput 76.5268% and occupancy 28.8641% are diagnostic metrics, not wins.

Both independent runtime-function exports have 2824 rendered instructions and
identical normalized instruction-text hash
`f6e1bd34e8b38fbd76b8d52ed335ab0492ce748daa1e3fa00885d503cbf1e2ec` after explicitly
normalizing ASLR-relative control targets. Predicates and other operands remain.
The report and library container hashes are retained; full JIT-module bytes/hash
are unavailable. Vendor SASS stays private. **A padded query-tile explanation is
an inference, not established causality.** No B1 specialization was implemented;
64x executed-work inflation is not 64x attainable speedup. READ_ONLY uses another
schedule and adds reduction, so its difference is not an exact removable cost.

## Dynamic workflow: CPU occupancy and update latency are different questions

The unchanged E_ADAPT 336-event trace contains 128 range, 128 kNN, 40 insert, 40 delete.
Median continuous trace is **1332.923838ms**, including service release but not
setup/context/warmup/disk. Update ACKs occupy only **0.063045%** of that interval.
Insert/delete event p50s are **0.013355 / 0.006330ms**; median 40-event ACK sums are
**0.544458 / 0.297361ms**. The older 0.532743/0.293380ms entries were total 40-event
sums, not per-operation medians. No rebuild; 153,600 inserted H2D bytes and 76,880
swap D2D bytes, 20 nontrivial swaps. UPDATE_BOUND fails decisively.

CPU rusage divided by trace wall time is **0.998461 core-equivalent**, confirming
high CPU consumption, but not independent CPU arithmetic. One dynamic NSYS
capture has 90.7837% GPU-active operation spans and a 97.915261ms lazy cudaHostAlloc
on the first measured Faiss kNN after restored/cloned warmup. This lazy resource
cost is charged, not an update cost or hidden by warming the restored instance.
CPU sampled stacks are unavailable; synchronization/polling as the cause of high
CPU usage remains an inference. Reducing a wait's CPU consumption does not by
itself shorten the GPU critical path. Secondary kNN uses native Faiss with
use_cuvs=false; the range-kernel classification is not transferred to it.

## Qualification, limitations and retained failures

- **106 top-level starts, 105 valid processes, one retained pre-CUDA failure**,
  within 110. The matched-reference launcher initially omitted BUILD_MAPPING=TILED;
  authorized recovery used the same binary/data/query/timing/quality and did not
  rerun the previous 103 valid processes. Ordered-FP64 reference passes all 40
  complete answers and field bits; its one-process latency is diagnostic only.
- An approved independent L2 supplement records read 3,901,936,832B,
  write 4,658,048B, Other 321,536B, total 3,906,916,416B. These are 32-byte request
  sectors, not DRAM transfer. The first offline two-bucket interpretation failed;
  a three-bucket correction retained the raw capture and performed no GPU rerun.
  Other subtype is unknown. Do not blend this capture with the earlier L2 total.
- Output targets are **not attained**: actual low/mid/high means are
  **200.34375 /205.9375 /1644.9375**, not 10/current/10x-current. The actual 8.210x
  high/low count contrast has paired time ratio 95% CI [0.999913,1.007838], not a
  confirmed large penalty. No inference to dense answers or all queries.
- Lower-D output means 1.1875/16.84375/103.875 are not matched to D960. D scaling is
  descriptive; the primary resource decision uses the fixed D960 controls.
- Native fields use the original 5e-5 scale tolerance; complete membership is
  exact on tested inputs. This is not a universal floating-point exactness proof.
- No P/tree or external index comparator is remeasured here. Earlier same-contract
  external results remain unchanged; no new GTSPP-over-baseline gain is asserted.
  No 100k/1B or sustained-workload projection, new kernel optimization, or paper edit.

## Research decision and reopen gate

**Do not start compression, Tensor Core, persistent execution or another tree
prototype under this campaign.** Any next direction must first pass a cheap
novelty kill test, exactness/quality definition and decisive same-contract external
comparison. Small-query tile selection and resource reuse already have upstream
prior art: [cuVS issue 277](https://github.com/NVIDIA/cuvs/issues/277). That discussion
is a novelty warning, not proof of this workload's 64x counter mechanism. Generic
B1 routing or a small kernel gain cannot rescue a subsumed system thesis.

| Retained negative hypothesis | Counterevidence | Reopen condition |
| --- | --- | --- |
| Independent CPU control is the static primary cost |97.7% GPU-active spans, 0 static allocation/free calls; API waits overlap GPU | Different declared workload with measured exposed CPU/control dominating, plus sampled CPU stacks |
| Current sparse output dominates |Only 0.75% signed full-minus-count share; actual 8.21x output count has no confirmed large time penalty |Separately frozen dense-output contract, complete output and same-scope timing |
| Updates dominate this short workflow |0.063% continuous-trace update ACK share |Separately frozen update-heavy sustained trace; no projection from 336 events |
| Strong scan is already at its reachable roofline |Only 76% reachable memory rate and 184.32G executed versus 2.879G useful proxy |Distinct, non-subsumed mechanism with correctness, library comparator remeasurement and end-to-end admission |

**Redundancy → mechanism → module → effect → end-to-end benefit:** observed
execution-work inflation and overlapping waits → no new mechanism admitted →
unchanged native scan plus diagnostic modules → measured resource attribution →
**no new end-to-end benefit demonstrated in this diagnostic campaign**.
