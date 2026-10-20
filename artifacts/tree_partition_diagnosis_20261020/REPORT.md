# Tree construction matters,but one-ball certificates remain loose

## Conclusion and strongest caveat

**On this fixed GIST1M/960D snapshot,query-blind construction changes pruning
substantially at the same tree shape and ball-certificate budget.** Random,KD
and sampled PCA-inspired trees prune about0.026%,3.96% and12.12% of points on
average. This is evidence against treating ambient dimension alone as a
complete explanation of weak tree pruning. It is not evidence that a tree
beats a strong GPU exact-search implementation.

The strongest caveat is query heterogeneity:the PCA-inspired mean12.12%
pruning has median3.60%. Of32 queries,27 have only the self-match,three
have2 hits,and the remaining two have1114 and5443 hits. This is not a broad
radius/selectivity study. Its mean coordinate-read proxy is11.37% below a
single-query full scan,but7/32 queries do not beat even that restricted proxy.
No physical traffic,search latency,batch reuse,updates or end-to-end service
cost was measured. Frozen128-query Gate1 inputs remain untouched as queries.

## Frozen experiment

- Experiment:`GTSPP_20261020_TREE_PARTITION_CERTIFICATE_DIAGNOSIS`.
- Data:GIST,N=1,000,000,D=960,FP32;3.84GB coordinate payload.
- Original32 development queries,self-matches included,radius
  `FP32 bits0x3f34a3d8` (approximately0.7056250572). All32 are retained.
- All trees:depth12,8191 nodes,4096 leaves of244/245 points,capacity256.
- Same full-coordinate mean-nearest real-member center rule and conservative
  ball test at every node;this is not a medoid optimizer.
- Random seed,three splitter definitions and all costs were frozen before
  population execution in CONTRACT.json. No query outcome enters construction.
- Sampled PCA uses up to512 fixed samples per internal node and8 fixed power iterations;
  it is not exact PCA and is not claimed as a new algorithm.

## Actual hierarchical traversal

At each query,visit a node once and prune its descendants only when its ball
proves exclusion. Charge every visited center and every point in retained
leaves;do not sum ancestor/descendant pruning multiple times.

| Query-blind builder | Mean points pruned | Median points pruned | Mean coordinate proxy/query | Mean proxy saving vs scan | Queries below scan |
|---|---:|---:|---:|---:|---:|
| Random balanced | 0.025944% | 0.000000% | 3.870460800 GB | -0.793149% | 0/32 |
| KD maximum-span median | 3.955047% | 0.244000% | 3.719076120 GB | 3.149156% | 9/32 |
| Sampled PCA-inspired median | 12.121034% | 3.600300% | 3.403454040 GB | 11.368473% | 25/32 |

GB is decimal10^9 bytes. Full-scan coordinate proxy=3.840003840GB/query.
The model is`(visited_nodes+retained_leaf_points)*960*4+960*4`.
It includes query input and full-coordinate center evaluation,without free
reuse. Node metadata reads are separate:mean262110,257884 and240816B/query
for random,KD and PCA-inspired,respectively. All trees store262112 node-metadata
bytes plus an8MB ID permutation;no persistent center-coordinate copy.
ID-map reads,output,state/cache/line traffic,execution control and CPU/GPU
synchronization are unmeasured. Therefore this is neither a complete physical
source-cost model nor a latency/speedup estimate. The full scan here is a
single-query coordinate denominator,not a measured batched GPU competitor.

The maximum individual pruning fractions are0.4883%,51.0805% and90.8650%;
30,7 and0 queries,respectively,receive no pruning. KD leaves fewer points than
random on25/32 queries (7 ties);PCA-inspired does so on32/32. These are descriptive
paired counts on the original development set,not held-out generalization or
confidence intervals.

## Partition opportunity versus certificate capture

The leaf oracle rejects a leaf iff **all** its authoritative point scores exceed
the squared radius. This needs future/full information and is not a realizable
index. It diagnoses whether empty-of-results leaves exist. Flat-leaf ball tests
are evaluated separately from the actual hierarchical traversal above.

| Builder | Mean leaf-oracle-prunable point mass | Mean flat-leaf ball-prunable point mass | Mean per-query flat-leaf capture | Mean leaf covering radius |
|---|---:|---:|---:|---:|
| Random balanced | 96.953641% | 0.024419% | 0.024425% | 3.622153 |
| KD maximum-span median | 99.406637% | 3.878769% | 3.879787% | 2.715505 |
| Sampled PCA-inspired median | 99.765825% | 11.930288% | 11.934408% | 1.943203 |

