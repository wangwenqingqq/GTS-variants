# Exact scan diagnostic results

GIST **N1M/D960 FP32 L2 B1**, original 32 range queries, radius bits 0x3f34a3d8. All primary values are the median of six process-level mean query intervals; p10/p90 are process quantiles, not per-query tails. Profilers are separate.

## 1. Unchanged native keeper

| Quantity | Median | p10 | p90 |
| --- | --- | --- | --- |
| Query ACK (ms) | 3.354495 | 3.283151 | 3.370836 |
| Continuous 32-query pass (ms) | 107.345354 | 105.062769 | 107.868824 |

The later FULL_OUTPUT control has the same unmodified Scan::range body and bit-identical answer payloads, but additional persistent diagnostic workspace outside query timing. Keeper and later control processes are not genuinely paired. No speedup is claimed between them.

## 2. Controlled ablation

| Mode | Query median ms | p10 | p90 | Signed previous delta ms |
| --- | --- | --- | --- | --- |
| READ_ONLY | 2.517245 | 2.516806 | 2.517675 | — |
| DISTANCE_ONLY | 3.291015 | 3.260549 | 3.336014 | 0.773770 |
| THRESHOLD_COUNT | 3.290806 | 3.256998 | 3.336730 | -0.000209 |
| FULL_OUTPUT | 3.315706 | 3.297626 | 3.379547 | 0.024900 |

These are different diagnostic pipelines, not additive exclusive phases or production replacements. READ_ONLY contains checksum/reduction; DISTANCE_ONLY contains score aggregation; THRESHOLD_COUNT substitutes a count reduction for full compaction. The tiny negative threshold-minus-distance delta is retained, not clipped.

| Paired numerator/denominator | Marginal median ratio | Paired geometric ratio | 95% paired CI | Wins | Forward / reverse |
| --- | --- | --- | --- | --- | --- |
| READ_ONLY/FULL_OUTPUT | 0.759188 | 0.755754 | [0.749023, 0.761969] | 6 | 0.757118 / 0.754393 |
| DISTANCE_ONLY/FULL_OUTPUT | 0.992553 | 0.989460 | [0.981957, 0.996633] | 6 | 0.997690 / 0.981297 |
| THRESHOLD_COUNT/FULL_OUTPUT | 0.992490 | 0.989149 | [0.982794, 0.995311] | 6 | 0.995959 / 0.982387 |
| DISTANCE_ONLY/READ_ONLY | 1.307388 | 1.309234 | [1.299192, 1.322004] | 0 | 1.317746 / 1.300777 |
| THRESHOLD_COUNT/DISTANCE_ONLY | 0.999937 | 0.999687 | [0.997241, 1.002275] | 4 | 0.998265 / 1.001110 |
| FULL_OUTPUT/THRESHOLD_COUNT | 1.007567 | 1.010970 | [1.004711, 1.017507] | 0 | 1.004057 / 1.017929 |
| high/low | 1.002235 | 1.003698 | [0.999913, 1.007838] | 2 | 1.001399 / 1.006002 |

Bootstrap: 20,000 paired process log-mean resamples, seed 2026101111. A win means numerator time < denominator; mode ratios are not system speedups.

## 3. Exclusive diagnostic timeline

| Component | Mean ms/query | Host-span share % |
| --- | --- | --- |
| distance_fused_read_arithmetic | 3.282701 | 97.1930 |
| predicate | 0.004651 | 0.1377 |
| compaction | 0.006241 | 0.1848 |
| output_fields_and_observer | 0.003140 | 0.0930 |
| copy_Host-to-Device | 0.000513 | 0.0152 |
| copy_Device-to-Host | 0.002089 | 0.0618 |
| exposed_Host_gap | 0.078173 | 2.3145 |

GPU-active union=97.6855% of one 32-query NVTX capture. Runtime APIs overlap it: cudaMemcpyAsync inclusive 106.007287ms, GPU overlap 104.596661ms. Do not add API waits to GPU time. No allocation/free API occurs in this static measured span. Event phase spans remain diagnostic and may include Host enqueue/resize gaps.

## 4. Main-kernel roofline

| Selected mode | NCU ms | DRAM read GB | DRAM write MB | L2 total GB | DRAM GB/s | FP32 executed TFLOP/s | Executed FLOP/DRAM byte | Occupancy % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| read | 2.507328 | 3.840142 | 5.464832 | 3.840627 | 1533.747 | 0.383501 | 0.250042 | 88.9300 |
| distance | 3.324352 | 3.840072 | 13.142272 | 3.904871 | 1159.087 | 55.445392 | 47.835386 | 28.8700 |
| full | 3.322912 | 3.840073 | 13.000448 | 3.904870 | 1159.547 | 55.469420 | 47.837140 | 28.8600 |

