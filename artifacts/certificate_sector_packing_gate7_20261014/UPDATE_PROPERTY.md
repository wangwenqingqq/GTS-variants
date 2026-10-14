# Fixed-permutation update property (structural only)

For an insertion, apply the frozen pi to the incoming 960D FP32 vector before
appending its row to the packed dense store. Apply the same fixed permutation to
future queries. No online packing retraining or per-object metadata is introduced.

Deletion retains the dense store's existing row-occurrence/identity semantics;
removing or moving a whole row does not alter its coordinate permutation. A swap
delete would still need the existing logical-ID-to-row bookkeeping. This artifact
does not implement, validate or time that path, or claim improved update ACKs.

The update workload and distribution drift are NOT_TESTED. The current keeper's
insert/delete implementation is unchanged. Packing provenance describes the
initial frozen corpus only; the numerical diagnostic provides no dynamic
correctness, persistence or retraining claim.
