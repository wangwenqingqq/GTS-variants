# Prior-art kill: lossless, progressive, exact, single-source dense-vector search

**Admission: DISTINCT_ENOUGH_TO_TEST, for one cheap CPU falsification only.**
This is not a novelty confirmation. No inspected primary work directly established
all five requested properties in dense FP32 exact-distance search. Lossless
bit decomposition and progressive query processing themselves are old. A positive
byte model would not establish a publishable contribution; the closest bit-split
ANN design is a substantial overlap, not a weak comparator to ignore.

Legend: `Yes` is within the source's stated scope, not our reproduction; `No`
means the described mechanism does not meet this property; `?` means not
established. Exact refers to the original dense-vector distance problem, unless
another domain is explicitly named. Single source may include residual layers,
but not a second full raw vector representation.

| Primary work | Lossless | Progressive | Exact | Single representation | Dense vectors | GPU | Boundary |
|---|---|---|---|---|---|---|---|
| [Zhang, memory-bandwidth ANN design (2025)](https://kdd2025.kdd.org/wp-content/uploads/2025/07/CameraReady-06.pdf) | Yes relative to stored bits | Yes | No deterministic guarantee | Yes, high bits + remainder | Yes | Proposed placement, not same-contract benchmark | Sections 3.1-3.2: expected-error/likely rejection, FP16 HNSW evaluation; no second raw copy is needed by its split storage. |
| [VA-file (1998)](https://www.vldb.org/conf/1998/p194.pdf) | No for approximation alone | Filter/refine | Yes with original objects | No | Yes | No | Section 4: cell interval lower bounds and original-vector refinement. |
| [BOND (2002)](https://www.cs.uoi.gr/~nikos/sigmod02.pdf) | Yes with lossless column storage | Dimensions | Yes | Yes | Yes | No | Sections 3-6 and 7.6: partial distances over decomposed dimensions; compression does not make it bit-prefix exact decoding. |
| [PDX (2025)](https://arxiv.org/html/2503.04422v1) | Yes, raw coordinate layout | Dimensions | Yes in exact mode | Yes | Yes | No | Sections 3-5/6.5: block-vertical coordinates and dimension pruning, not bit precision. |
| [3DPro (2022)](https://openproceedings.org/2022/conf/edbt/paper-24.pdf) | Reversible mesh refinement | Yes, mesh LODs | Yes for stated spatial predicates | Yes, mesh refinement stream | No, polyhedra | Yes, geometric acceleration | Sections 2-5: progressive conservative/progressive approximations; directly precedes the broad storage/execution abstraction in a different problem. |
| [Fout and Ma (2012)](https://vis.cs.ucdavis.edu/papers/Vis2012_compression.pdf) | Yes | Yes, precision | ? search not supplied | Yes | Floating volume arrays, not vector search | No | Progressive Precision section: partition floating bits for visualization/data access; no exact search predicate. |
| [zfp 1.0.1](https://zfp.readthedocs.io/en/release1.0.1/modes.html) and [algorithm](https://zfp.readthedocs.io/en/release1.0.1/algorithm.html) | Yes in reversible mode | Embedded coding | ? exact search not supplied | Yes | Numeric arrays | Other implementations exist; not tested | Coding/bit-exact recovery is not an exact-distance-search algorithm; do not conflate error-bounded and reversible modes. |
| [PRISM (2026)](https://github.com/hpdps-group/PRISM) | No, error-controlled lossy | Yes | No original-bit exact search supplied | Yes, one compressed file | Floating arrays | Yes | Official README: GPU progressive decompression with absolute/relative error controls; not lossless FP32 membership. |
| [BUFF (2021)](https://www.vldb.org/pvldb/vol14/p2586-liu.pdf) | Bounded precision, not arbitrary FP32 bits | Yes, byte subcolumns | Scalar filtering | Yes | Scalar columns | No | Sections 3.1/3.2/3.4.1: progressive filtering over decomposed bytes; exact general FP32 dense L2 is not established. |
| [QED/BSI (2018)](https://openproceedings.org/2018/conf/edbt/paper-185.pdf) | Fixed-point encoded attributes | Bit slices, not precision rejection | Different localized metric | Yes | Yes | No, distributed CPU | Section 3: query-dependent quantization/local similarity; not safe lower bounds for original FP32 squared L2. |
| [DistVS/PRESS (2026)](https://www.usenix.org/system/files/nsdi26-yin.pdf) | Exact SSD copy exists | Yes | ANN search | No, three precision copies | Yes | Not this GPU scan | Sections 3-4: low/high/exact representations across tiers, exact reranking from SSD. |
| [RCSI (2013)](https://www.vldb.org/pvldb/vol6/p1534-wandelt.pdf) | Yes | Not precision layers | Exact edit-distance matching | Referential representation | No, strings/genomes | No | Sections 3-4: compressed-domain exact matching, not dense floating L2. |
| [Herf FloatFlip (2001)](https://stereopsis.com/radix.html) | Yes, reversible bit permutation | Not a search algorithm | Not supplied | Yes | Individual FP numbers | Not relevant | Existing order-preserving sign transform; mapping is not claimed as new. |

## Closest overlap and kill boundary

The Zhang document explicitly splits full-precision numbers into high bits and
remaining bits to avoid duplicate full and reduced-precision copies. Calling all
bitplane ANN methods `code + raw` would be false. However, its Section 3.1 rejection
uses expected errors and highly-likely statements, not a deterministic enclosing
interval with zero false rejection. Its ANN-recall evidence does not qualify
original-FP32 exact range membership here. Publication venue metadata in the PDF
contains placeholders; no independently confirmed proceedings status is claimed.

3DPro already makes queries progressively decode a single compressed representation
until spatial decisions are known. Thus, `exact search as progressive decoding`
alone is too broad a novelty claim. The narrow dense FP32 bit-prefix/deterministic
bound conjunction has enough unresolved feasibility to admit the requested CPU
kill test, not an expensive campaign or paper claim. No external speedup, correctness,
or compression result is adopted as our evidence.

## Search coverage and limitations

Searches covered lossless compressed-domain distances, embedded/bitplane floating
coding, exact compressed representations, interval bounds, bitplane ANN,
compressed-domain matching, and GPU progressive decompression/search. Primary
byte identities are in [SOURCE_IDENTITIES.json](evidence/SOURCE_IDENTITIES.json).
HiPeR was a lead but no accessible full text was used as a decisive finding.
An exhaustive absence proof is impossible: any later directly matching dense-vector
work would reopen and kill admission. Composition of existing storage/bound
primitives, GPU porting, or small gains alone will not rescue a subsumed thesis.
