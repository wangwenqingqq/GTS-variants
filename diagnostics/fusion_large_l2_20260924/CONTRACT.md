# Large L2 result-fusion comparison

Registered 2026-09-24 before this campaign's GPU runs. Compare the same C/E
result pipelines as the completed N=2000 campaign at N=65,536 and N=1,000,000
for pinned GIST (960D), Deep (96D), and Tloc (2D). No cross-dataset absolute
query-latency claim; only within-dataset C/E ratios. Same original traversal,
native layout, batch one, fanout 10, leaf cap 20, and float32 L2 arithmetic.

Create nested real-data subsets containing all previous N=2000 source IDs plus
seed-20260924 additions from each pinned 1M source. Retain the eight prior
query source IDs at offsets 0,8,...,56 of the 64-ID fixture and remap their
local IDs at each N. Normal inclusive radius is the prior N=2000 normal radius
for each dataset, held constant across N. Also test zero, a CPU-oracle-derived
all-hit radius (maximum of all eight query/dataset distances plus one), and -1.
Independent float64 CPU L2 matrices cover all eight queries against every
point; cross-check sample distances with scalar CPU loops. Record source and
fixture hashes, full output count/order/float32 bits and oracle tolerance.
At the normal-radius boundary, require exact membership outside the declared
absolute/relative numeric tolerance, allow either side only inside that band,
and report the ambiguous count. C/E must still match native A bit for bit.

The source data are float32. Use an experiment-only contiguous binary loader
before tree construction to avoid the original per-number stringstream parser
at 1M. This changes setup/input decoding for BOTH arms, outside the timed
query. Check binary data bit-for-bit against the pinned source and previous
N=2000 fixture. Reuse the dynamic-capacity Words C/E driver and exact selector;
only extend its metric/N assertion and binary loader. Height is determined by
the same worst-child bound, and node/leaf coverage verified after construction.
No change to query arithmetic, C/E memory allocation, transfer length,
traversal or selector algorithm. Report loader and construction outside timing.

Full A/C/E normal-radius output checks use eight queries per dataset/size.
At N=1M, additionally check A/C/E at radius zero (two query IDs), A/C/E at
all-hit radius (one query ID), C/E at -1 (two IDs). C/E memcheck and synccheck
at each size on one fixed query ID; E initcheck and racecheck at N=1M.
Stress C/E with 8 changing queries x 4 repeats after 16 warmups per size.
No timing is admitted before all validation passes.

Six fresh C/E paired rounds, alternating CE/EC and dataset/size traversal
order; 16 warmups/process. At N=65,536 measure 32 queries/process (8 IDs x4);
at N=1M measure 8 queries/process (8 IDs x1). Median process-mean completed
hot-query latency and C/E ratio, exact 6^6 paired log-ratio bootstrap, wins/6.
Two sustained opposite-order pairs double the query count. Full host-ready
output delivery is timed; loading, construction, setup/capture, warmups and
hashing excluded and reported separately. All timed output hashes must match
CPU-validated native order. No pooling with historical N=2000 observations.

NSYS C/E at each dataset/size: two fixed query IDs, two warmups, one measured
repeat and first call (five query executions); verify actual common kernels,
removed result stages and kernel counts. Profile timings are diagnostic only.
GPU admission: one freshly idle RTX PRO 6000, same UUID for all runs, advisory
lock and in-process foreign-work monitoring. Stop owned work on interference
or any gate failure; preserve failures, do not replace samples. CPU shared;
GPU clocks, power and driver settings unchanged. Retain raw local audit data.
No production, cold-start, dynamic-update or other-metric claim.
