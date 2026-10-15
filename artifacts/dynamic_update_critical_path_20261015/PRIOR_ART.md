# Gate0 and competing explanations

This is a diagnosis of an existing implementation,not a new dynamic-search
mechanism. Batching transfers and amortizing launch/wait overhead are ordinary
CUDA techniques. A fine-grained bottleneck,if measured,is not by itself novelty.
The cheap kill test is to inspect and then trace the unchanged native copy/API
sequence before designing anything: delete may issue one D2D swap per moved
row,whereas insertion can upload a contiguous batch with one H2D call. A naive
bulk delete substitution would be invalid when source/destination ownership
dependencies differ. No such substitution is made here.

[NVIDIA CUDA13.1 synchronization semantics](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/api-sync-behavior.html)
explicitly make asynchronous-copy behavior argument-dependent;pageable Host
memory can require staging or blocking. Therefore an Async name is not proof
of no CPU wait,and a stream-sync duration is not all GPU computation.

[Nsight Systems user guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html#gpu-metrics)
distinguishes sampled device-level utilization from per-process attribution.
The installed2025.5.2 gb20x definitions are separately hashed. Its DRAM metric
is interface-active percentage,not an exact transferred-byte counter. The
[analysis guide](https://docs.nvidia.com/nsight-systems/AnalysisGuide/index.html)
provides CUDA runtime,copy and NVTX timeline exports. Profiler overhead and
nested/overlapping work require comparison to unprofiled whole ACKs.

Symmetric hypotheses: data movement or GPU work may dominate;alternatively
Host validation/mapping,copy API submission,waits and their serial granularity
may dominate. Batch trends,actual API/transfer counts and intervals plus a
standard large-copy reference distinguish them. Low SM activity alone cannot
reject a copy-engine bandwidth limitation. Any novel design requires a new
prior-art and same-contract advantage gate after this attribution study.
