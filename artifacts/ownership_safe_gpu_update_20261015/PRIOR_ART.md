# Gate0: nearest techniques and cheap kill test

This is not a claim that batching,scatter/gather,permutation,compaction or dead-store elimination is new.

- [CUDA13.1 memory API](https://docs.nvidia.com/cuda/archive/13.1.0/cuda-runtime-api/group__CUDART__MEMORY.html):cudaMemcpyBatchAsync is already available in the installed runtime. Copies inside a batch have no order guarantee;dependent copies are undefined. We use dependency-safe levels as the ordinary available baseline,not an unsafe direct batch. API fields/signature are checked against the installed13.1 headers,not a12.x example.
- [EnTT sparse-set source](https://skypjack.github.io/entt/sparse__set_8hpp_source.html):sequential swap-and-pop,bulk iteration and tombstone compaction establish standard ownership techniques. They do not by themselves establish a same-contract GPU dynamic exact-range advantage.
- [NVIDIA stream compaction](https://developer.nvidia.com/gpugems/gpugems2/part-iv-general-purpose-computation-gpus-primer/chapter-36-stream-reduction):scan/gather/compaction are longstanding prior art. Generic compaction is not automatically strict sequential-swap layout compatibility.

Cheap falsification: compare ordinary safe runtime batching against composed final-source materialization,first on full-capacity CPU state and dependent adversaries,then on a bounded same-contract GPU screen. If safe batching accounts for the practical gain,report an engineering improvement,not a new scientific mechanism. The current search does not establish novelty;more expensive thesis development is not admitted by an operator win. Any broader novelty claim requires a new same-setting prior-art audit and decisive advantage beyond packaging.
