# Fixed32 mechanism result

**Fixed3 passes the diagnostic gate; shrinking the CTA alone does not show a
stable leaf-kernel win.** These are NSYS durations, not formal Host-ready ratios.

| Fixed32 NSYS round | G0 leaf total(ms) | G1 leaf total(ms) | G2 leaf total(ms) | G0/G1 | G1/G2 |
|---|---:|---:|---:|---:|---:|
| R1: G0,G1,G2 | 9989.709 | 9910.830 | 3312.641 | 1.00796 | 2.99182 |
| R2: G2,G1,G0 | 9747.200 | 9756.820 | 3305.688 | 0.99901 | 2.95152 |

All three count binaries produce **byte-identical per-node sidecars**. They
retain2,929,074 visited leaves,29,290,740 valid objects,29,290,708 distance-loop
objects,28,119,079,680 leaf dimensions and28,442,203,200 total distance dimensions.
Node tests/passes, entry bounds, original task order, participation/acceptance
masks and complete ID/distance results agree. Results also match the preceding
original-GTS baseline. Count-build and profiler times are excluded from formal
latency estimates.

| Runtime geometry, all32 queries | G0 | G1 | G2 |
|---|---:|---:|---:|
| Leaf kernel launches | 32 | 32 | 32 |
| Leaf CTAs | 2,929,074 | 2,929,074 | 976,369 |
| Threads/CTA | 512 | 32 | 32 |
| Configured warp slots | 46,865,184 | 2,929,074 | 976,369 |
| Warps with distance participants, source/mask-derived | 2,929,074 | 2,929,074 | 976,369 |
| Distance-lane fill in object-active warps | 31.24997% | 31.24997% | 93.74884% |

Every captured NSYS grid/block matches the corresponding recorded per-query
geometry. G2 contains976,347 full three-leaf groups,11 one-leaf tails and11
two-leaf tails. Distance participant counts per G2 warp are30 in976,315 groups,
29 in32 self-query groups,10 in11 tails and20 in11 tails. This is a static mapping
of recorded arithmetic participation, not a dynamic instruction or occupancy
measurement. The mechanism reduces CTAs, **not CUDA kernel launch count**.

G0/G1 selected leaf SASS is identical. G2 uses52 rather than48 registers; all
three retain47528 bytes of declared stack, no shared allocation and zero
ptxas-reported spill bytes. The declaration also covers the original multi-metric
kernel body; it is not measured L2-path local traffic. G2 introduces no extra
stack allocation, packing buffer or result-sort change.

NCU counter discovery failed with ERR_NVGPUCTRPERM before runtime collection.
No privilege or driver policy was changed. Issued warp/thread instructions,
DRAM/L2 bytes, coalescing counters, branch efficiency, hardware occupancy and
dynamic local traffic are **unavailable**. NSYS supplies kernel time, captured
launch geometry and launch resources, not those missing counters.

Gate E passes through unchanged work/results, clean qualification, matching
runtime geometry and lower G2 leaf duration in both orders. The evidence supports
testing packing's independent net benefit; it does not yet establish the public
Host-ready multiplier. G1's failure to improve both orders neither disproves
packing nor proves all oversized CTAs are free. Formal results use the separate
registered256-query,18-process campaign.
