# Prior-art matrix — frozen before diagnostic implementation

Parent: `1341def36d95db3077e09032d88f57c476b386d6`. Source inspection: 2026-10-13.
This is a bounded primary-source audit, not proof that an unreported capability
is impossible. **NR** means not established in the inspected source. **Derived**
means a safe algorithmic specialization, not a published implementation or timing.
Algorithmic exactness does not qualify a library against our ordered-FP64 oracle.

| System | Exact | Range | kNN | Dynamic | Progressive dims | GPU | Physical layout | Aux rep |
|---|---|---|---|---|---|---|---|---|
| [BOND (S01)](https://www.cs.uoi.gr/~nikos/sigmod02.pdf) | Yes, bounds | Fixed-threshold specialization derived; measured API NR | Yes | Appends/updates discussed; bitmap deletes/reorganization | Yes | NR, CPU evaluation | Vertical dimensional fragments | Bounds/IDs; compressed fragments also studied |
| [PDX layout (S02)](https://arxiv.org/html/2503.04422v1) | Depends on search strategy | NR in paper | Yes | In-place/PAX-like maintenance discussed | Layout enables it | GPU identified as future work | Blocked vertical, multiple vectors per dimension | No required quantized copy in paper |
| [PDX-BOND (S02)](https://arxiv.org/html/2503.04422v1) | Yes | Fixed-threshold specialization derived | Yes | Raw-data pruning compatible with ingestion; dynamic benchmark NR | Yes | NR in paper | PDX; dense warmup then active positions | Means, partial distances/positions |
| [VA-file (S03)](https://www.vldb.org/conf/1998/p194.pdf) | Yes after exact refinement | Fixed-threshold specialization derived | Yes | Fixed cell boundaries during inserts/deletes/updates | Compact-code filtering; per-prefix execution derived | NR | Sequential approximation file + raw vectors | Bit-coded per-coordinate intervals/boundaries |
| [Faiss Flat (S04/S05)](https://github.com/facebookresearch/faiss/blob/1a9ddc60d2201c9a44dfca3acead6ee38fbe21dc/faiss/IndexFlat.cpp) | Exhaustive; numeric qualification separate | CPU API yes; native GPU API NR here | CPU/GPU yes | CPU add/remove; remove can move survivors | No for ordinary Flat | Yes, GPU implementation S06 | Raw full-vector storage; tiled GPU distance/selection | Norms/workspace, not a screening code |
| [cuVS brute force (S07)](https://github.com/rapidsai/cuvs/blob/b9a8f8062d50d9c0ec5ade8752d3027be7ebd1cc/cpp/include/cuvs/neighbors/brute_force.hpp) | Exhaustive; numeric qualification separate | NR in this header | Yes | Dataset replacement + sample filters; cheap row mutation NR | NR | Yes | Device row/column-major views | Optional norms/workspace |
| [GPU early-stop distance: cuVS IVF-PQ (S08)](https://developer.nvidia.com/blog/accelerating-vector-search-nvidia-cuvs-ivf-pq-deep-dive-part-1/) | Not exact raw-vector search | NR | ANN | NR in this article | Early stop over distance components | Yes | Aligned encoded chunks | PQ codes/LUT; not our exact comparator |
| [SIMD early-exit: SOFA (S09)](https://helios2.mi.parisdescartes.fr/~themisp/publications/icde25-sofa.pdf) | Exact refinement for its data-series setting | NR here | Yes | NR here | Chunked lower-bound early abandoning | CPU SIMD | Symbolic Fourier summaries + original data | Quantization bins/SFA codes |
| [UCR Euclidean early abandoning (S10)](https://www.cs.ucr.edu/~eamonn/SIGKDD_trillion.pdf) | Exact in its stated setting | Fixed cutoff derived | Nearest subsequence | Streaming series, not this row-update service | Yes, nonnegative partial squared distance | CPU evaluation | Time-series windows | Bounds/normalization state |
| [GPU stream compaction (S11)](https://highperformancegraphics.org/previous/www_2009/presentations/billeter-efficient.pdf) | Preserves predicate-selected items | Not a search API | Not a search API | Not a store/update API | Retains arbitrary staged work, not a distance rule | Yes | Dense retained stream | Flags/scan/selection state |
| [Faiss FlatPanorama (S04/S12)](https://github.com/facebookresearch/faiss/blob/1a9ddc60d2201c9a44dfca3acead6ee38fbe21dc/faiss/IndexFlat.cpp#L578-L704) | Intended exact bound at strict setting; ordered-oracle parity untested | Yes | Yes | Add/remove implemented; removal moves survivors | Shared progressive filter for both APIs | CPU implementation inspected; GPU NR | Level-major batches | Cumulative norms + active/distance buffers |

## Candidate-specific kill claims

| Candidate | Already known | Exact difference under test | Result that kills this claim |
|---|---|---|---|
| M1 | Blocked vertical/PAX organization and ordinary coalesced warp access | Sector-aware stage organization plus local row ownership would need **additional physical traffic** opportunity over the frozen warp-per-row store | <20% modeled removable traffic; or only a PDX/transpose GPU port. Layout-only does not change the survivor set |
| M2 | Compact coordinate intervals, lower-bound rejection and raw exact refinement | Only one concrete screen is inspected: 8-bit intervals on the original first256 coordinates. No distinct non-incremental principle is currently identified | Representation >25% raw or first-two-stage raw payload saving <50%; independently, a VA-file/BOND-style screen fails novelty admission even if bytes pass |
| M3 | Exact partial-distance kNN with a running k-th cutoff | Same raw store and progressive state with range's fixed cutoff replaced by exact kNN's threshold; no distinct algorithm beyond this substitution yet | Ideal coordinate saving <40%; independently, shared progressive range/kNN alone fails novelty admission |

### New material precedent found in the live source review

Faiss's pinned `IndexFlat.cpp` uses `flat_pano_search_core<false>` for kNN
and `<true>` for range. Both invoke `progressive_filter_batch` over the same
storage and state buffers; the threshold source changes. Thus “one progressive
primitive for both query types” already has an implemented precedent, not just
a possible extension of BOND. Its bounds/layout differ from our raw-coordinate
prototype; this is **not** evidence of equal latency, update cost or FP64 parity.

The three numeric cheap kills will still be recorded. A positive byte model
does not waive the four-part admission rule. No external/GPU implementation is
allowed without a surviving non-incremental distinction. No claim is made that
all future representations or GPU-native search abstractions are subsumed.
