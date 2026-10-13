# M3 cheap kill — CPU-only initial-snapshot k8 replay

Queries are the **first32 kNN events' source rows from the original Gate3 A trace**,
selected by trace order before outcomes. Replay all1M initial rows, not the later
mutated snapshots. Keep self matches and all duplicate occurrences, k8, original
coordinate order, ordered FP64 unexpanded squared L2. Do not generalize to all128
dynamic queries, other k values or later update snapshots.

One pass records complete ordered scores plus first strict crossing for:
1. Oracle final eighth score: optimistic coordinate-only lower bound; obtaining
   this threshold is not a realizable free service operation.
2. A valid fixed seed threshold from the first256 raw rows: realizable but loose,
   with the complete256*960*4 seed reads charged before scanning other rows.
   No tuning or alternative seed. This bounds the cost of a fixed-threshold
   implementation; adaptive tightening is not measured.

Every full score must match the preserved, hash-bound Gate3 oracle bit-for-bit.
Every rejection crosses strictly with predecessor<=threshold. Retained complete
scores must reproduce exact k8 (distance, then occurrence ID for CPU ties);
all cutoff-equal occurrences remain eligible. Record required-dimension histograms,
first-crossing mean/p10/p50/p90, retained counts at128/256/512/960, and ideal
4-byte-coordinate payload. Also round consumption up to the frozen four stages;
a coordinate-at-a-time ideal must not masquerade as the existing GPU schedule.

Primary kill: oracle ideal saving<40% -> KILL_M3. A pass means headroom only;
prior-art subsumption independently kills thesis admission. Seed, top-k, query
loads, state/compaction, Host waiting and output costs are not a byte-to-latency
conversion. No GPU program, update replay or performance claim in this test.
