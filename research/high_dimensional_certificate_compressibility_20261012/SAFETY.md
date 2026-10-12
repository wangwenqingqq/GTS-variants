# Numerical and validation contract

The full stored basis, projected cache, permutation, queries, original scores and
cutoffs are pinned to the preceding campaign. No transformation is fitted here.
The preceding directed Gram proof establishes contraction of the full stored
basis; its prefix rows are contractive. Its arithmetic proof bounds cached
coordinate errors by ETA=1e-8 and distance arithmetic by the common margin
0.00010061967733539321. Those proofs and sources are frozen dependencies.

Each FP32 box encloses the cached coordinate interval [z-ETA,z+ETA] outward.
The query interval is also widened by ETA. Each positive interval gap, its square,
ordered nonnegative prefix sum and square root is rounded down. The sum is kept
nondecreasing when adding zero, without exceeding the exact nonnegative sum.
Subtracting the inherited margin again is intentionally conservative: coordinate
uncertainty is partly counted twice, but the comparison retains the same keeper
and an explicit point-set-safe-lower dominance check. It is not a tightness claim.

G1 explicitly checks128D coverage for all3M object memberships.32/64D files are
exact prefix slices, proving all9M prefix memberships; report768M physical endpoint
coordinate comparisons, not a fictitious larger physical count. Nine real binary
record files are roundtripped, each little-endian interleaved FP32 lo/hi.
G2 compares every AABB lower against the matching inherited safe point-set lower
and original truth norm (2,664,000 query-prefix-region cells). The point-set *raw*
RN norm is not declared inherently <=original norm; it needs the proven envelope.
G3 additionally tests the strict original squared-score truth, not just sqrt(U).
G4 exact72 keeper counts, original truth arrays and U* must match.
G5 is conditional: outward rounding of independent formats does not guarantee
nesting. Any admitted quantizer must enclose its preceding decoded format and
validate mask subsets; with only FP32 it is N/A, not a quantization PASS.

An extra independent replay uses all members of24 preregistered original regions
and72 prefixes. Ordered original-vector projection must lie within the boxes;
all original scores, cached-input endpoints and scalar directed bounds are
checked. Cached versus ordered projection need not be bit-identical; both share
the proof envelope. This subset replay does not replace exhaustive G1-G4.

No finite experiment proves universal data/queries safety independently of the
numerical premises. No latency, GPU utilization or general-tree performance claim
is admitted. All costs are logical standalone scan proxies, never actual traffic.
