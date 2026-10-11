# Fixed3 current-P design card

Target: RTX PRO6000 Server, sm_120, FP32 row-major data and query. Native
compute is scalar ordered FP64 distance, not tensor MMA. Hypothesis: remove
overlarge/underfilled leaf execution groups. This is not an occupancy forecast.

| Phase | Roles / state | Readiness and last use |
|---|---|---|
| list decode | uniform CTA checks up to 3 canonical entries | guarded list reads; uniform all-inactive return |
| query load | all 32 lanes; 960-float shared array | all writes -> one unconditional CTA barrier |
| distance | lanes 0..29: leaf=lane/10, j=lane%10 then j+=10 | query read-only until kernel exit; local FP64 sum per object |
| output | same distance owner writes original hit/field slot | one writer per slot; no shared top-k or reduction |
| collect | unchanged N-sized host reduce/scan + GPU collect | existing synchronization before host-ready output |

P0/P1 share the same 3840-byte query staging. P2 intrinsically loads one query
per active GROUP, not per leaf; this priced staging reduction belongs to the
execution-mapping change, not an independent pivot cache. Object row layout is
unchanged. Partial/inactive groups may lower effective lane fill. No persistent
reuse, overwrite, cross-warp transfer, pipeline stages, clusters or Graph.

Expected live peak: per-lane node/index, address, FP64 sum/delta and query pointer;
no arrays in registers. Shared query lifetime ends at CTA exit. No second barrier
is required because nothing overwrites it. Startup/tail use the same mapping.
Static gate: production leaf functions must have zero stack/spills/local traffic;
shared <=3840 bytes, no register cap. Freeze measured ptxas/SASS resources before
GPU qualification. Compilation and SASS are not runtime or timing gates.

Useful-work ledger: exact node/pivot/leaf/object counter arrays must match.
Movement ledger: source-predicted query staging reduction only; actual DRAM/L2
unknown unless NCU counters admitted. Control ledger: actual grid/CTA counts in
NSYS, unchanged launches; one barrier/active group. No instruction or hardware
occupancy inference from lane mapping.

Reject at first semantic/sanitizer/isolation failure. Formal promotion requires
Gate E and the complete current-P workflow criterion in CONTRACT.json. A local
leaf win alone does not close the current-P external-baseline gap.
