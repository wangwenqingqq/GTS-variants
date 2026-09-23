# GTS CUDA Graph scale experiment

The experiment extends the fixed-capacity Graph attribution to the complete
611,756-string Words dataset and to larger captured serial query bundles.
This is an engineering scale test, not a new graph algorithm or novelty claim.
**Partial campaign, not a completed profiler attribution.** The five completed
shape comparisons show a shrinking Graph benefit: 1.320x at 2,000 objects,
1.076x at 20,000, 1.011x at 100,000, and no reliable benefit at the complete
611,756-object scale. Increasing the serial bundle to eight does not establish
a win. K=32 performance remains unvalidated.

Collection stopped when a foreign process entered GPU 0 during the second K=32
round. The monitor terminated only the owned benchmark. Of 242 planned runs,
219 completed cleanly and one was rejected; 22 were not started. All six shapes
passed their correctness/sanitizer/stress gates. Five shapes completed all six
primary rounds and both sustained orders. **All four new NSYS traces remain
uncollected.** The interrupted observation is retained, never replaced or included
in a speedup estimate. GPU availability must be re-admitted before a separate
continuation; no foreign process or GPU setting was changed.

## Measured results

Host-wall milliseconds per completed query, or amortized per query for K>1.
Each entry is the median of six process means, not a profiler duration. A is the
configured native-function comparator; B is fixed-capacity ordinary stream; C is
same-enqueue Graph replay. Only B/C isolates Graph from buffer reuse.

| N | Serial K | A (ms) | B (ms) | C (ms) | B/C | Decision |
|---:|---:|---:|---:|---:|---:|---|
| 2,000 | 1 | 0.5920 | 0.1458 | 0.1105 | 1.320x | Shape-local latency gate passes |
| 20,000 | 1 | 1.1524 | 0.5759 | 0.5350 | 1.076x | Shape-local latency gate passes |
| 100,000 | 1 | 5.6166 | 4.2237 | 4.1763 | 1.011x | Below declared benefit threshold |
| 611,756 | 1 | 44.0156 | 40.0623 | 40.8079 | 0.982x | Observed slowdown; NSYS pending |
| 611,756 | 8 | 44.0766 | 40.1259 | 40.8833 | 0.981x | No reliable win |
| 611,756 | 32 | — | — | — | — | Timing interrupted; do not rank |

At K=8, B/C bundle completion is **321.007 / 327.066 ms**, not 40 ms individual
response latency. K=32 passed full-output checks and 1,024-query stress in all
three modes, but one complete timing round is insufficient for promotion.

| N / K | Paired geometric B/C [95% interval] | C process wins | Sustained B/C: forward / reverse |
|---|---:|---:|---:|
| 2,000 / 1 | 1.319 [1.313, 1.325] | 6/6 | 1.333 / 1.335 |
| 20,000 / 1 | 1.078 [1.075, 1.081] | 6/6 | 1.084 / 1.078 |
| 100,000 / 1 | 1.011 [1.004, 1.019] | 5/6 | 1.012 / 0.999 |
| 611,756 / 1 | 0.988 [0.981, 0.996] | 1/6 | 0.983 / 0.983 |
| 611,756 / 8 | 0.995 [0.981, 1.008] | 2/6 | 1.001 / 1.021 |

The full-N K=8 marginal ratio and paired interval differ materially; process
means have about 40.1/40.9 ms modes. Retain this variability and both sustained
orders: the result does not establish a general Graph slowdown or speedup.
Settings were unchanged, clocks were not locked, and CPU/host resources were
shared. Full-N K=1 has a small repeatable slowdown under this contract, but its
cause is unresolved without the missing profiler evidence.

B/C query-loop CPU time remains approximately **100% of one core** at every
completed shape. Full-N sampled device-memory peaks are about 13.3 GiB for B/C,
and whole-process GPU-utilization sample medians are 100% (native A: 94% at K=1).
These are 100 ms whole-process samples, not allocation attribution, query-only
utilization, SM occupancy, or an achieved-bandwidth measurement. Small-N sampling
can miss the short query interval entirely. Graph has not solved CPU occupancy
in this blocking driver. Its synchronous completion path is a candidate for
follow-up diagnosis, not a measured busy-wait attribution.

## Claim and decision ledger

