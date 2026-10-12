# Evidence figure captions

1. **Local split choice does not meet the ancestor admission gate.** P0 is original
   GTS, P2 max-spread PCA-balanced, P3 all-eight oracle, P4 hard-six oracle. All
   use unchanged PCA8 / 64 B metadata. Alignment divides pruned objects by each
   partition's reaggregated truth-prunable objects, over 8M or 6M pairs. The
   60% guide is an ancestor promotion threshold only (L3/L4), additionally
   requiring 25 pp hard gain; L5 cannot independently promote. Complete frozen
   counts, no population CI or latency measurement.
2. **Hard queries improve unevenly and the hardest remains poorly covered.**
   Every one of the six preselected hard query IDs is shown, P2 versus P4, across
   L3/L4/L5. Each denominator is its own truth-prunable subset of 1M objects.
   Excluded easy queries are still reported in the full companion CSV: 90208
   regresses sharply at L3. These six improvements are not full-workload dominance.
3. **Many parents offer no immediate gain over their own S0 proposal.** CDFs
   include every parent producing L3/L4/L5 (100/1,000/10,000 per oracle). Regret
   is best immediate objective minus S0 on the same parent, normalized by QN:
   Q=8 for P3, Q=6 for P4, N=parent object count. Different oracle hierarchies have
   different parent memberships; this is not a P2-versus-oracle end-result gain.
4. **Axis choices dominate the selected IDs, but ties distort their frequencies.**
   All twelve proposal IDs remain in each panel: S0 max-spread, PC1..PC8 are
   S1..S8, Cyc=S9, Lex=S10, Rad=S11. Lowest-ID ties favor S0; duplicate proposals
   are retained, so zero selections of cyclic/lexicographic do not establish their
   intrinsic inferiority. All earlier construction levels are in the CSV. Gray
   with dots denotes P3; blue with hatching denotes P4, readable in grayscale.