Each depth covers exactly1M points;all fractions are point-mass weighted,not
merely node fractions. Capture above is the arithmetic mean of32 per-query
ratios;ratio-of-total hierarchical capture is also retained in SUMMARY.json.
The PCA-inspired tree has99.765825% leaf-oracle-prunable mass,yet actual traversal
prunes only12.121034%. Better construction shrinks covering radii and improves
pruning,but the tested one-ball lower bound captures only a small part of the
available exclusion opportunity. This supports **certificate slack within this
family**,not an information lower bound or a failure of all high-dimensional
trees. Oracle opportunity itself also improves with the tested construction.

All96 per-method/query records and1248 per-query/depth records are retained,
including distance contrast and all weak/no-pruning cases. Single-run CPU
construction times are retained only as resource observations;the run order
was fixed and no paired construction-timing study was performed.

## Correctness and provenance

- Three serial population processes,each with at most4 arithmetic threads,
  BLAS1,nice10;zero GPU starts,zero held-out-query evaluations.
- Every query/node ball rejection was compared with the full authoritative
  membership oracle;zero falsely rejected hit-containing nodes. Every true-hit
  ID remains in retained leaves. No deployed query-engine distance fields were
  produced or timed.
- Before verification,the controller sealed the exact59-file population census,
  source/library/qualification identities,commands,starts,exits and completion
  hashes. This seal remains unchanged.
- Fresh O0 verification reconstructed all8191 centers/covers and4095 splits per
  tree,with reverse pair orientation for covers,and bitwise checked262112 query
  center scores per tree. An independent owner-array oracle/reach-set evaluator
  reproduced every query and level scalar. The numerical interval helper is
  shared with the preceding implementation,not independently rederived.
- O3 and O0 qualification each passed9 small tree fixtures,FP32 boundary cases,
  independent scalar arithmetic and3 altered-scalar rejection tests. The tiny
  960D line permits87.5% point pruning with KD/PCA-inspired trees;this is a
  synthetic low-intrinsic control,not a second real dataset or dimension study.
- SOURCE_FREEZE binds the12 registered experiment files. Scalar aggregation,
  the portable checker and final prose are postrun delivery work,not changes to
  the tested algorithm. The archived execution documentation predates final
  portable-gate instructions and wording-only clarification of sample capacity
  and center-selection-rule ownership.
- Raw source snapshots,all tree arrays,logs and receipts remain in the persistent
  private archive identified by evidence/CUSTODY.json. Full inputs are external
  and pinned by exact hashes;neither database nor private operational paths are
  uploaded. Local and remote archive members are checked independently.

## Decision and next action

**DESCRIPTIVE_ONLY_NO_GPU_OR_INDEX_ADMISSION.** The experiment resolves that
construction matters in this controlled family;it does not establish a new
index,universal best builder,dimension-induced impossibility or end-to-end win.
Classical construction/ball mechanisms are not novelty-admitted.

The prior S1/P2 signature-center single-ball NO-GO remains intact. Because that
older experiment also used a different center rule,a cross-study difference
cannot be attributed solely to construction.

Do not tune more trees on these32 queries or touch the frozen Gate1 set to
rescue the result. A follow-up would require a separately frozen question:
for example,whether a different safe certificate family captures this fixed
partition's residual gap at lower complete cost,or whether an independent
intrinsic-dimension-controlled study reproduces the structural effect. Establish
nearest-prior-art separation first. No such follow-up is started here.

## Replay

From the repository root,run the data-free gate:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 artifacts/tree_partition_diagnosis_20261020/check_public.py
```

Owners of the preserved private archive can append`--archive /private/RAW_R1.tgz`
to check every member against the public manifest. For full fresh semantic
reproduction,use REPRODUCE.md with the exact original input hashes. A portable
hash/scalar check is not a replacement for that full geometry replay.
`test_public.py` also rejected six altered delivery copies,including changed
source,query/aggregate scalars,verification status,priority and extra files.
Five cases refresh publish hashes before requiring semantic/anchor rejection.

## Established prior art

[Spatial-tree analysis,UAI2009](https://arxiv.org/pdf/1205.2609) studies partition
adaptation to intrinsic structure;[M-tree,VLDB1997](https://www.vldb.org/conf/1997/P426.PDF)
establishes classical metric-ball indexing. These are mechanism provenance,
not support for a universal claim about this dataset or GPU service performance.
