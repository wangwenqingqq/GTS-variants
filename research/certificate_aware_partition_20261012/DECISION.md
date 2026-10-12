# Decision: PARTIAL_CO_DESIGN_SIGNAL

**Matching membership to the fixed PCA box improves safe certifiability, but the
predeclared ancestor promotion gate is not met. Do not enter GPU implementation.**
This is the primary PCA-only matrix on 8M query-object pairs, not the older
native-to-truth gap metric. PCA8 uses 64B per region.

| Partition | L3 alignment | L4 alignment | L5 alignment |
|---|---:|---:|---:|
| P0 GTS original | 13.19% | 22.04% | 35.62% |
| P1 random balanced | 0.00% | 0.07% | 12.71% |
| P2 PCA balanced | 39.84% | 45.80% | 54.49% |
| P2 minus P0 | +26.65 pp | +23.76 pp | +18.87 pp |

Neither ancestor reaches 60%, and neither gains 30 pp over P0. Both exceed the
20 pp random-control margin. Kill K1 and leaf-only K3 do not fire; K2 is false at
all three levels. The predeclared partial rule applies, without changing gates.

## The strongest material caveat: the hard queries remain weak

All six original high-visit queries improve at all levels, but improvement is
not the same as adequate certifiability. Their 6M-pair pooled PCA8 alignment is:

| Partition | L3 | L4 | L5 |
|---|---:|---:|---:|
| P0 | 2.20% | 5.98% | 17.17% |
| P2 | 22.89% | 29.81% | 40.49% |

For query 359924, P2 L4 reaches only 7.06%. Query 470632 reaches 59.47% at L4;
the other hard-query L4 values span 17.92%–36.71%. There is no uniform rescue.

Query 660835 remains positive: P0 to P2 is 75.75% to 94.98% at L3 and 88.10% to
95.59% at L4. Excluding it, pooled alignment still rises from 4.21% to 31.95%
(L3) and 12.60% to 38.69% (L4), denominator 7M. Thus the gain is not solely this
exception, but the eight-query pooled result must not be presented as the hard
query result. Query 90208 is another strong case (P2 L4 91.94%).

## Residual, geometry and contamination

| Partition | L3 truth residual | L3 PCA8 residual | L4 truth residual | L4 PCA8 residual | L5 truth residual | L5 PCA8 residual |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 0.5875% | 86.8875% | 0.0725% | 77.9750% | 0.0075% | 64.3820% |
| P1 | 0.8000% | 100.0000% | 0.0800% | 99.9338% | 0.0080% | 87.2885% |
| P2 | 0.6125% | 60.4000% | 0.0713% | 54.2313% | 0.0076% | 45.5184% |

Metadata/read and operation proxies are in the count CSV; they are not latency
or measured DRAM traffic. Query projection is charged once per query, not once
per level when combining a hierarchy. Each reported level is a separate offline
counterfactual, not a composed tree traversal or native GPU query plan.

Mean stored PCA8 box diagonals (L3/L4/L5) are P0 3.9139/2.8223/1.6418, P1
8.3360/5.6665/3.1447 and P2 4.1867/2.4456/1.1913. **P2 L3 has a larger mean
diagonal than P0 despite better pruning.** Scalar diagonal compactness alone
does not explain query-to-box separation; no uniformly-smaller-box claim.

At the unchanged U*, truth-retained L3 regions have 64 near objects in aggregate
under every partition, but P0 retains 47,000 objects and P2 49,000. Mean near
fractions are 0.1362% and 0.1306%; single-near fractions are 82.98% and 77.55%.
L4 retains 5,800 versus 5,700 objects, a small difference; L5 retains 600 versus
610. The severe near-object contamination is not systematically resolved.
The 1.05U/1.10U diagnostics are preserved separately, not used for pruning.

## Validation and costs

- G1: full unique balanced nested ownership in all three partitions.
- G2: 5,328,000 bounds checked; zero bound-above-truth and zero false topK
  prunes; C8 >= C4; all 18 fixed-size serialized records round-trip exactly.
- G3: P0 endpoint and truth bytes match prior inputs. The secondary native+PCA
  bridge reproduces all comparable fields in 6 pooled and 48 query rows. Its
  PCA8 remaining objects are 6,347,000/5,846,000/5,073,250 and its old gap is
  4.89%/6.93%/16.86%; these are not the primary alignment numbers.
- G4: 128 frozen query-region pairs per candidate, all objects independently
  reprojected and original ordered scores recomputed from original FP32 vectors.
  95,440 sampled membership occurrences cover 90,016 unique objects including
  query rows. All 720,128 independently recomputed query-object scores match
  cached scores bitwise; selected endpoints/truth match exactly.
- Local Python3.13/NumPy2.4 replay matches the remote Python3.12/NumPy1.26 counts,
  bridge and all metadata bytes. Six supplementary diagonal means differ by at
  most 8.89e-16, within a conservative FP64 reduction envelope; not called
  bit-identical. The separate scalar fixture is supplementary, not a G4 proxy.

P2 partition generation uses 11,111 sorts (5M sorted object occurrences),
1.1891 process CPU seconds, 4MB permutation and 76MB explicit peak scratch-array
proxy **with precomputed PCA coordinates**. PCA fitting/projection, input reads,
metadata and validation are excluded from that construction substep. P0's
0.5286-second prebuilt-index load/audit is not its original build time. Whole
worker highwater 4,828,892 KiB includes mapped inputs and validation. One
low-priority CPU core, no GPU, no query-latency or end-to-end measurement.

## Three separate decisions

- Implementation: **validated offline prototype** for the declared contract.
- Mechanism: **partial positive attribution**, beyond arbitrary reshuffling;
  insufficient absolute pruning and insufficient P0 margin for promotion.
- Thesis: **not established**. Balanced PCA splitting is prior art; one failed
  split does not reject all linear partitions or require nonlinear geometry.

Recommended next action is a cheap, fixed-budget certificate-effectiveness
split-objective probe focused on the six hard queries, with a fresh prior-art
kill test and held-out evaluation. This is a recommendation, not an automatically
started experiment. Reopen GPU construction only after an ancestor cell meets
all frozen promotion criteria and hard-query behavior is explicitly reported.
