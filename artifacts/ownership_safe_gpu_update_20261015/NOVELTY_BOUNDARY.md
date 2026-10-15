# Engineering value is not novelty admission

The frozen W2 has no within-batch copy dependencies and no removable row moves. On that workload, FINAL's executor is an ordinary indexed,coalesced GPU copy. A win over CUDA's batch-copy API therefore does **not** establish a new ownership algorithm:the two implementations can have very different internal per-copy execution costs despite equally small Host API counts.

Parallel indexed gather/scatter is established functionality;see NVIDIA's [Thrust gather source and contract](https://github.com/NVIDIA/cccl/blob/main/thrust/thrust/gather.h). This is a mechanism comparator,not a claim that the library was benchmarked here or that its nonoverlap contract can be ignored. CUDA13.1 also already provides [unordered batch-copy APIs](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/group__CUDART__MEMORY.html);our WAVES comparator preserves ordering by separating dependent levels.

The additional object under investigation is **strict full-capacity tail-provenance composition**,including retired rows,under the native descending-last swap contract. Its proof and dependent-shape correctness are useful,but not by themselves evidence of scientific novelty over dead-store elimination,permutation compilation or parallel compaction. A same-contract generic GPU gather/scatter comparator on dependency-rich mixed-query traces is still missing. No claim of beating all ordinary GPU batching implementations is allowed.

The synthetic chain distinguishes movement elimination from call-count reduction. It is not a measured dependency-rich GIST service. The current study improves the inherited contiguous-vector Frozen-PDX service;it does not establish an improvement to every GPU tree,original GTS traversal or an external Faiss/CAGRA system.

Decision scope:retain any reproducible engineering improvement and the semantic proof. Novelty remains **not admitted**. Reopen a paper-level claim only with a distinct mechanism not explained by known gather/scatter/compaction,plus decisive same-contract mixed-workflow evidence against those alternatives. This is a missing-evidence boundary,not a universal impossibility result.
