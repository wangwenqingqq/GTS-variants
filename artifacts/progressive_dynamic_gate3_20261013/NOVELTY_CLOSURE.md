# Novelty closure: not admitted

**Decision: ENGINEERING_ONLY; no current paper-thesis admission.** A same-contract internal GPU integration result is not a same-contract external advantage, and the execution gate does not waive Gate0.

The nearest precedents already cover much of the proposed property. [BOND, SIGMOD2002](https://www.cs.uoi.gr/~nikos/sigmod02.pdf), section1, uses incremental partial-distance pruning with little auxiliary storage; section6.2 discusses appends/updates on its vertically decomposed representation and deletion bitmaps with periodic reorganization. [PDX, SIGMOD2025](https://arxiv.org/html/2503.04422v1), “Inserts and Updates” and PDX-BOND, explicitly discusses update-in-place/PAX strategies and preprocessing-free exact pruning suitable for frequent ingestion. These are not same-layout GPU measurements, but “partial pruning plus cheap updates” is not a new principle.

## What this campaign can establish

| Proposed property | Exact scope of new evidence | Novelty consequence |
| --- | --- | --- |
| No rebuild | No rebuild in a preallocated 1M/D960 store through A's 40 inserts/40 deletes | Bounded compatibility, not a novel flat-store property |
| Raw ownership plus progressive range | One device raw buffer, unchanged append/swap-delete/native kNN, query-only state | Integration realization; no distinct non-incremental algorithm demonstrated |
| Bandwidth-bound exact range | Gate2 static traffic evidence; Gate3 remeasures complete range ACKs | No new dynamic DRAM measurement; do not generalize static counters |
| Joint query/update cost | A's entire fixed 336-event stream plus the documented service-release segment | Internal D0/D1 evidence; no PDX/BOND/VA-file same-contract external advantage |
| No heavy secondary representation | No D1-specific O(ND) device representation; additional O(N) query workspace is charged in memory | No claim of index-free total memory or absence of native library reservations |

Unmeasured: update-heavy B, capacity growth/rollover, long-lived churn, 100k events, 10k-query populations, 1B scale and external dynamic competitors. kNN remains native Faiss; this is not progressive kNN. Updates transfer one D-dimensional row and preserve native norms: do not turn fixed-D measurements into an O(1) complexity proof.

Stop the current paper-thesis promotion, retain the narrow engineering evidence. Reopening requires a genuinely distinct mechanism and decisive reproducible same-contract external evidence, not another stage choice, query mix, broader package or small performance rescue. No manuscript, Overleaf project, abandoned incremental baseline or production dispatch was changed.
