# Initial-only PCA qualification and paid resources

One deterministic streaming FP64 mean/covariance construction over all 1M initial vectors. No sampling, randomized solver, rebuilt refit, query-selection or oracle tuning. Some dataset rows later serve as fixed query fixtures; they participate only as ordinary training objects, not using their query roles. Covariance/eigenvector determinism is scoped to the retained backend and chunk/thread settings; cross-library bit equality is not promised.

| Field | Value |
| --- | --- |
| PCA wall seconds (one construction + qualification) | 9.543945293 |
| Process CPU seconds | 31.575067 |
| Explicit covariance-chunk live arrays peak (bytes) | 77667840 |
| Process peak RSS incl mapped input/runtime (bytes) | 3959263232 |
| Pre-PCA process peak RSS (bytes) | 53350400 |
| Direction matrix (bytes) | 30720 |
| Top-four covariance variance fraction | 0.379291519 |
| Relative eigen residual | 3.01518e-16 |
| Exact-Gram infinity deviation upper | 2.46182e-15 |
| Represented projection norm squared upper A2 | 1.0000000000000018 |

Time includes two full input passes, covariance, two eigh/sign/Gram qualifications. It excludes earlier registration/build/test/input hashing. Input validation has already read the data, so this is not a cold-start full index build. RSS includes mapped input pages; it is not temporary-array size. The explicit chunk-array account excludes BLAS/LAPACK/runtime internal allocation; both measures are retained rather than conflated. No query time is collected.

Top five covariance eigenvalues: 0.401829411009, 0.150031591024, 0.1342628568, 0.0749524077623, 0.0601944866477. The top-four variance fraction alone does not identify which omitted directions determine range separation or prove a universal anisotropy explanation. Directions, signs and exact represented Gram bounds are retained in JSON. Actual native-library hashes/configuration and actual OpenBLAS threads=4 are retained in evidence/REGISTERED.json.