Each row is one first measured main-kernel launch, not all 32 queries, output kernels or the full Host interval. NCU replay uses 10 passes, no cache flush/clock modification. FP32 executed proxy = predicated-on FADD + FMUL +2*FFMA; FP64 add/mul/FMA counters are 0 here.

Useful model: 3.84GB and 2.879G scalar operations/query. The native kernel instead records 184.32G executed FP32 proxy FLOPs (~64.02x useful model); do not substitute useful FLOPs for executed work when explaining the roofline. Advertised peaks are 1597GB/s and 120TFLOP/s; the same-campaign reachable stream reference is 1525.477GB/s, not a universal measured hardware maximum. D2D combined-read/write calibration is 1461.533GB/s and READ_ONLY Host logical-payload rate is 1525.477GB/s. Counter GB/s always uses duration from the same NCU capture.

Supplemental L2 capture: read 3,901,936,832B, write 4,658,048B, Other 321,536B, total 3,906,916,416B. All are 32-byte request sectors. Other subtype is unknown. The initial two-bucket assertion was rejected offline; runtime and all 40 answers were already valid. This separate capture is not mixed with the earlier main-kernel L2 total, and no GPU rerun was used for the interpretation correction.

## 5. N and D scaling

| Series | N | D | Query ms | ns/object | Logical payload GB/s | Mean hits |
| --- | --- | --- | --- | --- | --- | --- |
| D | 1000000 | 128 | 0.526337 | 0.526337 | 972.760 | 1.18750 |
| D | 1000000 | 256 | 0.960568 | 0.960568 | 1066.036 | 16.84375 |
| D | 1000000 | 512 | 1.810292 | 1.810292 | 1131.309 | 103.87500 |
| D | 1000000 | 960 | 3.315706 | 3.315706 | 1158.124 | 205.93750 |
| N | 100000 | 960 | 0.400087 | 4.000871 | 959.791 | 22.78125 |
| N | 250000 | 960 | 0.884318 | 3.537273 | 1085.582 | 51.34375 |
| N | 500000 | 960 | 1.712587 | 3.425175 | 1121.111 | 101.53125 |
| N | 1000000 | 960 | 3.315706 | 3.315706 | 1158.124 | 205.93750 |

The GB/s column is logical vector bytes divided by Host ACK, not measured DRAM throughput. Lower-D output selectivity is not matched: D128/256/512 means 1.1875/16.84375/103.875 versus 205.9375 at D960. D scaling is therefore descriptive, not a pure same-hit arithmetic/memory attribution. N prefixes keep original Host query vectors and radius even when qid is outside the prefix.

## 6. Selectivity

| Radius label | Actual mean hits | Query ms |
| --- | --- | --- |
| low | 200.34375 | 3.275366 |
| mid | 205.9375 | 3.315706 |
| high | 1644.9375 | 3.282688 |

The target 10/current/10x-current counts are not attained; no post-measurement retuning. Actual high/low hit count grows 8.210x but the paired time ratio CI crosses 1. This rejects a large output bottleneck only within this attained sparse-output range, not dense answers or all query distributions.

## 7. Fixed 336-event dynamic workflow

Continuous trace median 1332.923838ms includes service release but excludes setup/context/warmup/disk. Sum of operation ACKs is a distinct denominator.

| Operation | Count | Median total ACK ms | Median event p50 ms | Median event p95 ms |
| --- | --- | --- | --- | --- |
| insert | 40 | 0.544458 | 0.013355 | 0.015273 |
| delete | 40 | 0.297361 | 0.006330 | 0.015514 |
| range | 128 | 431.975867 | 3.371714 | 3.387057 |
| knn | 128 | 860.644990 | 6.018969 | 6.026697 |

Median update ACK share of continuous trace=0.063045%; UPDATE_BOUND fails. Inserts move 153,600 H2D bytes ; 20 swap deletions move 76,880 D2D bytes; no rebuild. Historical 0.532743/0.293380ms entries were 40-operation ACK sums, not per-operation medians. CPU rusage/trace ratio=0.998461 core-equivalent. It does not identify CPU arithmetic or driver polling without sampled stacks.

One dynamic NSYS capture has GPU-active fraction 90.7837%. It includes one lazy cudaHostAlloc call (97.915261ms), charged to the first measured kNN after cloned warmup restoration. This is not an update cost, and moving it to setup would not remove cold-service work. Secondary kNN uses native Faiss with use_cuvs=false; do not transfer the range-kernel resource classification to kNN.

## 8. Ordered-FP64 reference

One diagnostic process: all 40 complete answers and field bits pass; measured 32 query mean 6.658273ms. This is not a six-process native comparator, paired ratio or system speedup. Tree/packed setup outside this reference interval is retained in metadata; no tree query is executed.
