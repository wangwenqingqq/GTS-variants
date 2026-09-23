# Independent traversal fusion and parent-pivot reuse

**Measured result: accept traversal fusion (F) as a bounded prototype; do not
promote the parent-pivot reuse implementation (P).** On the newly admitted idle
GPU 1, F passes all predeclared gates. P removes 90% of evaluated pivot distances
but loses every primary timing pair. No production dispatch or original author
source was changed, and no combined F+P candidate was tested.

The domain is **Words N=2000, batch one, immutable height-3/fanout-10 tree**,
64 deterministic distinct queries, byte edit distance, inclusive radius, and
complete ordered CPU-resident IDs/distances/count. Both candidates and the keeper
already use the same result-selector fusion from `6221ae9`; these numbers are
**not** speedups against wholly unmodified GTS. Construction, setup and Graph
capture are excluded; transfers and host completion are included.

## Independent comparisons and completed-query timing

RTX PRO 6000 Blackwell Server Edition, 188 SMs, CUDA 13.1.115, driver 590.48.01,
600 W limit unchanged, clocks unlocked. All denominators were remeasured on
GPU 1 in this campaign; none comes from the previous GPU 0 campaign.

| Variant | Stream / Graph modes | Traversal change | NSYS kernels/query | Graph us/query | Stream us/query |
|---|---|---|---:|---:|---:|
| Keeper | D / E | Original traversal | 17 | 59.854 | 79.350 |
| F: fusion only | G / F | Init + two walk/clear pairs become one CTA kernel; original per-child distances preserved | 13 | 54.216 | 70.647 |
| P: pivot reuse only | Q / P | One distance per live parent with nonempty children, shared publication, original level boundaries | 17 | 60.706 | 80.209 |

Times are medians of six fresh-process means, each with 64 warmups and 4096
completed queries at radius 4. Query samples exclude output hashing; loop CPU
includes it. No candidate compaction, leaf evaluation, output selection, copies,
capacity or host-wait change is bundled with either traversal candidate.

| Comparison | Ratio of process medians | Paired geometric mean | Exact paired-bootstrap 95% interval | Process wins |
|---|---:|---:|---:|---:|
| E/F: Graph fusion | 1.103978x | 1.103093x | [1.100167, 1.106016] | 6/6 |
| E/P: Graph pivot reuse | 0.985961x | 0.983397x | [0.977967, 0.987346] | 0/6 |
| D/G: stream fusion | 1.123178x | 1.116062x | [1.095499, 1.138844] | 6/6 |
| D/Q: stream pivot reuse | 0.989287x | 0.989139x | [0.986172, 0.992114] | 0/6 |

Ratios are keeper/candidate, so greater than one is faster. F reduces median
Graph latency by 9.42%; P increases it by 1.42%. The bootstrap resamples the six
paired process log ratios, not individual correlated query samples. The full
process order, order splits and per-process query p10/p50/p90 are retained in
[EVIDENCE.json](EVIDENCE.json); no unfavorable observation is removed.

### Sustained screen: 16384 queries per process

Each cell is keeper/candidate for the displayed radius and process order.

| Radius | Order | E/F | E/P | D/G | D/Q |
|---:|---|---:|---:|---:|---:|
| 0 | DEFGPQ | 1.059223 | 0.971023 | 1.104639 | 0.975415 |
| 0 | QPGFED | 1.052629 | 0.989604 | 1.133835 | 0.982343 |
| 4 | DEFGPQ | 1.098537 | 0.988367 | 1.143347 | 1.018395 |
| 4 | QPGFED | 1.098449 | 0.989376 | 1.172127 | 1.039045 |
| 256 | DEFGPQ | 1.074101 | 0.995554 | 1.114261 | 1.004956 |
| 256 | QPGFED | 1.055530 | 0.988006 | 1.108415 | 0.978505 |

Both avoid a >5% sustained regression, but that does not rescue P's failed
primary win/confidence gates. P has some favorable stream sustained rows; the
negative decision is implementation- and contract-specific, not a universal
claim that pivot reuse cannot help.

## Correctness, safety and resource gates

All **133 primary observations** pass: 27 complete-output/oracle/native-order
runs; one clean 352-case traversal regression; 24 sanitizer runs; six stress
runs of 16384 queries; 36 primary timing processes; 36 sustained processes; and
three NSYS node traces. Native A anchors exact ordering at radii 0/4/256. All
six measured modes also pass radius -1; native A is excluded there because of
its pre-existing zero-grid failure. Diagnostic patterns include first-child
empty, whole-group empty and alternating empty children. Production kernels
have no work counters.

Memcheck/synccheck cover all six measured modes; initcheck/racecheck cover both
F/P variants in stream and Graph. All four tools also cover the standalone
traversal regression. Complete oracle-approved ordered-output hashes are
checked throughout timing, stress and profiling, not just result counts.
Independent review additionally recomputed all 128000 CPU query-record distances.

