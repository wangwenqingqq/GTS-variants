# Phase A: admission is NOT_ADMITTED

The core primitives are established. A verified one-system evaluation of the
entire strict deadline, mixed exact output and mutable-ordering contract was
not found in the inspected sources. Neither absence nor partial overlap proves
novelty. Do not force `SUBSUMED_PRIOR_ART`, or claim a new mechanism.

The user authorized only a bounded CPU opportunity falsification despite this
unresolved admission. This is not DISTINCT_ENOUGH_TO_MEASURE, a paper admission
or a GPU exception. No external implementation/performance is reproduced.

## Capability matrix

Y = documented capability; E = exhaustive retained-representation search, not
our ordered-FP64 parity proof; T = tiled/reuse opportunity, not measured traffic;
W = window/timeout policy, not complete per-query SLA; ? = not established by the
inspected source; N/A = a different problem domain. No question mark means
evidence that a capability is impossible.

| System | Offline batch | Shared DB tile | Online batch | SLA-aware | Exact | Range | kNN | Mutable DB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Faiss GPU Flat | Y | T | ? | ? | E | ? | Y | add/reset; no ordering proof |
| cuVS brute-force | Y | T | via wrapper | W via wrapper | E | ? | Y | ? |
| cuVS dynamic batching + brute-force | Y | upstream T | Y | W | E | ? | Y | external lifetime |
| Flasma service | Y | ? | Y | W | E | ? | Y | fixed targets |
| OpenViking cuVS microbatch | Y | upstream T | Y | W | E | ? | Y | Y |
| Faiss CPU Flat range | Y | ? | ? | ? | E | Y | Y | Y; no concurrent-order proof |
| Milvus | Y | GPU-dependent | ? | consistency/timeout | index-dependent | capped search | Y | Y |
| Triton dynamic batcher | Y | backend-dependent | Y | W + timeout/priority | backend-dependent | ? | ? | backend-dependent |
| Orca | Y | shared model, not DB | Y | scheduling policy | N/A | N/A | N/A | N/A |
| MultiQx-GPU | Y | resource sharing | Y | query scheduling | SQL, not vectors | N/A | N/A | ? |
| Proteus GPU data management | Y | H2D transfer sharing | query concurrency | ? | SQL, not vectors | N/A | N/A | HTAP discussion |

## Sources, locators and material boundaries

