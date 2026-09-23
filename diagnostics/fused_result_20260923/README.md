# GTS stable result-selection fusion

**Implemented and accepted as a bounded hot-query prototype.** Fusing result
counting, rank scan, stable compaction and final ID projection reduces completed
query latency from **108.71 to 60.38 us (1.800x)** against the freshly remeasured
unfused CUDA Graph control. This is a measured engineering improvement, not a
novel GPU-tree algorithm or an all-workload result.

## What changed

`fused_result.cuh` adds one 512-thread CTA. Each 512-slot tile cooperatively scans
binary hit flags; the scan supplies both stable output ranks and its total. A
carry connects consecutive tiles. Hit lanes directly emit mapped IDs and original
distances to the final output. Thread 0 publishes the final count, including zero.

This replaces the F4/F5 sequence: duplicate result reductions, singleton count
scan, hit scan, intermediate compaction and separate projection. It does **not**
fuse leaf distance computation with global result completion: independent leaf
CTAs still finish across a same-stream kernel boundary. The deletion-prefix scan
remains and its cost is charged. Traversal, candidate selection, leaf evaluation,
input/output copies, capacity and stream completion are unchanged.

The original GTS source and previous Graph experiment remain untouched.
`prepare.py` checks an exact comparator hash and generates a separate driver
with D/E modes. B/C retain the original enqueue branch. Even now-unused temporary
buffers remain allocated in D/E to isolate this change; this experiment does not
claim optimal workspace size or improved device-memory footprint.

## Same-campaign results

Words N=2000; 64 deterministic distinct query IDs; batch one; inclusive radius 4;
immutable height-3 tree; 111 candidate and 2220 result slots; RTX PRO 6000
Blackwell Server Edition, CUDA 13.1.115, driver 590.48.01, `sm_120`.

| Mode | Submission / selection | Median process-mean query us | Median loop CPU us/query |
|---|---|---:|---:|
| B | Stream / unfused | 143.40 | 143.57 |
| C | Graph / unfused | 108.71 | 108.84 |
| D | Stream / fused | 81.70 | 81.83 |
| E | Graph / fused | 60.38 | 60.49 |

C/E isolates fusion under Graph: **1.800x**. B/D isolates fusion under ordinary
stream submission: **1.755x**. Neither ratio borrows a previous campaign's timing.
Both use the same binary, fixed-capacity workspace and completed host delivery.
The timer includes input preparation/transfer, device query and host count/ID/
distance readiness, but excludes output hashing. Loop CPU includes hashing.
CPU time/query falls; **CPU utilization remains about one core**, not a released
CPU core or reduced whole-host saturation.

Six independent rounds use the preregistered orders `BCDE, EDCB, CEBD, DBEC,
DEBC, CBED`, 4096 queries per process after 64 warmups. E wins all six C/E pairs.
The paired geometric-mean ratio is **1.797x**, exact paired-bootstrap 95% interval
**[1.786, 1.805]**. This interval describes paired log ratios, not the 1.800x ratio
of medians. B/D paired ratio is **1.754x [1.734, 1.776]**, also six wins.
All raw process order, per-query samples and p10/p50/p90 are retained;
[EVIDENCE.json](EVIDENCE.json) contains the curated ledger.

### Sustained repetition and setup boundaries

Each row below is a fresh 16384-query process pair within a four-mode round:

| Radius / selectivity | C/E, forward order | C/E, reverse order |
|---|---:|---:|
| 0, exact matches | 1.296x | 1.313x |
| 4, normal workload | 1.799x | 1.807x |
| 256, all 2000 records | 1.850x | 1.872x |

No required C/E or B/D sustained row regresses. These loops last roughly seconds,
not a minutes-long thermal or production-service test. Clocks were not locked;
GPU 0 was admitted idle under its existing advisory lock, monitored, and returned
to idle. Another GPU's foreign workload was excluded and untouched.

| One-time metric, median of six processes | C | E |
|---|---:|---:|
| Workspace setup including capture, us | 1747.85 | 1512.40 |
| Capture/instantiate subset, us | 702.83 | 568.22 |
| First completed query, us | 224.94 | 170.13 |

Tree construction/load and warmup are outside hot-query timing. The inherited
driver retains whole-process-before-cleanup and loop times, but does **not**
isolate load/tree-construction time; no whole-program or cold-start speedup is
claimed. Full cold-start attribution remains unvalidated, rather than assigning
that residual to a guessed phase.

## Mechanism and correctness evidence