The device had no compute process before/after each run and the campaign held
its advisory lock. One-second process monitoring found no foreign activity in
samples that occurred. **All 36 primary timing processes ended before their
first one-second process sample**, so their process checks are empty: pre/post
checks plus an advisory lock do not prove continuous exclusion of transient,
uncooperative external work. The 100-ms GPU telemetry is retained separately.
No foreign process was signaled, no device setting changed, and GPU 1 was clear
at closure. Work on excluded GPUs was not touched.

| Selected production function | Registers/thread | Stack bytes/thread | Final shared bytes | Static LDL / STL sites |
|---|---:|---:|---:|---:|
| Original `findNextRnn` | 50 | 47528 | 0 | 12 / 55 |
| F `fusedTraversal<false>` | 52 | 47528 | 0 | 12 / 55 |
| P `dedupLevel<false>` | 48 | 47528 | 1064 | 12 / 55 |

All three report zero ptxas spill loads/stores. The explicit full DP table and
local-memory instructions remain; `LOCAL:0` does not mean zero stack traffic.
P declares 40 bytes of shared distance state; 1064 is the final linked report,
including compiler/linker overhead. Registers are not a performance claim.
Executable and selected-function normalized SASS hashes are preserved.

## What the independent mechanisms establish

**Measured launch redundancy:** NSYS observes 193 queries per Graph trace,
17/13/17 kernels per E/F/P query. F changes traversal from five launches to one;
its downstream signature is identical. Traversal kernel-duration sums in NSYS
are 17.932/13.226/19.260 us per E/F/P query. These instrumented sums explain the
structure but are not the public latency denominator above.

**Measured arithmetic redundancy:** at radius 4 over 64 diagnostic queries,
original and F each evaluate 6630 query-child pivot distances; P evaluates 663
query-parent distances. Child predicates, intermediate flags and complete final
outputs agree. This is a 90% reduction in evaluated pairs, not a 10x latency gain.

**CPU remains busy:** median loop CPU time per query is 59.980 us for E, 54.345
for F and 60.828 for P; loop CPU/wall remains approximately 100% of one core in
all modes. F lowers CPU time per completed query, but has not eliminated CPU
occupancy or established which host call consumes it. This is process CPU
accounting including hashing, not sampled attribution of CPU distance arithmetic.

### Focused NCU follow-up

The [pre-collection plan](NCU_FOLLOWUP.md) and [validated exports](NCU_EVIDENCE.json)
cover the first query's two levels only, same binary/device/radius, fixed D/G/Q
order, identical sections, 16 replay passes, no clock/cache control. All 64
complete-output hashes pass after each run. Five selected launches are recorded:

| Mode / selected launch | Warp instructions | Avg. predicated-on threads/instruction | No-eligible scheduler cycles | Replayed us |
|---|---:|---:|---:|---:|
| D / level 1 | 2000 | 9.67 | 83.95% | 6.624 |
| D / level 2 | 9603 | 17.03 | 83.66% | 8.576 |
| G / fused traversal | 12902 | 17.03 | 88.94% | 13.792 |
| Q / level 1 | 2693 | 8.61 | 94.67% | 7.264 |
| Q / level 2 | 4029 | 11.67 | 94.42% | 9.216 |

The dynamic instruction metric is `smsp__inst_executed.sum`; participant ratios
use `smsp__thread_inst_executed_pred_on_per_inst_executed.ratio`. P's selected
level-kernel total is 6722 versus 11603 warp instructions (42.07% fewer, not 90%
fewer). Its level-1 instruction count increases. F's count includes initialization
and parent clearing, unlike the selected D/Q kernels, so those totals are not
an equal-work instruction comparison.

All five launches use **one 512-thread block on 188 SMs**. P retains both launch
boundaries and adds shared publication plus a CTA barrier; at most ten lanes
produce distances, rather than up to one hundred child lanes. P's selected
barrier-state/average-warp-latency ratios are 87.44% and 87.72%, alongside fewer
eligible warps. This supports a **readiness/parallelism-cost explanation**, not
proof that a particular source PC or the barrier alone caused the slowdown.
Warp-state shares are not application-wall-time shares. Occupancy percentages
use active-cycle denominators and must not be read as whole-device utilization.

NCU durations above are diagnostic replay measurements, with explicit uncontrolled
cache/clock warnings, not clean speedups or repeatability estimates. No source-PC
sampling or absolute local-memory traffic ledger was collected. InstructionStats'
zero placeholder per-opcode fields are not evidence of zero local instructions.
These limits do not alter the clean timing decision.

## Decision, claim boundary and reopen condition

