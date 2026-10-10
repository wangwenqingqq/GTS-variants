# Figure semantics

All curves show exact arithmetic means over the frozen 32 queries, not repeated
process timing. No confidence intervals are invented. Numeric distributions are
retained per query in JSON. Figures are authored at 7.2-inch full-paper width;
vector PDFs and 300-DPI PNGs are generated from the adjacent CSVs.

1. `pruning_power_curve`: Global pivot bands are far less selective than oracle;
   the horizontal tree-candidate line counts the same layout's original candidates.
2. `oracle_gap`: Most surviving blocks contain no range hit even at eight pivots.
3. `pruning_vs_update`: Local writes do not solve weak query filtering. All points
   recompute post-update survival for their actual slack packing; intervals have
   different true I/D counts. Marker size grows with P=1/2/4/8, shape encodes slack,
   facets encode layout, color/fill encodes pivot strategy; all three strategies are retained, coincident points are
   not jittered. Results are counts/models, not GPU speed or traffic.