- NSYS node traces verify **24 -> 17 GPU kernels/query**, for all 193 recorded
  queries per mode. The first 14 kernels and retained deletion-prefix scan have
  identical names, geometry and resources. Both modes still issue one Graph
  launch/query. Fusion removes seven GPU launches, not just host submissions.
- Diagnostic NSYS time is 42.45 us for the old count kernel alone versus 3.84 us
  for the new combined selector; summed kernel time is 101.23 versus 50.46 us.
  These perturbed, differently scoped kernel numbers are **not** a public
  speedup ratio. The result above uses clean completed-query wall time.
- Final linked selector resources: **40 registers/thread, 0 stack/local bytes,
  3232 shared bytes**. The pre-link ptxas field is 2208 shared bytes; retain both
  stages rather than conflating them. No spill loads/stores or static LDL/STL
  are observed. Selected-function SASS and binary hashes are retained privately;
  no new NCU collection is needed to establish the removed-launch mechanism.
- **19 full-output runs** pass independent CPU byte-edit-distance membership,
  distance and count checks, plus same-round native A ordering at 0/4/256.
  B/C/D/E return empty results for the negative-radius robustness probe; A's
  previously documented zero-grid fault is not silently repaired or re-admitted.
- **16 sanitizer runs** pass. B/C/D/E pass memcheck and synccheck; D/E also pass
  initcheck and racecheck. A standalone selector passes all four tools with
  **132 cases per invocation**: tile boundaries, zero/one/max capacities,
  nonidentity prefix maps, poisoned inactive capacity, alternating large/small/
  empty states, stable payloads, tail guards and fresh allocations.
- Each B/C/D/E mode additionally passes **16384 changing-query stress calls**.
  Every timing/stress/profile row checks count and ordered full-output hashes
  generated only after full independent validation. Query IDs vary within the
  fixed 64-ID set; this is not independent coverage of every possible query.

The full-query campaign has no insertions/deletions. Synthetic prefix-map tests
validate projection arithmetic, not dynamic update visibility. No larger tree,
concurrent query, kNN, full-dataset, other GPU-tree or production deployment claim.
The one-CTA selector is deliberately bounded, not a universal large-output design.

## Reproduce

The repository supplies only the new kernel, tests, generator and analysis.
Original author source and Words data must be supplied separately; do not use
Python `-O` or C++ `-DNDEBUG`. Every output root/run label must be fresh.
`AUTHOR_SOURCE_ROOT` contains `GTS/`. Use the actual toolkit executable (the
relocated `nvcc` launcher on this host could not resolve headers).

```sh
D=diagnostics/fused_result_20260923
python3 diagnostics/original_tree_profile/make_fixture.py "$WORDS" "$FIXTURES" --sizes 2000
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$FIXTURES" "$SCRATCH"
(cd "$SCRATCH" && "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
  -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -Xptxas=-v \
  -Isource/include graph_bench.cu -o bin/graph_bench && \
 "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -lineinfo -Xptxas=-v \
  test_selector.cu -o bin/test_selector)
python3 diagnostics/graph_query_20260923/oracle.py make \
  "$SCRATCH/fixtures/words_2000.txt" "$SCRATCH/fixtures/queries.qid" "$ORACLE"
# Admit GPU 0 first; reuse its existing advisory lock and exclude other jobs.
python3 "$D/suite.py" "$SCRATCH" smoke --gpu "$ADMITTED_UUID"
python3 "$D/verify_full.py" "$SCRATCH" "$ORACLE"
python3 "$D/suite.py" "$SCRATCH" gates --gpu "$ADMITTED_UUID"
python3 "$D/suite.py" "$SCRATCH" timing --gpu "$ADMITTED_UUID"
python3 "$D/suite.py" "$SCRATCH" trace --gpu "$ADMITTED_UUID"
python3 "$D/test_cpu.py"
```

`summarize.py RAW_ROOT ORACLE ARCHIVE OUTPUT_JSON` reproduces the curated record
from the preserved campaign archive (including resource/SASS exports), rejects
missing or mislabeled observations and checks exact source/binary/data pins and
actual process order. Compare its output byte-for-byte with `EVIDENCE.json`.
The archive SHA256 is
`7ce2524e82eb8b6cf64b3109d539191ee993836956480537c551446c811ffd7b`.
Sources, binaries, fixture data, profiler reports and machine records stay out
of Git. The initial compile-path failure is retained; it ran no GPU work.

Decision and predeclared gates: [CONTRACT.md](CONTRACT.md). Candidate selection
(F2) is a separate next attribution experiment; it is not included in this gain.