| Claim / decision | Evidence state | Allowed scope and counterevidence |
|---|---|---|
| F speeds completed queries and removes four launches | measured | This immutable Words N=2000 batch-one contract only; all predeclared gates pass; no default dispatch change |
| P eliminates repeated sibling-pivot evaluations | measured | Diagnostic pair count and exact output checks; not equivalent to wall-time savings |
| This P implementation is a performance keeper | rejected | Zero of six primary wins in both Graph and stream; extra shared/barrier cost and fewer producer lanes; some sustained stream rows improve |
| P's added readiness cost offsets reduced work | inferred | Selected NCU scheduler/barrier evidence supports the explanation; no causal PC isolation or full-query counter average |
| Fusion solves CPU occupancy or fills the GPU | rejected for this implementation | One-core CPU ratio remains near 100%; traversal still has one CTA |
| Most/all GPU tree indexes have the same bottleneck | unknown from this campaign | No external index was run; generic fusion/pivot reuse are established mechanisms, not demonstrated novelty |

Keep F as a bounded candidate for the next separately contracted scale/batch
experiment, not as a universal implementation. Preserve P as negative evidence;
reopen only with a declared change that increases independent query/parent work
or removes the publication/producer bottleneck, and rerun the same correctness
and clean timing gates. Do not revive the same batch-one P solely because its
logical distance count is lower. No paper thesis or cross-index claim is promoted.

## Reproduce and evidence preservation

[CONTRACT.md](CONTRACT.md) retains the original GPU 0 plan and the user-authorized
**GPU 1 amendment recorded before execution**. [CHECKPOINT.json](CHECKPOINT.json)
remains the earlier compiled-only, zero-run checkpoint; it has not been rewritten
as a runtime pass. Exact source/data/binary identities and 133 receipts are linked
by hash in [EVIDENCE.json](EVIDENCE.json). All primary observations are retained.

`AUTHOR_SOURCE_ROOT` and `FIXTURES` provide the pinned external author source and
verified Words fixtures separately. Neither is redistributed. Use a fresh
scratch directory, admitted idle GPU, its existing advisory lock and actual
CUDA toolkit executable. Do not use Python `-O` or C++ `-DNDEBUG`.

```sh
D=diagnostics/traversal_ablation_20260923
python3 "$D/test_cpu.py"
python3 "$D/prepare.py" "$AUTHOR_SOURCE_ROOT" "$FIXTURES" "$SCRATCH"
(cd "$SCRATCH" &&
 for source in graph_bench test_traversal; do
   "$CUDA_HOME/bin/nvcc" -std=c++17 -O2 -arch=sm_120 -rdc=true -lineinfo \
     -Xcompiler=-fno-omit-frame-pointer -Xnvlink=--ignore-host-info -Xptxas=-v \
     -Isource/include "$source.cu" -o "bin/$source" || exit
 done)
python3 diagnostics/graph_query_20260923/oracle.py make \
  "$SCRATCH/fixtures/words_2000.txt" "$SCRATCH/fixtures/queries.qid" "$ORACLE"
# First record verified hardware/admission and acquire the admitted-device lock.
python3 "$D/suite.py" "$SCRATCH" smoke --gpu "$ADMITTED_UUID"
python3 "$D/verify_full.py" "$SCRATCH" "$ORACLE"
python3 "$D/suite.py" "$SCRATCH" gates --gpu "$ADMITTED_UUID"
python3 "$D/suite.py" "$SCRATCH" timing --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/timing.txt"
python3 "$D/suite.py" "$SCRATCH" trace --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/trace.txt"
```

Retain commands, stdout/stderr, all scratch artifacts, final `cuobjdump` resources
and selected-function SASS/normalization under `logs/`. The `logs/admission.json`
record contains GPU index/UUID/name, driver, CUDA, NSYS, architecture, power limit,
clock-lock state and authorization statement; record live values before execution.
The evidence summation is deliberately pinned to this campaign, not a generic
benchmark that silently accepts another configuration.

```sh
python3 "$D/summarize.py" "$SCRATCH" "$ORACLE" "$PRIMARY_ARCHIVE" "$OUTPUT_JSON"
# Optional fixed first-query NCU diagnostic; verified existing sudo policy only.
sudo -n python3 "$D/profile_ncu.py" "$SCRATCH" --gpu "$ADMITTED_UUID"
python3 "$D/summarize_ncu.py" "$SCRATCH" "$NCU_RAW_ROOT" "$NCU_ARCHIVE" "$NCU_JSON"
```

The primary summary initially rejected NSYS's `fusedTraversal<(bool)0>` spelling
because it expected `<false>`; only the analysis parser was corrected. No GPU
measurement, source, executable or acceptance threshold was changed. NCU's qid
parser was also corrected to consume the fixture's count header before curation.

Private archive SHA256 values:

- Earlier compiled checkpoint: `177c3a46985ab192e237924041ed7a4b22a04be50b41eba2748894753739c77c`.
- Complete primary run: `515a287951cae81e096965f7367cde64521dbca057a9363ddfb4387d64a22c83`.
- Focused NCU run: `5dcf3f5e9c1a085fb420c2536e8056ebd3647e620d02676fa60b01d1f21ed3f7`.

Raw data, external source, executables, profiler files, process identities and
machine routing remain excluded from Git. Rollback is selecting unchanged D/E.
