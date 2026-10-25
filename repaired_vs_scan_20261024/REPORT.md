# Repaired GTS vs strong baselines — no GPU result

**Decision: undecided.** No GPU benchmark was launched and zero latency samples
were collected. The required comparison, correctness/sanitizer gates, and
work-count experiment are incomplete. This checkpoint cannot support a systems
paper claim, establish R's cumulative gain over A, or close the low-dimensional
route.

## Why the attempt stopped

The original physical GPU 0 / UUID was first observed idle. At 05:56:21 UTC on
2026-10-25 it had a foreign `VLLM::Worker_TP0` (PID 561143, 80,730 MiB), and at
05:57:50 UTC the same process remained active (80,896 MiB, GPU utilization 78%).
No task-owned GPU workload had started. The attempt stopped without signaling
that process, changing GPU settings, switching cards, or replacing samples.
A later advisory-lock-held read-only check at 05:59:55 UTC was idle; it is retained
in [the admission record](evidence/GPU_ADMISSION.json), not treated as a restart.
A new complete attempt was requested for clarification; no automatic restart
occurred in this delivery.

The driver is now 590.48.01, versus the older campaign's driver state. Historical
r4 timings and speedups were not reused. Current CUDA is 13.1.115. Eight pinned
original author files match exactly; the broken original dataset mount was not
used to invent new input: the retained complete fixtures match their known
Words/Tloc SHA-256 hashes.

## Required workload table

All times would be complete host-ready **batch latency in ms**, not per-query
latency. `NA` means not measured, never zero. CPU hit medians are reference output
sizes only, not GPU work counters or a GPU correctness pass.

| Dataset | Target hits | Radius | Q | CPU median hits/query | A ms | R ms | S ms | ArborX ms | R/S [95%] | R/A [95%] |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| words | 10 | 3 | 1 | 15 | NA | NA | NA | N/A | NA | NA |
| words | 10 | 3 | 32 | 28.5 | NA | NA | NA | N/A | NA | NA |
| words | 10 | 3 | 1024 | 21 | NA | NA | NA | N/A | NA | NA |
| words | 100 | 4 | 1 | 352 | NA | NA | NA | N/A | NA | NA |
| words | 100 | 4 | 32 | 279 | NA | NA | NA | N/A | NA | NA |
| words | 100 | 4 | 1024 | 133.5 | NA | NA | NA | N/A | NA | NA |
| words | 1000 | 6 | 1 | 39907 | NA | NA | NA | N/A | NA | NA |
| words | 1000 | 6 | 32 | 16491 | NA | NA | NA | N/A | NA | NA |
| words | 1000 | 6 | 1024 | 6126 | NA | NA | NA | N/A | NA | NA |
| tloc | 10 | 0.05369744822 | 1 | 2 | NA | NA | NA | NA | NA | NA |
| tloc | 10 | 0.05369744822 | 32 | 16 | NA | NA | NA | NA | NA | NA |
| tloc | 10 | 0.05369744822 | 1024 | 14 | NA | NA | NA | NA | NA | NA |
| tloc | 100 | 0.2003019303 | 1 | 26 | NA | NA | NA | NA | NA | NA |
| tloc | 100 | 0.2003019303 | 32 | 168 | NA | NA | NA | NA | NA | NA |
| tloc | 100 | 0.2003019303 | 1024 | 169 | NA | NA | NA | NA | NA | NA |
| tloc | 1000 | 0.5796645284 | 1 | 122 | NA | NA | NA | NA | NA | NA |
| tloc | 1000 | 0.5796645284 | 32 | 1146.5 | NA | NA | NA | NA | NA | NA |
| tloc | 1000 | 0.5796645284 | 1024 | 1343 | NA | NA | NA | NA | NA | NA |

ArborX is not applicable to Words. Its native Tloc configuration failed at
`find_package(Kokkos 4.5 REQUIRED CONFIG)`; default CMake search did not locate a
usable Kokkos package. This is not a claim that no installation exists anywhere.
[Actual command, pinned upstream commit, and failure log](evidence/ARBORX.json).
The attempt used native [ArborX source](https://github.com/arborx/ArborX/blob/3a20eaba22bd8b6c13d6b32064a2086a3ce1c993/CMakeLists.txt),
not a proxy; neither a native benchmark nor an adapter was built.

## Completed CPU preparation and its limits

- 16 calibration and 1024 test IDs per dataset are deterministic and disjoint.
  All three radii were frozen before test-oracle generation. Query IDs, radii,
  hashes and complete CPU-output manifests are retained in `evidence/`.
- Words integer radii 3/4/6 yield calibration median counts 17/124.5/4521.5,
  not exactly 10/100/1000. Integer distances and ties overshoot the targets;
  the predeclared smallest qualifying radius was retained. No retuning followed.
- At Q1024 the test median counts are Words 21/133.5/6126 and Tloc 14/169/1343.
  Sampling differences are retained, not corrected using test data.
- Both datasets' complete independent CPU oracle files were generated and
  structurally audited: all IDs are sorted/in-range, distances finite/in-radius,
  counts monotonic across radii, self IDs present at zero distance, no trailing
  bytes. Known-answer CPU tests pass locally and remotely. These checks do not
  compare any GPU output and cannot replace sanitizer or Graph validation.
- The CPU oracle/header/data pins are verified. Combined R assembly/CUDA build,
  native-batch S, the exact host-ready campaign runner and instrumentation are
  still pending, not "implemented and validated".

## Work counts and required gates

| Requested measurement/gate | A | R | S | ArborX |
|---|---|---|---|---|
| Distance calls | not measured | not measured | not measured | not measured |
| DP cells / coordinates evaluated | not measured | not measured | not measured | not measured |
| Candidate leaves | not measured | not measured | not applicable | not measured |
| Effective payload-thread fraction | not measured | not measured | not measured | not measured |
| Complete ID/distance/count GPU vs CPU | not run | not run | not run | not run |
| Native ordered A/R bitwise comparison | not run | not run | not applicable | not applicable |
| Memcheck / synccheck | not run | not run | not run | not run |
| Six paired fresh-process rounds | 0 | 0 | 0 | 0 |

No R/S or R/A point estimate, confidence interval, process-win count, kernel
profile, or workload count can be calculated from this attempt. The oracle output
sizes are not estimates of GPU distance work. None of the old gains were multiplied.

## Positioning and next action

1. **GPU metric-tree execution-paper candidate: not established.** R/S<=1 across
   the required matrix and a >=2x win somewhere have not been tested.
2. **Attribution/analysis positioning: not decided by this attempt.** Earlier
   evidence of implementation defects remains earlier evidence, not a newly
   measured R/A result against strong scan.
3. **Tloc low-dimensional route: not closed.** R/ArborX>=5 was not measured.
4. **No universal tree-index conclusion.** These missing measurements are a
   resource/prerequisite limitation, not mechanism-level negative evidence.

Before resuming, obtain a separate complete-attempt decision and re-admit the
intended GPU under lock. Compose/validate R and strong native-batch S; then run
all required correctness, sanitizer, stress, instrumentation and six paired
rounds without replacement. Resolve Kokkos for native ArborX without substituting
an in-house BVH. Strong-baseline batching is explicitly required by
[the pre-GPU amendment](AMENDMENTS.md). Native Q1024 complete-output support is
not inferred from an API parameter; serial bundles must be labeled as such.
Optional Deep was not run. No paper text or original production/evidence file
was modified, and this branch is not merged into main.