1. [Faiss GPU/CPU guide](https://github.com/facebookresearch/faiss/wiki/Comparing-GPU-vs-CPU)
   explains batched index-memory amortization and floating-point CPU/GPU
   differences. [GPU guide](https://github.com/facebookresearch/faiss/wiki/Faiss-on-the-GPU)
   documents host/device input, copies back, Flat indexes and caller-managed
   batching. This covers batched exact kNN and distance-matrix reuse, not an
   online deadline scheduler or identical FP64 reductions. GPU Flat range support
   is not inferred from the CPU API.
2. [cuVS brute-force](https://docs.nvidia.com/cuvs/user-guide/api-guides/indexing-guide/brute-force)
   documents full-dataset comparison and matrix queries.
   [Dynamic batching](https://docs.nvidia.com/cuvs/user-guide/api-guides/other-ap-is/dynamic-batching)
   includes brute-force upstream support, timeout/cap dispatch, output scatter,
   and latency/throughput priority choices. At pinned revision
   `bc23aa84a0ef26d85900185ad5e68d3372be487e`,
   `cpp/tests/neighbors/dynamic_batching/test_brute_force.cu:14-27` instantiates
   brute-force correctness tests; `cpp/include/cuvs/neighbors/dynamic_batching.hpp`
   distinguishes dispatch timeout from total latency. These tests are not an
   evaluated original-FP64 mixed-range service SLA. Nonconservative mode can
   execute a maximum-size padded search with only a few valid rows.
3. [Flasma](https://github.com/sionic-ai/flasma/tree/906fa7a92ab9c3ca14e2b2730ae70b35949645bf)
   reports REST-level batch throughput and exhaustive cosine ranking.
   `AkkaQueueService.scala:22-28` implements a cap or 5ms collection window;
   `CosineSimilarity.scala:36-62` broadcasts query rows over the whole target
   tensor and reduces/top-k selects. Thus it is not proof of one on-chip DB
   stream or a complete deadline guarantee. The README admits numerical changes
   and unlike-hardware comparisons. Its fixed targets and window alone neither
   match the proposed mutable contract nor establish its novelty.
4. [OpenViking cuVS guide](https://github.com/volcengine/OpenViking/blob/3385dd5966df7c4d9a1582305c3e95489f2b4b60/docs/en/guides/16-cuvs.md)
   documents exact microbatching, immutable snapshot/filter/top-k compatibility,
   maximum eight requests and configurable collection delay. The source
   `cuvs_index.py:1962-2000` implements oldest/cap dispatch;
   `:672-747` performs one matrix call, synchronization and host result copies.
   Mutation/rebuild generations and native fallback have different numerical
   representations. Collection delay explicitly excludes worker/device backlog.
   Most importantly, [PRELIMINARY_RESULTS.md](https://github.com/volcengine/OpenViking/blob/3385dd5966df7c4d9a1582305c3e95489f2b4b60/benchmark/cuvs/PRELIMINARY_RESULTS.md)
   labels its results pre-microbatch. A runnable current service harness is not
   evidence that the new microbatch path was measured with the full SLA. No such
   inference is used for a direct kill.
5. [Faiss CPU IndexFlat source](https://github.com/facebookresearch/faiss/blob/main/faiss/IndexFlat.cpp),
   `range_search`, covers batched exhaustive range independently of kNN. It does
   not establish a mixed GPU postprocessor or strict ordered-FP64 agreement.
6. [Milvus vector search](https://milvus.io/docs/v2.4.x/single-vector-search.md),
   [GPU indexes](https://milvus.io/docs/gpu_index.md),
   [range search](https://milvus.io/docs/range-search.md) and
   [consistency](https://milvus.io/docs/consistency.md) cover request vector lists,
   GPU index choices, capped range retrieval and GuaranteeTs visibility.
   Group-by is not cross-request batching. ANN/range-with-limit is not our
   complete exact range contract; different consistency modes are not silently
   interchangeable. One integrated shared-full-scan SLA evaluation is unverified.
7. [Triton batchers](https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/user_guide/batcher.html)
   establish collection delay, capacities, priorities and reject/defer timeout
   policies. The scheduler is generic, not by itself an exact vector backend.
8. [Orca, OSDI2022](https://www.usenix.org/conference/osdi22/presentation/yu)
   establishes iteration-level admission and selective batching in generative
   inference. Sharing model work is not proof of mutable exact-vector scan
   semantics; continuous batching is an adjacent scheduler precedent.
9. [MultiQx-GPU, PVLDB2014](https://www.vldb.org/pvldb/vol7/p1011-wang.pdf)
   addresses concurrent analytical query scheduling and device memory management.
   [Proteus, CIDR2020](https://vldb.org/cidrdb/papers/2020/p18-raza-cidr20.pdf),
   Section5.2 and related work, shares transfers across queries and discusses
   epoch storage. H2D sharing is not the same denominator as on-device DRAM
   sharing, and SQL concurrency is not exact vector-SLA evidence.

Mandatory areas are covered: offline Flat, GPU multi-query kNN, tiled distances,
range search, vector-DB batching, dynamic/continuous serving, shared GPU scans,
mixed range/kNN (not established), and update/snapshot ordering. Complete
host-ready output is documented in Faiss/OpenViking; parity and SLA are untested.
The pinned code/doc hashes and retrieval limits are in SOURCE_IDENTITIES.json.

## Admission conclusion

Ordinary cap/window batching and shared dataset evaluation cannot be claimed as
GTSPP novelty. The stronger proposed coupled system remains NOT_ADMITTED, not
disproved and not proven subsumed. The only authorized continuation is the cheap
four-rate CPU model. Any future GPU or paper stage needs a distinct mechanism,
an exact output/visibility contract and a comparison against these prior systems
and the progressive keeper. Changing architecture, range support or batch size
alone is not a reopening condition.
