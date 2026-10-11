# Fixed3 claim-evidence ledger

Experiment `gts_20261011_fixed3_leaf_packing`, registered and last verified 2026-10-11.

| Claim | Final evidence state | Denominator / evidence | Claim boundary |
|---|---|---|---|
| G1 isolates leaf CTA shrink | measured, static/control scope | RESOURCE_GATE: identical selected leaf SASS and distance/output code, changed leaf blockDim only | Source/resources alone are not a speed claim |
| G2 preserves useful distance/search work | measured | WORK_COUNTS: byte-identical fixed 32 per-node sidecars, full results and independent oracle | Diagnostic fixed 32 scope, no universal traversal theorem |
| G2 reduces actual leaf CTA count | measured | NSYS: 2,929,074 to 976,369 CTAs, still 32 leaf launches; joined to recorded leaf sequence | Runtime launch geometry, not issued-instruction counter |
| G2 leaf execution is faster than G1 | measured | Reverse NSYS rounds: 2.99182x and 2.95152x on the same 32 queries | Diagnostic profiler denominator only |
| G2 improves complete Host-ready time over G1 | measured | SUMMARY: 2.543937x [2.541211, 2.545909], 6/6 wins, 18 total fresh processes | Original GTS, reused fixed 256 GIST query set only |
| G2 improves complete Host-ready time over G0 | measured | SUMMARY: 2.561733x [2.556026, 2.570420], 6/6 wins | Not current GTSPP or external superiority |
| G1 supplies the dominant gain | rejected | G0/G1 formal 1.006995x [1.005330, 1.009733]; leaf benefit not stable in both NSYS orders | Small formal net win is real within this contract, not the packing explanation |
| Fixed3 is novel or improves current GTSPP | rejected / unknown | Generic packing novelty rejected; no current-GTSPP experiment | Do not claim either from this experiment |

NCU hardware counters are unavailable under the measured account permission.
Do not substitute static instruction counts or launch geometry for DRAM/L2,
issued warp/thread instructions, dynamic spill traffic or hardware occupancy.
