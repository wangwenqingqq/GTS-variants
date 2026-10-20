# Tree partition versus certificate slack: CPU diagnosis

This is a bounded **development-only diagnosis**, not a new tree algorithm,
Gate1 held-out evaluation, GPU optimization or end-to-end benchmark.

Completed results and limits are in [REPORT.md](REPORT.md);all query/level
records and the deterministic aggregate are in `results/`. The portable
`check_public.py` gate needs only Python's standard library,not the data or GPU.

| Experiment | Hypothesis | Contract | Controls | Invariants | Evidence | Decision |
|---|---|---|---|---|---|---|
| GTSPP_20261020_TREE_PARTITION_CERTIFICATE_DIAGNOSIS | Partitioning changes oracle opportunity and/or safe-bound capture | CONTRACT.json | Random balanced,KD maximum-span median,sampled fixed-iteration PCA-inspired median | Same GIST1M,32 old queries,radius,binary shape,center-selection rule and certificate budget | Private raw campaign;public identities and scalar tables | Descriptive only;no automatic method/index/GPU admission |

## What is isolated

- GIST **N=1,000,000,D=960,FP32**,3.84 GB coordinate payload;initial snapshot only.
- Original32 database-row development queries;self-matches retained;one radius.
- Each tree:depth12,8191 nodes,4096 leaves of244/245 points;capacity256.
- Every node uses the real member nearest its full-coordinate empirical mean,
  then the same conservative covering-ball test. This is not a true medoid.
- Each node has16 certificate bytes plus16 common start/count bytes;the8 MB
  permutation ID array is separate. No persistent center-coordinate copy.
- No query IDs,radii,reference scores or query rejection outcomes enter build().
  The shared database includes all rows as ordinary data,not as held-out queries.
- All128 frozen Gate1 queries remain untouched as query inputs;no query-specific
  feature,score,rejection depth or plan is generated for them.

The sampled PCA-inspired splitter uses up to512 samples per internal node and8
fixed power iterations about the complete-node mean. It is not an exact PCA
solver or a parameter sweep.
Actual BLAS/OpenMP object identities and thread settings are retained because
floating-point projection ordering can affect partition boundaries.

## Three different quantities

1. **Oracle opportunity:**a node can be excluded if every authoritative
   point score in it exceeds the squared radius. The oracle reads future/full
   information and is not a deployable competitor.
2. **Certificate capture:**how much of that opportunity the one safe ball
   proves. Node counts and point-mass-weighted fractions are reported separately.
3. **Traversal/cost:**root-first pruning without ancestor/descendant double
   counting;charge every visited center distance and surviving leaf point.

Coordinate reads and node metadata reads are a declared source model,not actual
DRAM traffic. Cache,line waste,ID-map accesses,output,state traffic and scheduler
latency remain unmeasured. CPU construction wall time is a single-run resource
diagnostic,not a paired performance comparison or GPU service speedup.

## Prior evidence and novelty boundary

The earlier fixed S1/P2 signature-center single-ball result remains negative:
it retained92.2501%/93.4250% of blocks. This study changes the controlled partition
space and holds a full-coordinate center rule fixed across its new controls;
it cannot attribute a difference from that older experiment solely to the tree.
It does not revive a novel single-ball thesis.

Partition adaptation is established:[UAI2009](https://arxiv.org/pdf/1205.2609)
compares spatial-tree diameter contraction under intrinsic structure.
Metric-ball range rejection is classical:[M-tree,VLDB1997](https://www.vldb.org/conf/1997/P426.PDF).
These precedents rule out novelty based merely on KD/PCA splits or ball bounds.
This diagnostic measures their behavior under one fixed contract,not a new index.

Fresh O0 verification reconstructs every node center/cover and internal split,
recomputes every old-query center score,and independently checks the full owner
oracle,reach sets and every reported scalar. The numerical interval helper is
shared with the preceding proved implementation;it is not independently rederived.
The960D low-intrinsic line is a small synthetic qualification,not a substitute
for GIST evidence or an intrinsic-dimension estimate.
