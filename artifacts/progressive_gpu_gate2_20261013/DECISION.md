# Decision: GO_PROGRESSIVE_GPU

Strong-GO thresholds are met, but the formal label remains `GO_PROGRESSIVE_GPU`. Apply the human-approved order: GO -> NO_GO -> BYTE_SAVING_BUT_CONTROL_BOUND -> UNCLASSIFIED. No thresholds, stages, queries or numerical semantics were relaxed.

| Frozen admission | Observed | Pass |
| --- | ---: | --- |
| Complete membership and fields | 0 FN /0 FP; all checkpoint ID sets match | Yes |
| Mean all-kernel DRAM<=1.60GB | 1.119337016GB | Yes |
| Median process mean P1/B1<=0.80 | 0.443374874 | Yes |
| Paired95% CI upper<0.90 | 0.443627215 | Yes |
| Strong: DRAM<=1.30GB and ratio<=0.65 | Both met | Yes |

## Q1: Did the GPU exactly reproduce CPU Gate1 survivors?

Yes. All four complete checkpoint ID arrays for the original40 target qualification invocations (8 warmup +32 measured) matched Gate1 required dimensions or original ordered-FP64 full-score membership. Stable compaction retains ascending original occurrence IDs and multiplicity. Bounded4096 repeats and all three sanitizers also passed. Primary processes checked stage counts and complete final results; full checkpoint dumps are qualification-only and their transfer/export overhead is not used as primary timing.

## Q2: What is the actual complete DRAM traffic?

Mean all-kernel totals: B1 **3.862198832GB/query**, P1 **1.119337016GB/query**, reduction **71.0181%**. Independent diagnostics retained160 baseline and416 P1 launches over all32 queries, including all CUB initialization/selection and field kernels. P1 read/write1.059251120/0.060085896GB; L2 traffic1.215920365GB/query. Query DRAM min/p90/max0.560533504/1.483967539/1.626806784GB; these are workload variation, not confidence bounds. Strong-GO is explicitly a mean-query gate.

## Q3: Did complete Host-ready latency beat the strengthened scan?

Yes: same-campaign B1 **2.573117**, P1 **1.140855ms/query**. Reduction **55.6625%**, speedup **2.255428x**. Paired geometric ratio **0.443278**, 95% CI **[0.442961, 0.443627]**, six process wins; both forward/reverse strata pass. The old2.569716ms keeper number is historical context, not this comparison's denominator.

## Q4: What cost remains after byte reduction?

The independent event-enabled diagnostic has complete ACK **1.163904ms**, scan sum **1.036338ms**, CUB **0.053138ms**, fields **0.005012ms**. CUB is only **4.5655%** of this diagnostic ACK. Stage4 scan alone averages0.213077ms despite only14.473928MB/query in its new-coordinate payload; it includes the charged ordered960-coordinate replay of every retained hit. This supports further investigation of the final exact-score/replay path, but does not isolate arithmetic vs dependency latency vs memory with a causal control. Host-minus-events0.069416ms remains unattributed. No CPU-wait, persistent-kernel, or all-query-tail win is inferred from the residual.

## Q5: What is admitted next?

Only the frozen static feasibility gate is closed. A separate prospective Progressive E_ADAPT integration contract may now be proposed: charge insertion, deletion bookkeeping, layout/state maintenance and full-vector fallback storage, with logical-ID/generation ownership and full-output oracles. Do not automatically run the336-event workflow, tune stage boundaries, introduce a persistent/Graph version or edit the paper. The CUB>=25% persistent-motivation gate did not fire. Novelty remains ENGINEERING_ONLY until a clearly distinct mechanism survives nearest-prior-art and same-contract external kill tests.

## Retained negative and excluded evidence

One qualification guard attempt failed at a Python transitive import before CUDA initialization. It was retained; after explicit human approval, fixed baseline dependencies and Host proof checks were frozen in a new build. Kernel headers/fixtures and all five normalized selected P1 SASS functions were unchanged. No valid sample was discarded or rerun. R2/R3 CPU-only build/curation revisions do not consume GPU starts. Scalar postprocessing recognizes `ns`/`nsecond` explicitly and was checked against direct sums of all NCU rows. No manuscript, production path, incremental baseline or dynamic experiment changed.
