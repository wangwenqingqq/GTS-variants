# Gate 0: diagnostic, not a novelty claim

Checked before measurement on 2026-10-12. The nearest established mechanisms
already include conservative coordinate approximations and exact lower-bound
filters. PCA followed by an outward low-bit box is not claimed as novel. This
cheap diagnostic may proceed; algorithm novelty and GPU advantage remain unknown.

| Required topic | Primary source and relevant boundary |
|---|---|
| VA-file | [Weber, Schek, Blott, VLDB1998](https://www.vldb.org/conf/1998/p194.pdf): compact coordinate approximations filter candidates before refinement. |
| Scalar quantization exact filtering | Same VA-file paper: coordinate-cell bounds are established; conservative intervals are not a new mechanism. |
| Product quantization exact lower bounds | [Product Quantized Translation, AAAI2018](https://cdn.aaai.org/ojs/11752/11752-13-15280-1-2-20201228.pdf): exact Euclidean search uses translated mean/variance lower bounds. Standard approximate PQ distances are not automatically safe. |
| Compressed bounding boxes | [Ylitie et al., HPG2017](https://research.nvidia.com/sites/default/files/publications/ylitie2017hpg-paper.pdf): compressed wide BVHs establish conservative box compression; 3D ray traversal is not this high-dimensional search contract. |
| High-dimensional spatial indexes | VA-file analysis discusses high-dimensional degeneration under stated distribution assumptions; it is not a universal impossibility theorem for these GIST regions. |
| Quantized region summaries | Compressed BVHs establish this general mechanism. This experiment tests its measured retention in frozen PCA-balanced regions, not invention of summaries. |
| Certified sketches | [Higuchi et al., ICPRAM2018](https://www.scitepress.org/PublishedPapers/2018/65850/): publisher abstract describes sketch-derived lower bounds; full safety scope not inferred from the abstract. [RaBitQ](https://arxiv.org/abs/2405.12497) concerns ANN error bounds, not this deterministic all-region exact-prune contract. |
| Compressed exact nearest-neighbor filters | VA-file and Product Quantized Translation are direct prior mechanisms. A future block-energy/moment direction must first survive comparison with the latter. |

Source access: VA-file indexed primary text, AAAI and HPG full primary papers,
ICPRAM publisher abstract, and RaBitQ author abstract. No claim that this is an
exhaustive literature survey. No copyrighted paper files are redistributed.
