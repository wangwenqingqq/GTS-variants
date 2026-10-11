# NO_GO_GRANULARITY: stop finer whole-tile GLOBAL4 pruning

**Making the maximum leaf size eight times smaller barely changes verified
object work, while multiplying endpoint/filter state by eight.** On the same
GIST N1M/D960 FP32 L2 B1 workload,256 ->32 reduces mean surviving objects from
**68.8981% ->66.7223%** initially and **67.8736% ->65.5008%** after rebuild.
The decreases are **2.1758 /2.3727 percentage points**, not20 or15 points.
Zero false prune and all320 independently reconstructed count rows validate
the structural observation, not GPU latency or end-to-end gain.

## Q1. Does smaller tile size reduce surviving objects?

Yes, monotonically and on all64 queries for128/64/32 versus256. This positive
signal is preserved: a smaller child cannot have a wider conservative bound
than its containing parent. However, the aggregate reduction is too small
for admission. From512 to32 the gains are only3.2216 /3.5567 points. The
256 anchor exactly reproduces previous permutations, starts and full counts.
Earlier68.8995% /67.8749% numbers were **tile fractions**; this experiment's
object fractions differ slightly because leaves hold244/245 objects.

## Q2. Does any granularity reach <=50% surviving objects?

No. Both snapshots remain above65% even at32; no identical fine target meets
GO or the stated positive conditional band. Both snapshots independently
remain above60% at32 and both gain less than10 points. The frozen NO-GO
condition is decisive; this is not an uncovered gray interval.

## Q3. Is there a reasonable metadata/filter sweet spot?

No measured timing sweet spot is established. Tile counts are2048,4096,8192,
16384,32768; endpoint state/checks scale0.5x,1x,2x,4x,8x versus256.
Endpoint metadata increases from262144 bytes at256 to2097152 bytes at32.
The three predeclared sensitivity coefficients consistently prefer256 for
lambda=.01 and512 for lambda=.05/.10 on both snapshots. None prefers fine
128/64/32. These are uncalibrated sensitivity proxies, not GPU measurements.

## Q4. Are both snapshots consistent?

Yes, in the direction and limited magnitude of survivor reduction. At32, p90
object survival remains **85.9019% /86.7952%**. The oracle requires only
**0.1703% /0.1989% of tiles**, containing1703.8125 /1989.6250 objects on
average, versus667223.03125 /655008.28125 surviving objects. The reference
mean true-hit counts205.9375 /388.40625 are unchanged across capacities.
Most surviving fine tiles are still actually empty. Oracle-required object
counts include neighbors sharing a required tile and are not true-hit counts.

## Q5. Final decision and next boundary

**NO_GO_GRANULARITY; update_admitted=false.** Do not run10I10D/20I20D, tile16/8,
extra pivots/summaries, hierarchy, CUDA or long matrices under this campaign.
Coarse ownership + fine verification is not prototyped, qualified or admitted
by these results. Previous formal R/T/P and external end-to-end results remain
unchanged; the private manuscript is not modified or uploaded.

This evidence argues against **coarse256 work units being the primary cause
of poor selectivity in this fixed S1/P2 GLOBAL4 configuration**: shrinking to
30/31-object leaves fails to remove most unnecessary verification. It does
not prove a universal limit on all trees, all partitions, pivots, geometry or
exact pruning. The measured negative boundary is the tested family and scale.
Reassess whether tree-style exact pruning should carry the main mechanism
claim; do not rescue it by unregistered smaller-tile or summary tuning. A new
research direction needs a distinct falsifiable mechanism and Gate0, not more
packaging of these classic filters. No new experiment is launched by this note.

| Negative-evidence field | Exact scope |
| --- | --- |
| Target | Cheap whole-work-unit rejection that reduces exact verification objects |
| Workload | GIST N1M/D960 FP32 L2 B1, original32 range queries each on initial/first_rebuilt |
| Keeper | Qualified GLOBAL4/S1/P2 maximum256 leaves, actual244/245 members |
| Rejected mechanism | Only changing widest-range median recursion stop to128/64/32 |
| Added costs | Up to8x tile checks/endpoints;10 offline independent constructions; no paid update study after stop |
| Measured effect |32 still66.7223% /65.5008% object survival; only2.1758 /2.3727 points below256 |
| Diagnosis | In this layout/summary, finer whole tiles expose too little additional safe rejection |
| Reopen condition | Separately approved, non-subsumed work-unit/algorithm mechanism and explicit same-contract cost/quality evidence; not tile16/8, more pivots or summary variants |

## GTSPP thesis boundary

**Redundancy -> mechanism -> module -> effect -> end-to-end benefit:** empty
exact-verification work -> smaller whole-tile interval rejection -> frozen
GLOBAL4/recursive partition/filter modules -> safe but insufficient survivor
reduction, sharply increased metadata -> **no new end-to-end benefit measured**.
No CPU waiting, coalescing or update amplification is inferred from these counts.

Vector/object filtering versus block access is already examined in
[Weber/Schek/Blott, VLDB1998](https://www.vldb.org/conf/1998/p194.pdf).
Leaf-size changes/filter-refine tradeoffs are not novel. The hypothetical
GPU ownership/execution decoupling needs a separate prior-art kill test and
actual dynamic/system evidence before a contribution claim.
