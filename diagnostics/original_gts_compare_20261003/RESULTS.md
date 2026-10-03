# Original GTS baseline-only pilot

## Measured result

The unchanged, pinned original GTS full-ID adapter passes all four real-data
baseline checks. **The optimized comparator has not been measured here.**
These are single-process diagnostic observations, not a statistical speedup
claim or a completed original-GTS/GTSPP comparison.

Each value below is milliseconds per complete **32-query Host-ready pass**,
K=8, self-inclusive in-dataset queries. Two warmup batches are excluded;
allocations, GPU search/sort, full ID/distance delivery, cleanup and synchronization
are included. Data/index/cache loading and oracle/checking are excluded.

| Dataset | N × D | B=1 ms | B=32 ms | Tie-aware / deterministic ID recall |
|---|---|---:|---:|---|
| GIST | 1M × 960 | 11380.121 | 10196.663 | 100% / 100% |
| Deep | 1M × 96 | 1443.739 | 1145.607 | 100% / 100% |

All distance-field tolerance, nonnegative and nondecreasing checks pass. The
reference is the first32 records of the existing independent full-table RN FP64
oracle. These queries have already been seen; no fresh-test or tuning claim
applies. They are not the preceding 256-query performance denominator.

## Provenance and boundaries

- Source: original `ZJU-DAILY/GTS@3bac1b725e92e98e3b69d5cb79ad9c56ccb5e639`.
  MAX_H6, fixed1GiB workspace and full-ID observation are the previously
  documented adapters; original search, pruning, distance math and sorting remain.
- Measured binary SHA256:
  `2871b26adf8b1109795291ffb0ff8645390365d89a20ec41ac3d6a239a27043c`.
- RTX PRO6000 Blackwell, idle physical GPU7/NUMA3, CUDA13.1.115,
  driver590.48.01. No GPU settings or foreign services changed. GPU0's protected
  service remained alive, and GPU7 was clear afterward.
- Source/harness/binary hashes were checked before and after; data/cache hashes
  were checked unchanged. Every process receipt is runtime-valid with no foreign
  activity. Independent oracle and signed/sorted field checks qualify outputs.
- No new sanitizer or profiler run was performed. Earlier sanitizer evidence
  applies only to its recorded synthetic reused-cache query scope; this is not
  a new full-data safety certification.
- The first pilot wrapper attempt failed before launching a GPU child because
  its subprocess argv contained an integer NUMA argument. The argument conversion
  was repaired, and the separate successful `raw_v2` run did not overwrite the
  failure log. This preparation failure is not a GTS algorithm failure.

Public text evidence is a redacted copy with explicit original/curated hashes.
Private raw evidence and output binaries remain preserved on the experiment
host. No raw SQLite/NSYS environment capture is included.

## Decision

**Implementation:** original baseline recheck passed; formal comparison pending.
**Mechanism:** no optimization mechanism tested in this pilot.
**Thesis:** no new speedup or novelty claim. The candidate source must be pinned
before a same-task, same-quality, direction-balanced comparison. Neither an
abandoned incremental kNN overlay nor a range-only prototype can silently stand
in for that candidate.
