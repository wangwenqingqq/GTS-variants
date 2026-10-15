# Native and diagnostic tables

Native entries are medians of six process aggregates. A process p95 is a finite empirical quantile, not an SLA; B512 has only16 ACKs/process. Million = decimal. R amortizes over2B point updates, not B.

| Operator | B | Mean ACK ms | p50 ACK ms | p95 ACK ms | ACKs/s | M point updates/s | µs/point |
|---|---:|---:|---:|---:|---:|---:|---:|
| I | 1 | 0.006494170 | 0.006599000 | 0.006798000 | 153984.288 | 0.153984 | 6.494170349 |
| I | 32 | 0.025385961 | 0.025259250 | 0.026506500 | 39392.113 | 1.260548 | 0.793311279 |
| I | 512 | 0.280495000 | 0.280694500 | 0.292977250 | 3565.147 | 1.825355 | 0.547841797 |
| D | 1 | 0.008258643 | 0.008334500 | 0.008910675 | 121086.078 | 0.121086 | 8.258642700 |
| D | 32 | 0.091224303 | 0.089453500 | 0.098896000 | 10962.012 | 0.350784 | 2.850759460 |
| D | 512 | 1.407445625 | 1.378154500 | 1.508243375 | 710.513 | 0.363783 | 2.748917236 |
| R | 1 | 0.014426296 | 0.014478000 | 0.015841850 | 69318.757 | 0.138638 | 7.213148102 |
| R | 32 | 0.117301223 | 0.115493500 | 0.125993625 | 8525.096 | 0.545606 | 1.832831604 |
| R | 512 | 1.707966031 | 1.677120000 | 1.818474375 | 585.494 | 0.599546 | 1.667935577 |

## Mixed service: native medians

Totals are separately aggregated process medians, not additive pie-chart pieces. Update shares are computed per process before aggregation. Events+release excludes the separately timed final-state export in both systems.

| System | Service ms | Query total ms | Delete total ms | Insert total ms | Update/service |
|---|---:|---:|---:|---:|---:|
| S1 | 1802.224032 | 172.949180 | 1318.476930 | 281.792550 | 89.321411% |
| S2_STALE | 1774.756564 | 136.902777 | 1333.863117 | 285.198578 | 91.148655% |

## Profiled Host partition — diagnostic only

Fractions divide by the same profiled whole ACK (R includes wrapper gaps); DMA is a non-additive device overlay. No independent profiler value is subtracted from native timing.

| Op | B | Profile/native mean ACK | Copy API % | Explicit sync % | Bookkeeping % | Other Host/wrapper % | DMA/ACK % |
|---|---:|---:|---:|---:|---:|---:|---:|
| I | 1 | 1.496958 | 36.336025 | 40.402058 | 3.907299 | 19.354618 | 4.671436 |
| I | 32 | 1.356113 | 64.240707 | 20.319907 | 8.496269 | 6.943118 | 14.614593 |
| I | 512 | 1.357831 | 87.565894 | 2.059704 | 8.468082 | 1.906320 | 50.304586 |
| D | 1 | 1.532189 | 42.310280 | 40.947107 | 7.448856 | 9.293757 | 9.203687 |
| D | 32 | 1.741704 | 87.039443 | 3.292070 | 8.396032 | 1.272456 | 23.360226 |
| D | 512 | 1.729730 | 90.081045 | 0.228486 | 9.192315 | 0.498154 | 24.430020 |
| R | 1 | 1.517617 | 39.394315 | 39.977793 | 6.511506 | 14.116386 | 6.440771 |
| R | 32 | 1.647833 | 83.145621 | 6.713960 | 7.623404 | 2.517015 | 18.376355 |
| R | 512 | 1.608456 | 90.227672 | 0.539802 | 8.670087 | 0.562439 | 24.721731 |

## Traffic and actual application work

| Cell | I | D | Boundary |
|---|---:|---:|---|
| B512 payload/ACK | 1,966,080 B H2D | 1,966,080 B D2D | Native requested and CUPTI bytes match |
| B512 copy calls/ACK | 1 | 512 | Exact runtime API counts |
| B512 explicit sync calls/ACK | 1 | 1 | Not a transport round-trip count |
| Application update kernels/launches | 0 | 0 | No explicit kernels in source; required query positive control visible |
| Native B512 payload rate GB/s | 7.009364 | 1.396926 | Payload/Host-ready ACK, not physical DRAM bandwidth |
| 1GiB bulk payload rate GB/s | 7.235592 pageable H2D | 733.880401 disjoint D2D | Different contract; no attainable delete bound |
| Exact DRAM/L2 bytes | N/A | N/A | Copy activity bytes are not DRAM transactions |
| Active warps/absolute SM throughput | Not calibrated | Not calibrated | Quantized percentage observations retained, scaled Avg fields not guessed |

All13 verified percent fields and their finite sample quantiles are in TIMELINES.json. They sample the device from first operator start to last operator end, not the full MICRO_FORMAL/COPY_FORMAL anchor and not an ACK-weighted average. A zero or one-percent observation is not a precise inactivity proof.

All six bulk-reference processes are retained, including two slower pageable-H2D rounds (~4.65/4.76 GB/s). They are not censored or silently replaced.
