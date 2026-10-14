# Exact-safe sector certificates

The oracle remains the frozen original-coordinate ordered FP64 squared distance
on original FP32 inputs. Every coordinate term uses separate FP64 subtraction,
multiplication and RN addition with fast-math/FMA contraction/reassociation disabled.
The certificate accumulates a subset of the **same rounded nonnegative terms in
increasing original coordinate order**. Omitting nonnegative terms and monotonic
RN addition imply `partial <= full` by induction, without a tolerance. A strict
`partial > cutoff` rejects; equality survives. Priority scores never replace
coordinate terms in the certificate.

O2 first adds eight coordinate terms in original order to each sector score,
then selects the largest 16 rounded scores, ties by increasing sector ID. Sector
scores rank only: the certificate is recomputed from original coordinate terms,
not from a reordered sum of sector aggregates. Independent stable NumPy sorting
and ordered accumulations qualify all32 x first4096 pairs; the full population
verifies every frozen full-score bit and every bound.

Rounded sector ranking can differ from ideal real-term ranking at last bits.
The declared guard is `abs(partial-cutoff) <= 2*gamma_960*max(partial,cutoff)`,
`gamma_960=960*2^-53/(1-960*2^-53)`. It conservatively covers both short group
ranking sums and original-order certificate sums. There are **zero** guarded
pairs in the observed pool. No arbitrary-query/all-subsets optimality claim is
made, and nonzero ambiguity would stop UNCLASSIFIED rather than admit S1.

S1 reuses the unchanged FP32 moments. It computes FP64 coordinate moment scores,
adds each fixed group's eight scores in coordinate order, and stably chooses 16
sectors. IDs are sorted for certificate evaluation. Moment/priority rounding can
affect yield, not bound safety. Both populations use the same native binary.

The fallback byte model is deliberately separate from final numerical execution.
Appending remaining coordinates to an arbitrary-subset partial need not recover
original-order full-score bits. A bit-identical implementation needs retained
selected values/terms and original-order recomputation, or rereads. Neither the
fallback nor its retention/spill costs is implemented or claimed measured here.
