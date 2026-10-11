# Fixed3 improves original-GTS Host-ready time by 2.562x

**Packing provides the independent benefit: G1/G2 is 2.543937x, whereas merely
shrinking the original CTA gives G0/G1 of 1.006995x.** All six process pairs favor
the candidate in each comparison. This is original GTS on the frozen GIST 1M
workload, not current GTSPP, an external-baseline victory or a novelty claim.

## Primary result: complete Host-ready pass

GIST N=1,000,000, D=960 FP32, exact L2, K=8/B=1, self-inclusive. Original ordered
arithmetic, tree/pivots, 1 GiB workspace, task decisions, layout, sorting and full
outputs remain unchanged. The 256 confirmation queries are reused verbatim from
the preceding campaign; they are not newly held-out or selected for this gain.
Each of six rounds launches three fresh processes in the preregistered balanced
order. Each process performs two warmup queries and one complete 256-query pass.

| Comparison | Interpretation | Paired geometric ratio | 95% paired bootstrap CI | Candidate wins |
|---|---|---:|---|---:|
| G0/G1 | CTA shrink only | 1.006995 | [1.005330, 1.009733] | 6/6 |
| G1/G2 | Independent packing increment | 2.543937 | [2.541211, 2.545909] | 6/6 |
| G0/G2 | Combined gain over original | 2.561733 | [2.556026, 2.570420] | 6/6 |

Ratios are computed from paired whole-process rounds, with 20,000 bootstrap
resamples and the frozen seed. Intervals describe run variation on this fixed
query set, not uncertainty across datasets, query distributions or GPUs. These
are pointwise intervals, not simultaneous family-wise guarantees. All raw
rounds, marginal medians, arithmetic/geometric means and order strata are in
SUMMARY.json and FORMAL_ROUNDS.csv; no observations were replaced or omitted.

| Mode | Geometric mean seconds/256-query pass | Median seconds/pass | p10–p90 seconds/pass |
|---|---:|---:|---|
| G0: 512-thread one-leaf CTA | 89.874330 | 89.756063 | 89.705218–90.163266 |
| G1: 32-thread one-leaf CTA | 89.249986 | 89.239976 | 89.207744–89.302274 |
| G2: 32-thread fixed3 CTA | 35.083408 | 35.072344 | 35.056525–35.121417 |

The measured host timer includes query copies, allocations, traversal, kernel
launches, synchronization, materialization, sort/merge, complete ID/distance
return and query cleanup. Data/index load, warmup, oracle validation, profiler
and file writes are excluded. There is no packing buffer or separate packing
kernel; lane/task decoding and all original result-slot stores are included.

## Attribution and strongest caveat

In the two reverse NSYS diagnostic rounds, G2's leaf-inclusive time is 2.95–2.99x
better than G1. All modes launch 32 leaf kernels; G2 reduces their total CTAs
from 2,929,074 to 976,369. The per-node count sidecars are byte-identical across
modes: same visited leaves, bounds, masks, distance work and original task order.
Full results are bit-identical. See MECHANISM_RESULTS.md for the exact inventory.

G1 does not beat G0's leaf-inclusive duration in both diagnostic orders, even
though the longer unprofiled formal pass shows a small 1.006995x net benefit.
These are distinct scopes; do not turn the tiny whole-pass gain into a stable
leaf-kernel claim. The large independent G1/G2 increment survives either order
and is not explained by the CTA-shrink control.

NCU hardware counters were permission-denied before runtime collection. We did
not alter driver policy or elevate privileges. NSYS confirms actual launch
geometry/time, but issued instructions, DRAM/L2 bytes, coalescing, hardware
occupancy, branch efficiency and dynamic spill traffic remain unavailable.
The result establishes a mapping-level net win, not a unique microarchitectural
explanation. Static SASS is unchanged for G0/G1; G2 adds four registers without
additional declared stack/shared allocation or ptxas spill bytes.

## Validation and preservation

The final generation includes 39 qualification processes, 6 work-count processes,
6 profiler processes and 18 formal processes: 69 total, with 5,790 complete-query
oracle checks. Nine unit processes each exercise 392 real leaf-kernel cases,
including all 20 result slots, tails, self/equal vectors and allocation lifecycles.
The GPU unit sizes are 1/4/5/10/11/13/20; only the CPU slot-ownership proof
enumerates every size from 1 through 20. The frozen contract's short phrase
`size1..20` is ambiguous: it does not mean an exhaustive GPU size sweep was run.
G1/G2 memcheck/racecheck/synccheck pass for those D96/960 unit cases and D96
whole-query fixtures. This is not full 1M sanitizer certification. N<K, B=32,
updates, concurrency, Graph and current GTSPP remain outside the contract.

The first 39-process qualification also passed. An independent protocol audit
then required holding the shared GPU locks across entire collection phases,
not only individual child processes. Its raw results were preserved and one
complete v2 qualification was registered and repeated using identical nine GPU
binaries. All corresponding outputs match. No performance result triggered
this change, and no formal result was rerun to seek a favorable observation.

The raw bundle, source/binary pins and per-phase receipts retain the entire
chain. Data and restricted/private machine details are not uploaded to Git.
