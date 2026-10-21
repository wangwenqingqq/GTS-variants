# CPU shared-frontier opportunity gate

## Thesis boundary and prior-art kill test

Shared query/data traversal is not a new problem or mechanism by itself.
[Quickjoin,Jacox and Samet](https://www.cs.umd.edu/~hjs/pubs/jacoxtods08.pdf)
already partitions metric-space joins,including text/DNA edit distance.
The eD-index family is another prior metric-join organization;it is not
implemented by calling an unrelated EDJoin string filter.
[JZ-Tree](https://arxiv.org/abs/2604.05885) already provides collaborative
GPU dual-tree walks with coalesced accesses,principally for low-dimensional
Euclidean data. [Gowanlock's public self-join](https://github.com/mgowanlock/gpu_self_join)
is a strong spatial/grid competitor. Thus classical dual-tree/grouped pruning
cannot alone support a new GTS++ thesis. This CPU diagnostic is a cheap
falsification,not a novelty admission. Even a10x opportunity is necessary,
not sufficient,for any subsequent distinct-mechanism research.

## Actual controls,not mislabeled native executions

| Label | CPU trace meaning | Boundary |
|---|---|---|
| GTS_LITERAL_CPU | Height-safe radial multiway tree,per-child query/pivot evaluations | Structural replay of the released algorithm,not native CUDA timing or identical tie layout |
| GTS_PARENT_CACHE_CPU | Same tree,pruning,leaf verification and BFS;one distance per active query/parent | Strong simple sibling-distance reuse;any gain over literal GTS is not shared-query novelty |
| SHARED_ANNULUS_CPU | Binary query-ball tree plus shared source-annulus bounds,then adaptive cardinality-driven split | No oracle/future rejection;all query-index construction calls and memory charged |
| QUICKJOIN_FAMILY_CPU | Rectangular ball partitions and two cross-window joins | Own exact family reimplementation,not a native eD-index or benchmark of its original executable |
| GRID_2D_CPU | Epsilon cells plus exact all-pairs verification in intersecting neighbor cells | Gowanlock-family coordinate baseline;not native GPU self-join throughput |
| SPATIAL_DUAL_AABB_CPU | Exact max-span spatial trees and bounding-box node-pair traversal | JZ-family adversarial spatial control,NOT a reproduction of JZ's Morton/plane hierarchy or FoF shortcuts |

The last two apply only to TLoc. No unproved coordinate embedding is supplied
for Words or DNA. The native JZ package is not installed on the target host;
no dependencies or CUDA paths are installed/launched. JZ kNN/FoF output cannot
silently replace complete epsilon-join output. Native JZ range-join adaptation
and native external timing remain unmeasured,not reported as failures.

## Frozen scope and accounting

The frozen contract precedes population counters. Words uses the existing
611756-row byte-string source. DNA is a separately labeled real-genome-derived
population:1M nonoverlapping108bp ACGT windows from public GRCh38 chr1,not the
unavailable original GTS DNA file. [UCSC provenance](https://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/)
identifies the assembly and public-use rights. TLoc uses the existing10M-row
2D source only as competition stress. Full source identities and selection
manifests are retained;trace size is65536 initial objects plus32 reserved
incoming objects,not a claim that the full source population was benchmarked.

Each frozen batch has256 original-row queries;two fixed seeds,three edit
radii/two spatial radii. All methods return every directed(query,data-ID,score)
triple,including self-matches and duplicate-content rows. No data outcome
selects queries,radii,partition parameters or the stopping threshold.

GTS fanout10/leaf20,midpoint pivot and sorted radial shells follow the
[released source](https://github.com/ZJU-DAILY/GTS). CPU height is sufficient
for every leaf;the unsafe fixed-height allocation is not used as a fast
baseline. CPU ties use immutable row IDs. Original headers remain private;
no upstream code or license is republished. The trace implementation is new
CPU code and clearly separates contract adaptation from native equivalence.

Counters include every metric evaluation by role,all candidate-verification
pairs,rejected and retained node-pair visits,both BFS buffers,allocation
capacity and logical query-node ownership. Query-tree resident bytes are
added to the shared-frontier denominator. Dense native GTS flags are reported
as a formula,not admitted as a weak memory baseline. Shared node-pair records
alone are not evidence of10x elimination if they merely pack more unresolved
query ownership into one record. DFS is not used to manufacture small queues.
Quickjoin task/window identity payloads are separate from tree-node units;
its metric counts are directly comparable,but its frontier unit is not silently
pooled with query-node pairs. CPU wall times are resource observations,not a
paired performance campaign or GPU-service prediction.

All implementations share the same exact metric primitive:bit-parallel
Levenshtein checked against independent two-row DP,or ordered FP64 squared L2
on FP32-parsed coordinates. L2 bounds use outward conservative intervals;
the CPU adaptation is not native GTS FP32 arithmetic parity. Complete output
streams are compared to an all-pair reference;that reference shares the metric
primitive,so it is not an independently rederived full-distance oracle.

Updates are a bounded full-rebuild diagnosis:delete32 frozen non-query IDs,
rebuild;append32 reserved real objects,rebuild. The middle-radius seed1
outputs are rechecked completely in both updated states. This does not claim
fine-grained ACK,concurrent updates or a100k-event workflow.

## Decision

A meaningful distance gate is10x including query-plan work versus the strongest
applicable non-shared competitor,not just literal GTS. A frontier gate requires
both10x allocated ownership-aware payload and10x logical query-node reduction
versus compact cached GTS. Every primary cell must pass for GO;no primary cell
passing means NO_GO. A mix remains MIXED and stops without promotion. TLoc
cannot rescue a Words/DNA failure. Missing/censored/invalid evidence is not a
negative result. Any first failure stops without retry. No CUDA follows from
any outcome. A negative is limited to this frozen classical candidate,not an
information-theoretic impossibility of all shared-frontier mechanisms.
