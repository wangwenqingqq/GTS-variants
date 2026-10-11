# LINEAR_PROJECTION_CERTIFICATE_KILLED

Full-database PCA and random orthogonal projected AABBs did not meet the
predeclared information gate on the frozen original tree. Stage A and all full
matrix correctness gates passed; this is a valid negative result, not a numerical
failure or missing-evidence rejection.

| Level | PCA-4 gap (32B) | PCA-8 gap (64B) | PCA-8 new / G0 visits | Best <=64B pivot gap | PCA-8 minus pivot |
|---|---:|---:|---:|---:|---:|
| L3 | 4.664855% | 4.891304% | 4.106464% | 8.529589% | -3.638285 pp |
| L4 | 6.604089% | 6.927600% | 5.711470% | 9.188991% | -2.261391 pp |
| L5 = leaf | 14.741883% | 16.857069% | 14.349396% | 13.526861% | +3.330208 pp |

Maximum PCA-8 gap = 16.857069%, below the 30% kill threshold. No ancestor
configuration reaches 50% gap plus 30% G0 pruning. Random-1/2/4/8 add no pruning
at any level. Stage C is skipped because its predeclared [30%,50%) condition is
false. Leaf-only status is also false (leaf gap <50%). The K3 random≈PCA weak
criterion holds only at L3, not at all three levels; PCA has a real, bounded
advantage at L4/L5. Preserve that counterevidence rather than claiming PCA and
random are equivalent everywhere.

## Negative-evidence record

- **Target:** missing information in native GTS certificates, measured by the
  native-to-truth gap; same 8 stratified development queries, GIST1M D960 K8 B1.
- **Keeper:** original full-path fixed-U* bound, unchanged region ownership.
- **Rejected mechanism:** two frozen nested linear projected-AABB families at
  k<=8 with 16–64B aligned records, on this existing tree and query slice.
- **Added costs:** query projection (61,440 coordinate updates for eight queries
  at k=8), aligned metadata reads, and joint box arithmetic; separate ledgers.
- **Measured effect:** leaf gap improves over the strongest pivot by 3.330208 pp,
  but ancestor gaps are smaller than the pivot envelope and all levels miss kill.
- **Diagnosis (inference):** these small boxes leave most certificate headroom
  unresolved. PCA retains 47.903783% of database variance in eight dimensions,
  which does not imply similar pruning information. This does not identify the
  universal root cause or prove the partition is bad.
- **Thesis impact:** do not promote PCA-plus-box as novel, and do not start CUDA
  implementation of this candidate on the current evidence.
- **Reopen condition:** a materially different, novelty-qualified representation
  or certificate-aware partition must first pass a cheap same-contract screen;
  broaden sampling before any population or GPU acceleration claim.

A recommended next research question is partition–representation co-design with
a decisive external comparator. That is a recommendation, not an experiment
performed here. No rebuild, new partition, GPU kernel, timing, CUDA Graph, NSYS,
NCU, formal256 or 10K run was performed.
