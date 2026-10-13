# Gate5 decision

## Q1: Exact-coordinate family headroom

**STRONG_HEADROOM.** O1: 2,574.0625 survivors/query; B0: 654,128.1875; ratio **0.003935104081**, below 0.50. This supports large information headroom in the frozen pool. O1 reads all 960 and selects for each pair; it is unpriced and not deployable. All 32M full-score bits agree, and zero pairs hit the numerical-boundary guard.

## Q2: One moment-score probe

C1: **41,480.0625 survivors/query**, realizing **94.0287%** of B0-to-O1 survivor headroom. The one subset uses only query and **7680 B** of dataset moments. No per-object metadata, alternate heuristic, layout change or budget sweep is added.

## Q3: Additional reduction

**GO_PROOF_PER_BYTE_ROUTING.** Ratio **0.063412742781**; additional survivor reduction **93.6587%**. Exact GO mean ceiling is **457,889.73125**, not the plan's rounded integer. Quality is evaluated first and passes.

## Q4: Query stability and exception

Min **0.000001456579**, p10 **0.000006205436**, median **0.003977562599**, p90 **0.373234554386**, max **1.0**. The p90 gate passes. Queries 625378 and 72436 already have one B0 survivor; both retain one. No stronger per-query/general-dataset claim is made.

## Q5: Separate final decisions

- **Implementation:** correctness-qualified CPU certificate reference, not complete search or a GPU artifact.
- **Mechanism diagnostic:** **GO_PROOF_PER_BYTE_ROUTING**, one fixed 512B selected-payload comparison.
- **Novelty/thesis:** **NOT_DISTINCT_ENOUGH_TO_IMPLEMENT**. Broad query-adaptive exact ordering is established; a moment correction does not supply a demonstrated non-incremental mechanism or external same-contract advantage.
- **GPU:** **NOT_RUN**, zero CUDA/NCU starts. Actual DRAM, latency and end-to-end effects remain unknown.

Stop after curating/uploading evidence. Do not write CUDA, replace keeper, add another heuristic, change budget/query/radius or promote manuscript claims. Reopening needs explicit authorization of a distinct mechanism and relevant adaptive comparator, not repackaged counts or small engineering gains.
