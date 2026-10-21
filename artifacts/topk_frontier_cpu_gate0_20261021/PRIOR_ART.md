# Prior-art gate and scope correction

The parent fixed-radius experiment does not test top-k threshold-dependent cutoff decisions. This artifact does not use that parent result to reject the corrected hypothesis.

| Primary source | Established overlap | Boundary for this experiment |
|---|---|---|
| [Hjaltason and Samet, Ranking in Spatial Databases (1995)](https://www.cs.umd.edu/~hjs/pubs/incnear.pdf), Section4 | Save a node/object priority queue and resume to retrieve subsequent nearest objects,with deterministic ties. | Saved-frontier continuation is a strong ordinary control,not novelty. Tombstones and source-ID ties here are own contract adaptations. |
| [Hjaltason and Samet, Distance Browsing (1999)](https://www.cs.umd.edu/~hjs/pubs/incnear2.pdf) | Incremental nearest-object enumeration with distance bounds. | Does not establish a speedup for this string/delete workload. |
| [Ukey et al., Efficient Continuous kNN Join (2023)](https://link.springer.com/article/10.1007/s11280-023-01204-9), Sections5.2,5.3,6.3 | Batch affected-user de-duplication,reverse-kNN posting tables,and deletion replacement pruning using friend-user candidates and PCA bounds. | Numeric Euclidean/PCA setting differs from this Levenshtein probe. Neither deletion pressure nor batch affected sets alone establishes novelty. HDR implementation is not benchmarked here. |
| [SPB-tree (2015)](https://irc.cs.sdu.edu.cn/973project/result/download/2015/53.EfficientMetric.pdf) | Dynamic metric indexing;range and kNN search. | Native SPB is not present/admitted;own ten-way tree is not relabeled SPB. |
| [Jacox and Samet, Metric Space Similarity Joins (2008)](https://www.cs.umd.edu/~hjs/pubs/jacoxtods08.pdf) | Metric partition joins. | Own pinned Quickjoin-family helper receives a charged exact top-k upper-bound wrapper,not future true thresholds. |

## Pre-implementation decision

NOVELTY_NOT_ADMITTED. The broad dynamic deletion/batch-repair premise overlaps prior art. Run only a bounded CPU opportunity falsification against ordinary saved-frontier repair and a conditional same-tree threshold oracle. No new index or GPU implementation is justified in this gate. Missing native comparators remain unknown,not defeated baselines.
