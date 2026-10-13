# Validation scope and limitations

## Executed

1. Primary-source prior-art review before codec implementation. Admission was
   DISTINCT_ENOUGH_TO_TEST only for a cheap falsification; no novelty promotion.
2. Frozen contract, exact baseline/input/reference identities, four-worker
   nice=10 CPU admission, and no GPU visibility. Shared processes and device
   settings remained untouched.
3. Linux g++ 13.3.0 CPU library build with the registered no-fast-math,
   no-contraction, no-reassociation flags. Binary hash is in evidence/BUILD.json.
4. Corner/random fixtures: **10,025** bit patterns including NaN payloads,
   infinity, signed zero and subnormals; odd-D padding and on-disk recovery;
   **65,808** exhaustive 4/8/16-bit prefix windows; sampled/corner 32-bit singletons;
   finite-value coverage; ordered-FP64 range equality, duplicates, empty output,
   and explicit nonfinite service admission failures. Fixture stdout is retained.
5. Query-independent encoding and bit equality for **960M coordinates** recovered
   from the actual persistent source. Original validation mapping closed before
   any candidate query. Source size includes all four layers plus header.
6. First4096 qualification for each frozen query (**131,072 pairs**), before the
   one full population replay. All **32M** memberships and complete member IDs
   match, zero FN/FP; all **6,917** full-decoded score bits match. All **66,167,243**
   visited safe bounds are finite, monotone, and no larger than the frozen oracle.
7. Source, representation, original data and 32 oracle hashes rechecked at closure.
   **One** completed bounded population process; no failed population or retry.
   Its 169.717 s wall time is an operational receipt, not search latency.
8. A separate read-only observer rehashed saved proof arrays and unchanged
   reference files, then revalidated all terminal histograms, write masks,
   visited lower bounds, final score bits, IDs and multiplicity. This audit did
   not invoke candidate search or create a second population observation.
9. Scalar checker recomputes pooled stage/bit/byte conservation, verifies registered
   measurement sources and parent evidence, and enforces the declared NO-GO.
   Three numerical figures are supplied as SVG and 300-DPI PNG, with units,
   fixed-pool scope, readable print-sized type and redundant grayscale encodings.
   Figures were rendered and inspected; no manuscript figure was edited.

## Not executed or not established

- Gate1, CUDA implementation/correctness/sanitizer/stress, NCU/NSYS, actual DRAM,
  paired GPU timing, host-ready latency or sustained workloads: **NOT_RUN**.
- kNN, dynamic updates, larger query pools, alternate data/radii/schedules,
  learned/entropy coding, bit or dimension reordering, Tensor Cores: **NOT_RUN**.
- Exhaustive testing of all 2^32 singleton patterns or all possible queries:
  **not claimed**. Mapping is an algebraic bijection; fixtures and this fixed
  population are the measured validation scope.
- GPU prefix-state/compaction traffic: **unknown, not zero**. CPU local prefix
  retention is not a target-GPU memory forecast. Logical source payload excludes
  these separately disclosed costs and cannot be called measured physical traffic.
- Private original data, encoded source, full outputs, full reference scores and
  source PDFs: retained outside Git. Public scalar checks cannot independently
  reproduce the entire raw audit without access to the specified private inputs.
- Prior-art absence or a distinct publishable contribution: **not established**.
  No manuscript synchronization, compilation, submission or publication is claimed.

Before upload, the exact curated set is checked separately for disclosure safety,
source identity and reproducibility. Public Git state is verified after upload;
the existence of this local report alone is not proof of a push.
