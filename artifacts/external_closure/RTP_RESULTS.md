# Direct cumulative and strengthened-reference R/T/P results

**All 18 fresh short-workflow processes passed complete ordered output and state checks.**
This is internal evidence, not an external static or dynamic ranking.

Original FP32 GIST **N=1,000,000, D=960, B1, K8**, radius bits `0x3f34a3d8`.
Each trace contains 336 events: 128 range, 128 kNN, 40 inserts, 40 deletes,
and two real threshold-10 rebuilds. R uses common numerical/safety repairs,
not untouched original GTS. T and P both use TILED construction.

| Mode | Range | kNN | Build |
|---|---|---|---|
| R | Staged common-repair reference | FULL | NODE |
| T | Same staged reference | FULL | TILED |
| P | PAR_STRONG | FULL | TILED |

## Direct continuous workflow result

| Comparison | Paired geometric reference/candidate |95% paired interval|Wins|Time reduction|
|---|---:|---:|---:|---:|
|R/P|13.423096x|[13.276551, 13.633182]|6/6|92.55%|
|T/P|6.448319x|[6.367368, 6.555937]|6/6|84.49%|
|R/T|2.081643x|[2.075815, 2.089109]|6/6|51.96%|

Ratios above 1 favor the denominator candidate. These are directly paired
measurements, not the product of historical 1.684797x and 8.029943x.
Continuous time includes complete Host-ready answers, serialized update ACKs,
buffer preparation, compaction/construction, safe-bound refit, mirror/PAR
refresh where required, and final service-device release/synchronization.
Initial setup, cloned 19-event warmup, parsing and context initialization are
separately recorded. Host answer allocation and complete D2H delivery are
included; later client consumption/release of retained Host answers and
file serialization are excluded. No leak-clean or production-ready claim.

|Round / order|R seconds|T seconds|P seconds|
|---|---:|---:|---:|
|1 / RTP|86.206411|41.586940|6.482499|
|2 / PTR|86.277559|41.106516|6.526575|
|3 / TPR|86.202856|41.398337|6.383917|
|4 / RPT|86.139044|41.529909|6.477201|
|5 / PRT|86.167238|41.431958|6.196728|
|6 / TRP|86.287822|41.444472|6.475446|

## Setup-inclusive sensitivity (measured setup + continuous trace)

|Comparison|Paired ratio|95% interval|
|---|---:|---:|
|R/P|13.775499x|[13.646121, 13.965145]|
|T/P|5.374709x|[5.313110, 5.452219]|
|R/T|2.563022x|[2.556300, 2.571848]|

This second denominator still excludes warmup, parsing and initial context;
it is not fresh-process wall time. The JSON includes every raw setup/warmup,
marginal ratio, p10/median/p90, per-process tail latency and order stratum.

## Attribution boundaries

|Process diagnostic, median seconds|R|T|P|
|---|---:|---:|---:|
|Range ACK sum|37.633604|37.636505|2.685291|
|kNN ACK sum|0.949660|0.950195|0.877010|
|Inclusive rebuild sum|47.498930|2.760248|2.815083|
|Trace CPU user|85.712581|40.960613|6.205289|
|Final device service release|0.065427|0.070168|0.068730|

Inclusive rebuild and component intervals overlap: never sum this table to
derive a speedup. R/T measures construction mapping under staged range;
T/P measures PAR organization with both constructions strengthened; R/P is
the direct final combination. CPU user time includes CUDA polling/control,
not proof of CPU distance computation. This campaign does not isolate
coalescing, traffic reduction, launch removal or numerical work as the sole
cause; no new NCU/NSYS evidence was collected.

## Validation, statistics and remaining scope

- One unchanged binary serves all three modes. Five T bridge processes pass:
  bounded full workflow, million-row rebuild prefix, memcheck/racecheck/synccheck.
- All 256 query payloads/process and all 336 state transitions are byte/state
  identical to the previously exhaustive ordered-FP64-qualified parent.
- Six permutations balance each method pair 3/3. Bootstrap 20,000, seed 2026101002;
  speedup requires lower 95% bound>1, at least5/6 wins and both strata>1.
  These intervals describe repeat-run variation on fixed observed queries,
  not dataset/query-distribution generalization.
- Same isolated single RTX PRO 6000 Blackwell GPU, CUDA 13.1/SM120; shared
  CPU host/NUMA placement, foreign jobs untouched, no clock/power changes.
- The original 96 B context-symbol full-leak boundary remains unresolved.
- New primaries 18/102; cumulative GPU qualifiers 25/32. External static B
  still has zero new primaries. Earlier native Faiss kNN counterevidence and
  GPU_TREE membership blocker remain; no external superiority is inferred.
- No new kernel optimization, precision, dataset,100k/1B, long campaign or
  manuscript publication. Standard tiling is not claimed as new research.

See [raw paired evidence](evidence/RTP_RESULTS.json), [contract](RTP_CONTRACT.json),
[attempts](RTP_ATTEMPTS.md), and [remaining external gates](NEXT_GATES.md).
