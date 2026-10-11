# NO_GO_LOCAL_BALL: stop the fixed C0 single-ball route

**The tested local ball is weaker, not stronger, than GLOBAL4.** On GIST
N=1,000,000 / D=960 / FP32 L2, the same 4096 S1/P2 blocks retain
**92.2501% / 93.4250%** of blocks, versus **68.8995% / 67.8749%** for GLOBAL4.
All 64 original queries have zero false prune; independent O0/reversed-pair
reconstruction confirms the complete result. No GPU or end-to-end timing was run.

## Q1. Is LOCAL_BALL systematically stronger than GLOBAL4?

No. LOCAL_BALL is worse on **63 of 64** queries, better on one initial query,
and equal on none. The comparison fixes membership, queries, radius, safe
numerics and block count, so this is not a different-occupancy comparison.
The center is a member nearest to the 4D signature mean; this is not an
optimized original-metric medoid and does not represent every possible center.

## Q2. Do both snapshots reach <=50% mean surviving blocks?

No. The means are 92.2501% / 93.4250%, with p90 **99.8486% / 99.6973%**.
Both means fail 50%, and both p90 values fail 70%. STRONG_GO inherits these
joint correctness/mean/tail requirements; it cannot bypass them.

## Q3. Is the improvement large rather than a few percentage points?

There is no aggregate improvement. GLOBAL4 minus LOCAL_BALL is
**-23.3505 / -25.5501 percentage points**. On both individual snapshots,
local mean exceeds 65% and improvement is below 10 points; the frozen
same-snapshot NO-GO condition therefore triggers without any gray-zone rule.
The ball also pays 4096 query-center distances instead of four query-pivot
distances and 15,728,640 bytes of logical center-coordinate payload/query.
[Full cost accounting](query/COST_PROXY.md) includes surviving-object work.

## Q4. Is the oracle gap still large?

Yes. ORACLE requires only **0.3654% / 0.3746%** of these same blocks.
LOCAL_BALL keeps an average **3763.59375 / 3811.34375** unnecessary blocks/query,
out of 4096. The evidence supports insufficient selectivity of this fixed
single-ball enclosure; it does not identify high dimensionality as a proven
universal cause or rule out all possible local summaries.

## Q5. Decision and next boundary

**NO_GO_LOCAL_BALL.** Preserve this negative result. Do not tune the medoid,
add multiple centers/balls, use query-adaptive or oracle-selected centers,
repartition, rerun updates, add hierarchy, or launch CUDA under this campaign.
The separately initialized historical update simulation is not evidence for
center-maintenance costs and cannot rescue this query failure.

| Negative-evidence field | Retained scope |
|---|---|
| Target | Reduce redundant exact block verification while keeping complete range semantics |
| Workload | Two GIST N1M/D960 snapshots, original 32 queries each, fixed FP32 radius |
| Keeper | GLOBAL4 on identical S1/P2 membership, retained and independently reconstructed |
| Rejected mechanism | One C0 signature-nearest-member center plus conservative covering radius/block |
| Added costs | N center/member construction distances/snapshot; 4096 query-center distances, radii and center payload/query |
| Measured effect | More surviving blocks on 63/64 queries; mean survival rises 23.3505/25.5501 points |
| Diagnosis | This particular ball envelope does not sufficiently exclude empty blocks |
| Reopen condition | A genuinely different mechanism with its own prior-art kill test, fixed quality/cost contract and approval; not more tuning of this rejected family |

## Main-line interpretation

**Redundancy -> mechanism -> module -> effect -> end-to-end benefit:** empty-block
verification redundancy -> triangle-inequality local-ball exclusion -> fixed
C0/radius/filter modules -> safe but weaker exclusion -> **no end-to-end benefit
established and no prototype admission**. The CPU diagnostic closes an idea,
not the whole GTSPP project. Old formal end-to-end results are unchanged.

Metric balls, covering radii and triangle pruning are established, including
[M-tree (VLDB 1997)](https://www.vldb.org/conf/1997/P426.PDF). No novelty claim
is made for them. Additional engineering cannot rescue a subsumed thesis;
a future direction needs a distinct defensible mechanism as well as matched
end-to-end evidence.
