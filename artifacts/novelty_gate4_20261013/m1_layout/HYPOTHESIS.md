# M1 — transaction-aligned progressive physical organization

Hypothesis: changing only the physical organization can remove at least20% of
current progressive traffic while preserving the raw FP32 store, frozen four
checkpoints, survivor sets, B1 request order and local update ownership.

Roles in the keeper: one warp owns one row; lanes load consecutive coordinates;
lane0 owns the partial sum/ID; CUB retains16-byte states; the Host waits for each
stage's active count. Every row stride is3840B and each stage begins on a128B
boundary. An update writes/copies a whole960-coordinate row. No new representation,
cross-query batching, changed stage, changed threshold or compaction tuning is
admitted. The candidate is a physical-traffic hypothesis, not an implementation.

Prior-art distinction must be more than blocked transposition (see matrix M1).
Expected saving is sector overfetch; added costs would be layout conversion,
scattered updates/ownership metadata, and possibly an additional raw copy.
No such added cost is waived. Readiness/count waits and ordered refinement remain.

Reopen only for a different, explicitly registered access geometry or a directly
observed >=20% removable physical-traffic component. This test cannot rule out
latency changes from cache scheduling that do not remove bytes.