All measurements below belong to `gts_20260923_graph_scale_words` and are
recomputed in [EVIDENCE.json](EVIDENCE.json), including raw hashes, every retained
process mean/order, quantiles, and the rejected receipt. Collection spans
2026-09-23/24 in Asia/Shanghai on the pinned GPU/toolkit below.

| Claim | State | Evidence and exact boundary | Allowed conclusion / reopen condition |
|---|---|---|---|
| Full output correctness at six shapes | measured | 88 complete-output oracle checks; 46 clean sanitizer runs; 1,024-query stress per mode/shape | Exact tested IDs, radii and immutable Words trees only; no update/service certification |
| Graph improves small-N completed-query latency | measured | Six rounds and two sustained orders; 2,000 and 20,000 only pass the declared gate | Shape-local benefit, not all GPU trees or all shapes |
| Applying the same Graph pipeline is sufficient at large N | rejected as a performance promotion | 100,000 has only 1.011x marginal gain; full-N K=1 is slower; K=8 is variable; retained ordinary stream is the comparator | Do not revive the unchanged large-N pipeline as a >5% speedup; reopen with an attributable work/parallelism change and fresh matched measurements |
| K=32 large-Graph performance | unvalidated | Correctness/sanitizers/stress passed; foreign activity rejected timing_1_C; remaining rounds/sustained absent | No speedup number until an independently identified continuation completes |
| CPU submission versus GPU-kernel/copy attribution | partial | Identical source enqueue and byte/capacity accounting; new NSYS traces absent | No new measured kernel-count, copy-time, gap, or bottleneck attribution |

Implementation status: the scaled driver is correct on the tested gates, not a
production replacement. Mechanism status: Graph is useful for the small tested
shapes but does not establish a large-N win. Thesis impact: this remains an
engineering attribution, not a novel GPU-tree mechanism. The next diagnostic
step is the missing NSYS comparison, then a separately pinned test of work or
parallelism rather than merely capturing more serial queries.

## Scope and comparison

The pinned author source stays byte-identical. A calls original query functions
with a configured height limit and a common result-delivery driver. B scales the
previous fixed-capacity ordinary-stream pipeline. C captures exactly B's enqueue
function. No result fusion, traversal deduplication, layout transformation, distance
optimization or prefetch is mixed into B/C. A is not the untouched default-height
main executable: leaving the default height at three would not produce a valid
full-data tree under the 20-object leaf contract.

The common driver selects enough levels using the original partitioner's maximum
last-child remainder. It validates that leaf intervals exactly partition N, leaves
fit 20 objects and tree IDs are a permutation of the input before any query.

| Data points | Height | Node slots | Object slots | Fixed B/C output bytes/query |
|---:|---:|---:|---:|---:|
| 2,000 | 3 | 111 | 2,220 | 17,764 |
| 20,000 | 4 | 1,111 | 22,220 | 177,764 |
| 100,000 | 5 | 11,111 | 222,220 | 1,777,764 |
| 611,756 | 6 | 111,111 | 2,222,220 | 17,777,764 |

All sizes use 64 changing deterministic IDs, exact byte-string edit distance,
inclusive radius four, self matches, immutable data and full native-ordered
host IDs/distances/counts. The largest data file is byte-identical to the source;
smaller cases are deterministic evenly spaced subsets. Capacity is conservative:
object slots are all node slots times 20, not actual matches or actual leaf count.

K=1 measures one completed query. At full N, K=8 and 32 put a sequential query
bundle into one stream/graph with a single final completion. Each query retains
its own pinned input and output slots while device scratch is reused in order.
**This is not query-parallel batching.** Report bundle completion and amortized
query time separately; they are not individual response-time measurements.
B/C at K=32 reserve 568,888,576 bytes of host staging. A returns only valid
results; fixed-size padding and output traffic are charged to B/C.

## Frozen measurement

See [CONTRACT.md](CONTRACT.md) for the preregistration and append-only collection
notes. Six fresh-process orders: ABC,CBA,BCA,ACB,CAB,BAC. Each process has 64 warmup
queries and 256 retained queries. Host-wall scope includes input preparation,
submission, finished full host delivery and A per-query teardown. Output hashing
is outside the query interval but inside reported loop CPU time. Construction,
setup, capture and first bundle are separately reported. B/C use identical native
kernels and scans; one-time output initialization has an explicit setup-only
completion before use by the nonblocking stream.

