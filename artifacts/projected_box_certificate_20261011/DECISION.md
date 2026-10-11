# NO_GO_PROJECTED_BOX: stop the tested PCA-4 box route

**The projected box is better than the rejected single ball, but worse than
GLOBAL4 on aggregate.** With unchanged S1/P2 membership, PROJECTED_BOX retains
**74.4102% / 75.1266%** of blocks versus GLOBAL4 **68.8995% / 67.8749%**.
All 64 queries have zero false prune, and all object/query projections,
8192 boxes and complete rows pass independent O0 scalar reconstruction.
This is a CPU structural diagnostic; no GPU/query/end-to-end time was measured.

## Q1. Is PROJECTED_BOX systematically better than GLOBAL4?

No. It is better/worse/equal on **6/26/0** initial queries and **4/28/0** rebuilt
queries: **10 improve, 54 regress**, not every query regresses. The shared
4096-block denominator and unchanged 244/245 membership eliminate occupancy
as a confound. Direction selection is one full-initial-snapshot PCA4 fit,
not per-block PCA or optimization of range separation.

## Q2. Do both snapshots reach <=50% surviving blocks?

No. Both means exceed 74%. p90 is **93.0078% / 92.6782%**, also failing 70%.
STRONG_GO inherits correctness, mean, tail and gain conditions; it cannot
bypass ordinary GO because of one favorable statistic.

## Q3. Does each snapshot improve GLOBAL4 by >=15 points?

No. GLOBAL4 minus PROJECTED_BOX is **-5.5107 / -7.2517 percentage points**.
Each snapshot independently satisfies the frozen NO-GO condition: box mean
>65% and improvement <10 points. No unassigned gray interval is involved.
The safe core pays four full-D dots plus one numeric max-absolute reduction,
262,144 endpoint bytes and 30,720 direction-coordinate bytes. These are cost
proxies, not equivalent instructions or latency to four pivot distances.
See [complete cost accounting](query/COST_PROXY.md).

## Q4. Is the oracle gap still large?

Yes. ORACLE requires only **0.3654% / 0.3746%** of blocks. PROJECTED_BOX retains
an average **3032.87500 / 3061.84375** unnecessary blocks per query.
The top-four initial global PCA coordinates do not sufficiently exclude empty
blocks under this fixed partition. This **does not prove the residual gap is
or is not mainly caused by anisotropy**: PCA maximizes global variance, and
block geometry or separation may lie in different/local/omitted directions.

## Q5. Decision and stop boundary

**NO_GO_PROJECTED_BOX; K8_admissible=false.** No random directions, multiple
PCA fits, multi-box, adaptive directions, repartition, updates, hierarchy,
CUDA or K8 follow-up under this campaign. Do not rescue a failed gate by
changing the direction family. Reassess the underlying low-cost-summary
hypothesis before registering any genuinely different work-unit mechanism.
No new experiment is automatically authorized by that recommendation.

| Negative-evidence field | Scope |
|---|---|
| Target | Safe whole-block rejection to reduce unnecessary exact verification |
| Workload | GIST N1M/D960 FP32/L2/B1, two snapshots, original 32 range queries each |
| Keeper | GLOBAL4 on the same S1/P2 blocks and query/radius identities |
| Rejected mechanism | One initial-fitted top-four PCA map plus conservative projected bounding boxes |
| Added costs | Full-data PCA mean/covariance/eigensolve/qualification; object projections/box construction; four query dots plus one max reduction and summary state |
| Measured effect | Survival rises 5.5107 / 7.2517 points versus GLOBAL4; 54/64 queries regress |
| Diagnosis | This low-dimensional global variance map does not give strong enough whole-block exclusion |
| Reopen condition | A distinct, prior-art-cleared mechanism and separately approved cost/quality contract; not direction tuning or K8 after this NO-GO |

PCA construction plus qualification costs **9.543945293 seconds wall /
31.575067 CPU seconds**; explicit covariance-chunk arrays peak at **77,667,840
bytes**, while process peak RSS is **3,959,263,232 bytes**, including mapped
input/runtime. Those are different measures. Prior input hashing has already
read the data; this is not cold-start full index-build latency. PCA time includes
two eigh/sign/Gram qualifications, not merely one eigensolve. No new dynamic
maintenance cost/locality evidence is claimed.

## Thesis and novelty boundary

**Redundancy -> mechanism -> module -> effect -> end-to-end benefit:** empty
verification blocks -> orthogonal-subspace box exclusion -> frozen PCA/projection/
box/filter modules -> safe but insufficient selectivity -> **no new end-to-end
benefit established and no GPU admission**. This closes one mechanism test,
not all tree indexes or the whole GTSPP project. Previous formal timings stay intact.

PCA bounding boxes and geometric approximation filters are established; see
[PCA bounding-box analysis](https://page.mi.fu-berlin.de/~rote/Papers/pdf/Bounds%2Bon%2Bthe%2Bquality%2Bof%2Bthe%2BPCA%2Bbounding%2Bboxes.pdf)
and [VA-file (VLDB 1998)](https://www.vldb.org/conf/1998/p194.pdf). No novelty
claim is made for PCA/linear projection/box lower bounds. A future co-design
requires a distinct defensible mechanism and matched end-to-end evidence,
not broader packaging of classic filters.
