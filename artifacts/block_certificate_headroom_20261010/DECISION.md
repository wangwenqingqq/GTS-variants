# Decision: CONDITIONAL — no GPU prototype

## Q1. Current problem

Physical scatter consumes much of the current tree's logical pruning. With exact
candidate identities unchanged, L0 mean block256 reach is 99.4633% / 99.5585%;
L1/L3 reduce it to 76.5477% / 63.8589% (initial / first rebuilt).
This is an offline permutation/count result, not executed GPU layout or speed.
The initial snapshot still exceeds the plan's 70% layout target.

## Q2. Headroom

Oracle block256 reach is 2.7995% / 4.2496% in L0, and 0.3311% / 0.3183% in L3.
These are means of the 32 original queries per snapshot; oracle is never used in
pivot selection, certificates, layouts, or insertion placement.
There is strong ideal block headroom, but no cheap realization is established.

## Q3. Cheap safe certificate

**No.** Even the separately best P<=4 configuration retains 87.7384% /
71.6047% blocks, not <=50%. At P=8 the separately best results are
78.3442% / 69.2227%, with different winning strategies.
No identical configuration passes both snapshots' GO gates. Oracle gaps remain
large; non-tiny queries (>=1% required blocks) are explicitly identified in JSON,
and small-oracle queries are not silently treated as ratio passes.
All 9,216 static configuration/query/block-size rows have zero false prune.
The closest cheap design is still substantially weaker than the current tree's
logical selection after contiguity, especially on initial.

## Q4. Update locality

**Local writes are possible in this model, not proved fast or sustained.**
All 288 layout/strategy/P/slack simulations are below 1.28% distinct changed
blocks. With 6.25% or 12.5% initial slack, no existing objects move and no blocks
split. Without slack, up to 1,288 / 2,579 existing occurrences move. Global
repartition is zero by construction. All 9,216 post-update query checks have
zero false prune, and final exact occurrence/lineage deltas match the retained
next snapshots. The first interval is actual 10I10D; the second is actual
20I20D, although its net entering/removing base instances are 10/10.
Each interval initializes its own organization; this does not establish
maintenance across consecutive epochs. Best-match insertion scans all block
summaries. Copy-model bytes exclude allocation, scheduling and measured I/O.

## Q5. Decision and next falsifiable action

**CONDITIONAL; do not enter GPU Flat Block Index v0.**
The cheap-query <=50% gate failed. Neither snapshot's best P8 result is >80%,
so the predeclared explicit global-design NO-GO is not triggered. Initial lies
in the otherwise unspecified 70–80% gray zone; CONDITIONAL means *not admitted*,
not a relaxed positive result. The original automatic D gate was false and its
receipt is retained. The user subsequently authorized D only as an additional
ownership diagnostic, under a separate pre-D contract.

Do not increase P beyond 8 or promote local-write success into a system claim.
The next bounded proposal should attack partition tightness or a genuinely
stronger <=4-cost summary, independently falsifiable against matched scan.
Before new work, test novelty against prior metric-indexing systems. Global
pivot triangle-inequality filtering is established prior art, not our invention
([Pivot-based Metric Indexing, PVLDB 2017](https://www.vldb.org/pvldb/vol10/p1058-gao.pdf)).
This round tests a GPU-block ownership realization, and **does not claim its
novelty or end-to-end benefit**.

## Narrative and evidence boundary

Redundancy: logical pruning still touches most complete verification blocks.
Mechanism tested: stable blocks plus globally shared conservative distance bands.
Modules: partition, certificate filter and local ownership simulator only.
Role: scatter is reduced and writes are bounded, but cheap block filtering is
not selective enough. **End-to-end gain: unknown, no GPU implementation/timing.**
Preserve this negative cheap-query result, all weak strategies and sensitivity
rows. Reopen only with a different partition/summary mechanism that clears the
same <=4-pivot/equivalent-cost query gate, not by adding more pivots.

## Validation and provenance

- Baseline: db89d2f1aa66b934f3b99b5730efafa87cee5a71.
- GIST N=1,000,000, D=960 FP32, L2, B1; original radius bits 0x3f34a3d8.
- 2 frozen snapshots ×48 main configurations ×32 original queries; block32/512
  are sensitivities using the same selected pivots, not additional searches.
- Fresh CPU library recomputed all 48,000,000 object-pivot distances bitwise;
  every layout/oracle/certificate row and summary reconstructed.
- Original and fresh four-test numerical suites passed; delivered suite adds
  joint-admission, proof-tamper and executed-copy recipe regressions. See closure and source hashes.
- Immutable execution copies remain outside Git. Delivered drivers were hardened
  after execution; original source identities and deferred-D receipt are not
  rewritten. Closure binds actual original inputs despite entry-gate omissions.
- No GPU process launched, no external matrix rerun, no real traffic/latency
  measurement, no sustained-workload validation. CPU-only four-thread helper,
  low-priority orchestration; no foreign process modified.
