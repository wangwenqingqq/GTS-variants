# Result fusion versus dataset size

Registered 2026-09-24 before this campaign's CUDA compilation or GPU runs.
Question: how does the previously measured Words N=2000 result-fusion speedup
change with N? No layout or traversal fusion is added.

## Fixed comparison

- Words byte edit distance, N = 2000, 4000, 8000, 16000, 32000, 64000,
  128000, 256000. Nested real-data subsets; N=2000 exactly reuses the old fixture.
  Keep the same 64 query words from that fixture at every N, remapping their IDs.
  Existing 2000 evenly spaced records plus seed-20260924 sampled additions;
  sort each subset by original source index. Preserve full source/fixture hashes.
- Radius 4, inclusive; immutable query-only index, batch one. Exact complete
  count, stable IDs and byte-edit distances returned to CPU.
- C: unfused result pipeline + CUDA Graph. E: result fusion + CUDA Graph.
  Same binary, tree, common traversal/leaf stages, fixed capacity and transfer
  lengths at a given N. Retain now-unused buffers in E. Native A is correctness
  reference only; no speedup relative to untouched GTS is claimed.
- Generalize node/slot capacity and safe maximum tree height in both arms.
  Tree order 10 and leaf capacity 20 unchanged. Choose height by repeatedly
  applying worst-child size s - 9*(s//10) until <=20. Validate actual leaves,
  complete coverage and ID permutation after construction. Original source intact.
- Preserve the one-CTA, 512-thread, sequential-tile selector. Only replace its
  hard-coded 111-node guard with a runtime capacity parameter; no new large-N
  selector, retuning, arithmetic change or mechanism switch during this experiment.
  The old 2000 executable is retained as an output and same-session timing anchor.

## Validation before timing

Independent C++ integer CPU edit-distance matrix; cross-check a deterministic
sample with the existing Python full-table oracle. For each N: full native A/C/E
outputs at r4 (64 queries), r0/r256 (8 fixed queries); C/E negative radius -1.
Membership/distance checks are independent, order checked against A (C for -1).
Then C/E memcheck and synccheck at every N (8 queries); E initcheck and racecheck
at the largest N for each resulting height (2000,16000,128000,256000).
Selector standalone stress covers tile boundaries, zero counts, poisoned inactive
capacity, nonidentity maps and maximum runtime capacity; all four sanitizers.
Each C/E arm runs 256 changing queries with 64 warmups before primary timing.
Stop and retain failures; do not silently discard, repair or replace a measurement.

## Timing and reporting

Six fresh paired rounds, CE/EC alternating. All N traverse increasing order in
even rounds and decreasing order in odd rounds. Warmup 64 each process. Queries
per primary process: 4096 for N<=16000; 512 for N<=64000; 128 for N=128000;
64 for N=256000. Two sustained CE/EC pairs per N use twice that query count.
Primary output: median process-mean hot completed-query latency and C/E ratio;
exact 6^6 bootstrap of round-paired log ratios, interval and wins/6; no pooling
across N or old campaigns. Record hit/candidate counts, tree/slot capacity, setup,
capture, first query and process order. Include setup amortization separately.
Historical 1.8x is a reference, not an input to the new ratios.

Timer includes input, device work, complete output copies and host readiness;
excludes loading, construction, setup/capture, warmup and output hashing.
NSYS C/E per N uses 8 queries, 8 warmups and 1 repeat (17 executions); runtime
verify common stages and actual launch counts, without assuming all N retain the
small-tree 24/17 counts. Profiler time is diagnostic only.

Use one freshly admitted idle RTX PRO 6000, existing advisory lock and UUID;
CUDA 13.1.115 / sm_120. No setting changes; CPU shared/unpinned, clocks uncontrolled.
Monitor before/during/after; stop only owned work on foreign GPU activity.
All raw data, generated external source, binary and machine identities stay local.
Produce a standalone scale plot and complete table, including losses or gates
that fail. No production promotion, whole-program, other-dataset or million-N claim.
