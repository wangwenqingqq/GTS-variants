# Exact-safe coordinate certificates

The service oracle is the existing original-coordinate, round-to-nearest FP64
sum of squared differences between original FP32 values. We neither change its
cutoff nor substitute a transformed, approximate or mixed-precision metric.

For every admitted pair, let `t_j` be the same rounded nonnegative squared
coordinate difference used in that full score. Any selected subset is accumulated
in **increasing original dimension index**, not in score/contribution order.
At each original index, its accumulator is no larger than the full accumulator:
omitting a nonnegative term cannot increase a sum, and RN addition is monotone.
Induction therefore gives `partial <= frozen_full` without a tolerance. We reject
only `partial > cutoff`; equality survives. The score chooses coordinates but
never substitutes estimated contributions into a certificate.

Native compilation disables fast-math, FMA contraction and reassociation.
Finite-value admission, signed zero, subnormal, extreme finite, duplicates,
equal-contribution ties and invalid indices are qualified. Both 32M-pair populations
also verify every emitted partial against the unchanged full-score files. These
are certificate validations, not complete-search-result or GPU legality tests.

B0 adds dimensions 0..127. O1 uses native `nth_element` on the 960 rounded terms,
chooses the largest 128 (ties by original index), and then sums the chosen terms
in original order. An independent NumPy stable sort verifies the selection and
ordered bit results on all 32 x first4096 qualification pairs. O1 maximizes the
unrounded sum of these fixed nonnegative terms; rounded accumulation of competing
subsets can differ at the last bits. Its numerical boundary guard checks
`|partial-cutoff| <= gamma_960*max(partial,cutoff)`, with `u=2^-53` and
`gamma_960=960*u/(1-960*u)`. **Zero** full-population pairs fall in that uncertainty
region, so no observed oracle classification depends on a last-bit order choice.
No all-subsets or arbitrary-query numerical optimality claim is made.

C1 computes deterministic, full-population FP64 moments in 8192-row chunks and
a second variance pass, then persists FP32 mean/variance arrays. Query scores are
FP64 calculations over those FP32 arrays. Stable descending score order breaks
ties by dimension index; the selected set is sorted back to original index order
for certificate evaluation. Rounding moments can affect priority, not safety.
