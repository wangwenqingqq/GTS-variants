# Gate 0: diagnosis admitted; novelty not admitted
Verified 2026-10-12 using primary sources.

| Prior art | Existing mechanism / setting | Boundary |
|---|---|---|
| [Faloutsos, Ranganathan, Manolopoulos, Fast Subsequence Matching, SIGMOD 1994](https://hdl.handle.net/1903/604) | Feature-space rectangle indexing and refinement for time-series matching | Lower-dimensional filter/refine is old; a different dataset is not a new mechanism |
| [Micó, Oncina, Vidal, LAESA, 1994](https://www.sciencedirect.com/science/article/pii/0167865594900957) | Reference-based nearest-neighbor approximating/eliminating search, linear preprocessing and memory | Multiple exact metric filters are not a new general idea; publisher search abstract/metadata checked, full text returned 403 |
| [Singleton indexes for nearest neighbor search, Information Systems 2016](https://www.sciencedirect.com/science/article/abs/pii/S0306437916300825) | Space-budgeted metric indexes built from standard discarding rules, adding pivots/hyperplanes/centroids and greedily tuning on a query sample | Budget-aware combinations and query-driven greedy filtering are established; this diagnostic instead freezes query-independent directions |
| [Yan et al., rpForests, IEEE Big Data 2018](https://arxiv.org/abs/1812.11689) | Ensembles of random-projection trees, missing-rate and distance-discrepancy analysis | Direction-diverse ensembles precede this test; approximate retrieval does not replace zero-false-prune certification |

## Cheap analytic kill test
For a fixed jointly contractive eight-row basis, concatenate all coordinate box gaps into g. For any partition into subsets G_v:

`max_v ||g[G_v]||_2 <= ||g||_2`.

Splitting a fixed PCA8 certificate into max-composed blocks therefore cannot strengthen its exact gap. D1 duplicates blocks; interleaving PC1..8 also loses joint energy. Conservative implemented arithmetic is separately tested rather than assumed to preserve every exact inequality.

Spread32 changes directions; old-PCA8 dominance is not assumed for it. The selected eight-row basis is jointly certified, but this plan tests only max, not an unrequested summed variant. Independent random views need not be jointly contractive; an energy sum there requires another proof.

## Admission
Proceed only as the requested small CPU diagnosis under a fixed budget. No novelty claim for safe-filter max composition, multiple directions, PCA boxes or ensembles. A positive count result would still need a non-incremental mechanism, decisive external same-contract comparison and held-out evidence before becoming a thesis. This negative closes only the frozen finite family.
