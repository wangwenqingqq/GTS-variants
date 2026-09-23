# Independent traversal fusion and parent-pivot reuse

**Checkpoint: implemented, compiled and statically reviewed; not runtime
validated or promoted.** GPU 0 was occupied by another benchmark and its
advisory lock was held. No GPU work was launched by this campaign and no foreign
process was changed. An alternate GPU had not been authorized at this checkpoint.
This is a resumable experiment, not a speedup result.

## Independent comparisons

| Variant | Stream / Graph modes | Traversal change | Intended launches per query |
|---|---|---|---:|
| Keeper | D / E | Unchanged original traversal | 17 |
| F: fusion only | G / F | Initialization + two walk/clear pairs become one CTA kernel; per-child distances unchanged | 13 |
| P: pivot reuse only | Q / P | Each level computes once per live parent with nonempty children, then broadcasts to unchanged child predicates | 17 |

These are **source-derived expected counts**, not collected runtime traces.
Both candidates use the same previously validated fused result selector as the
keeper. Candidate compaction, multi-CTA leaf distance, output projection, copies,
fixed capacity and host completion are held constant. There is no combined F+P
mode. Primary comparisons are E/F and E/P; D/G and D/Q check stream submission.

The domain remains Words N=2000, batch one, immutable height-3/fanout-10 tree,
64 deterministic distinct queries, full ordered host IDs/distances/count. Do
not generalize to a larger tree, another metric, updates or other GPU indexes.
Exact design, barriers, hypotheses and acceptance criteria: [CONTRACT.md](CONTRACT.md).

## Completed checks

- CPU generator regression passes: exact comparator pin, rejected source drift,
  separate F/P dispatch, common result path, and balanced six-process orders.
- Fresh benchmark and diagnostic executables compile for `sm_120` with CUDA
  13.1.115. Original upstream format warnings are retained in private build logs;
  compilation is not a CUDA correctness test.
- Independent read-only review confirms source-level barrier ownership, parent
  distance publication (including an empty first child), identical child
  predicates, and unchanged D/E downstream enqueue/timing logic.
- Generated source copied back from the build host matches local generation.
  Original author source and earlier campaign binaries remain untouched.

| Selected production function | Registers/thread | Stack bytes/thread | Final shared bytes | Static LDL / STL sites |
|---|---:|---:|---:|---:|
| Original `findNextRnn` | 50 | 47528 | 0 | 12 / 55 |
| F `fusedTraversal<false>` | 52 | 47528 | 0 | 12 / 55 |
| P `dedupLevel<false>` | 48 | 47528 | 1064 | 12 / 55 |

All three report zero ptxas spill loads/stores. The original full DP table and
its local-memory instructions remain; `LOCAL:0` does not mean zero stack traffic.
The P source declares 40 bytes of shared distance state; 1064 bytes is the final
linked resource report, including compiler/linker overhead. Register counts are
not occupancy or performance evidence. Selected-function normalized SASS and
full executable hashes are recorded in [CHECKPOINT.json](CHECKPOINT.json).

## Pending gates

The authored checks have **not yet been executed on a GPU**:

- 352 traversal-state/work-count cases: native, counted-native, F and P; actual
  tree plus first-child-empty, whole-group-empty and alternating-empty patterns.
- 27 independent full-output/oracle/native-order runs at radii -1/0/4/256
  (native A excluded at -1 because its existing zero-grid failure is known).
- 24 sanitizer runs, six 16384-query stress runs, 36 direction-balanced timing
  processes and 36 sustained processes, followed by three NSYS node traces.

The summarizer rejects missing observations or failed gates; it cannot produce
a campaign result from this compiled-only checkpoint. A GPU availability failure
does not reject either mechanism. No timing or dynamic-count value is invented.

## Resume / reproduce

`AUTHOR_SOURCE_ROOT` contains the externally supplied original `GTS/` source.
`FIXTURES` contains the existing verified Words fixture manifest. Supply those
separately; neither source nor data is redistributed here. Use a fresh scratch
directory, an admitted idle GPU, its existing advisory lock, and the actual
toolkit executable. The current admission is GPU 0 only. Do not use Python `-O`
or C++ `-DNDEBUG` because assertion checks are part of the contract.

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
# Admit the authorized GPU first. The suite refuses an occupied GPU/held lock.
python3 "$D/suite.py" "$SCRATCH" smoke --gpu "$ADMITTED_UUID"
python3 "$D/verify_full.py" "$SCRATCH" "$ORACLE"
python3 "$D/suite.py" "$SCRATCH" gates --gpu "$ADMITTED_UUID"
python3 "$D/suite.py" "$SCRATCH" timing --gpu "$ADMITTED_UUID" >"$SCRATCH/logs/timing.txt"
python3 "$D/suite.py" "$SCRATCH" trace --gpu "$ADMITTED_UUID"
```

Retain stdout/stderr, the full scratch tree and commands. Before summary, retain
final `cuobjdump` resources and exact selected-function SASS/normalization records
under `logs/`, as in the compiled checkpoint. `summarize.py ROOT ORACLE ARCHIVE
OUTPUT_JSON` validates the complete 133-observation inventory, exact source/data
identity, actual timing order, oracle-approved ordered hashes and unchanged NSYS
downstream signatures. It reports each candidate independently; an unavailable
or failed gate is not silently waived.

The private compiled checkpoint archive SHA256 is
`177c3a46985ab192e237924041ed7a4b22a04be50b41eba2748894753739c77c`.
Runtime results must be added as a new evidence record, without rewriting this
pre-execution checkpoint as if it had passed the pending gates.