Primary: ratio of median process means of amortized query time. Secondary: paired
geometric ratio and exact 6^6 percentile bootstrap interval over six process log
ratios. A shape is accepted only if every C process wins, paired lower 95% bound
exceeds 1.05, both 1024-query sustained orders avoid >5% regression, and all gates
pass. Any component regression is retained. These bounded repetition runs are
not a production or thermal-steady-state certification. CPU/GPU settings are not
changed, CPU is shared, and monitoring cannot rule out uncooperative transient
jobs between samples.

## Reproduce

Only this directory and existing pinned public helpers are needed; original
source/data are external inputs and are not redistributed. Python 3.10+ standard
library, C++17 compiler, CUDA 13.1, NSYS and Compute Sanitizer are required. Do not
use Python `-O` or C++ `-DNDEBUG`: fail-closed gates use assertions. Preparation
requires a fresh output root and verifies eight source hashes plus the full
Words hash. `AUTHOR_SOURCE_ROOT` contains `GTS/`.

```bash
D=diagnostics/graph_scale_20260923
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$SCRATCH"
python3 "$SCRATCH/fixtures.py" prepare "$WORDS" "$SCRATCH"
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info \
  -Isource/include graph_bench.cu -o bin/graph_bench)
(cd "$SCRATCH" && c++ -std=c++17 -O3 oracle.cpp -o bin/oracle)
python3 "$D/test_cpu.py"
# CPU reference: uint8 full-DP distances, query-major 64 x N, not GPU-generated.
python3 "$SCRATCH/fixtures.py" oracles "$SCRATCH"
# GPU 0 must be explicitly admitted and idle. Each suite holds its existing lock.
CASES='n2000_k1 n20000_k1 n100000_k1 n611756_k1 n611756_k8 n611756_k32'
for phase in smoke gates timing; do
  python3 "$SCRATCH/suite.py" "$SCRATCH" "$phase" $CASES || exit 1
done
python3 "$SCRATCH/suite.py" "$SCRATCH" profile n611756_k1 n611756_k32
```

The CPU oracle is independently checked against the existing Python full-table
DP on nonperiodic byte strings, empty strings and high bytes. Smoke creates the
ordered count/ID/distance hashes only after full-output CPU correctness and native
order agreement. Runtime receipts record frozen binary/input hashes and reject
foreign activity, runtime errors, mismatches and timeouts. Run directories cannot
be overwritten. Sanitizers cover every N and both enlarged bundle sizes; boundary
checks cover radius zero and all-hit radius 256, plus B/C empty-frontier probes.

`analyze.py EXTRACTED_ROOT ARCHIVE OUTPUT_JSON` verifies source/data/CPU oracle
pins, raw receipts, full outputs and runtime hashes. Without `interruption.json`
it requires the full planned inventory and matched node-level NSYS signatures.
For this archived interruption it admits only the exact known partial inventory,
checks the failed receipt and foreign-activity record, and emits neither a K=32
comparison nor NSYS measurements. The five complete primary/sustained comparisons
are recomputed without using the contaminated process. Archived oracle
process receipts in `logs/oracle_retry_N.json` additionally bind the measured
reference executable to each generated oracle. The publication contains only
portable code, curated numbers and hashes; keep source copies, fixtures, raw
reports, commands and exact host records in the private evidence archive.


## Evidence preservation and continuation

Raw archive SHA256:
`3cbff9336f881cd25108192a91a50bd3c22a12b9fbd65b3514248dd67a8c4e72`.
Measured CUDA source SHA256:
`75ba007721f255d4680f1351a35a084c30e2a9ae75922cdc876c99338335d484`.
Measured executable SHA256:
`ef898b0709155c2192c6032a06282fa455cd8c0488cbb8b331fff67ebd276bcf`.

The archive preserves original source copies, both preparation attempts, CPU
oracles, all completed/rejected run directories, isolation samples and the
interruption record. It is private and not redistributed. A continuation must
preserve this snapshot, recheck GPU 0 admission, and identify new timing runs
separately; never overwrite or silently substitute the interrupted round. The
reproduction recipe above describes a fresh complete campaign, not a command to
resume in the occupied run directories. The public oracle-receipt helper was
added after collection using the same reference command/receipt schema; measured
CUDA source, benchmark runner and CPU-oracle source remain byte-identical.
