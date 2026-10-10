# Decision: CONDITIONAL — uncovered interval, no CUDA admission

## Q1. Did partitioning tighten the bands?

Yes, for the recursive partitions, not for every partition. In the frozen joint
winner S1/P2, mean normalized width falls by 82.24% / 80.22%
relative to S1/P0 (initial / first rebuilt). Lexicographic P1 actually has wider
mean bands than P0 in all four snapshot/pivot-set combinations. Width is the
rounded-norm geometric diagnostic; filtering uses the unchanged conservative
outward endpoints. This is a descriptive finite-set result, not a significance test.

## Q2. Did tighter bands improve block filtering?

Yes, but not enough. The same S1/P2 configuration reduces mean surviving blocks
from 90.6698% / 88.8061% to **68.8995% / 67.8749%**.
The reductions are 21.7703 / 20.9312 percentage points,
not end-to-end speedups. P0 has 3,907 physical blocks; P2 has 4,096. Corresponding
surviving-object fractions are 68.8981% /
67.8736%, so this improvement is not
merely a block-count denominator effect. Query-to-pivot work remains four distances,
but P2 examines 4,096 certificates versus 3,907; preprocessing and routing are not free.
Oracle-required fractions for S1/P2 remain only 0.3654% / 0.3746%.
Even P3's slightly narrower bands do not uniformly outperform P2: average width
is an explanatory proxy, not a monotonic pruning guarantee.

## Q3. Does one P=4 configuration pass <=50% on both snapshots?

No. None of the eight shared configurations passes the joint GO (16 main
configuration-snapshot pairs, 512 query evaluations in total). Another 512 query evaluations reduce certificate dimensions
to P=2 on the same four-pivot partitions; they are a trend check, not a new search.
All 1,024 static rows have zero false prune.
The optimistic separately best certificate-aware results are
68.8995% / 66.4640%.
These are not a shared winning algorithm. They also do not trigger the explicit
>70% / other-snapshot >50% NO-GO threshold.

## Q4. Is local update retained by the selected configuration?

Local writes are retained in the two bounded simulations. Capacity-aware
initialization, authorized before measurement, uses 4,167 physical blocks of
239/240 objects, actual empty-slot fraction 6.257499%
(nominal reserve 6.25%). This is a different initialization from the static
4,096-block strict-median layout; its own before/after query survival is
68.8775% / 68.8775% for
initial→first_rebuilt and 67.8418% /
67.8418% for first_rebuilt→second_rebuilt.
Actual intervals are 10I10D and 20I20D. Changed blocks are
0.4800% / 0.7199%; existing moves,
splits and event-time global repartitions are zero. All 128 before/after query
checks have zero false prune; full final occurrence IDs, lineage, slots and bounds
match the retained next states. The locality gate passes.
Each interval has its own global initialization; sustained cross-epoch ownership
is not tested. Insertion still scans all block means, so local writes do not
prove local total CPU work, low update latency or end-to-end gain.

## Q5. Final decision

**CONDITIONAL / uncovered_interval.** The selected pair's 68.90% / 67.87% is
above the stated <=65% conditional band but below the explicit NO-GO condition.
The fallback was frozen before running: retain uncertainty, do not lower thresholds,
and do not relabel this as a positive conditional pass or a family impossibility.
No CUDA prototype, more pivots, extra partition variants, or long campaign is admitted.
Partition tightness contributes materially, but it does not close the certificate
selectivity gap. This evidence does not uniquely prove why the residual gap exists.
Keep this checkpoint; require a separately approved, genuinely different low-cost
safe-summary hypothesis and nearest-prior-art kill test before further experiments.

## GTSPP narrative and claim boundary

**Redundancy → mechanism → module → role → end-to-end gain:** scattered verification
work → certificate-space grouping → deterministic partition + unchanged safe
interval filter + bounded ownership simulator → fewer surviving blocks with local
writes, still a large oracle gap → **end-to-end gain unknown; no GPU timing**.
This does not replace the existing end-to-end baseline matrix or rescue a novelty
claim. Pivot-space mappings and triangle-inequality filtering are established
([Pivot-based Metric Indexing, PVLDB 2017](https://www.vldb.org/pvldb/vol10/p1058-gao.pdf)).
Preserve P1's wider bands, all weaker configurations, and the failed query gates.

## Validation scope

GIST N=1,000,000; D=960; FP32/L2; B1; radius bits 0x3f34a3d8;
32 original queries on each of two pinned snapshots. Baseline b89264e.
Independent stable-sort construction, direct per-block reductions and owner-based
oracle reconstruction checked all 16 partitions, 64,024 block-statistic rows,
1,024 query rows, summaries and the decision. The prior freshly verified score
cache is reused by exact hash; no new object-pivot distance computation or GPU
execution is claimed. CPU tests, numerical provenance, update full-state checks,
and raw receipt bindings are separate from CUDA sanitizer/performance gates.
