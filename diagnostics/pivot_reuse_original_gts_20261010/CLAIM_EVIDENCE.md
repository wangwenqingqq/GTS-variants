# Claim-evidence checkpoint

Experiment: `gts_20261010_pivot_reuse_original_knn`. Exact contract and frozen
identities: `CONTRACT.json`, `SOURCE_PINS.json`, `QUERY_SCOPE.json`.

| ID | Claim and scope | State | Evidence | Counterevidence / allowed wording |
|---|---|---|---|---|
| C1 | Original sibling-pivot sharing and encountered-pivot upper-bound use exist | measured (source audit) | BASELINE_AUDIT, eight source pins | G2/G3 are not independent new mechanisms; do not claim their novelty |
| C2 | G1 reduces distance arithmetic 1.068666579% on fixed32 | measured | WORK_COUNTS, final guarded diagnostic receipt hashes | No visits decrease; not whole-program work or a latency bound |
| C3 | G1 preserves admitted fixed32/synthetic complete results and new-cache sanitizer gates | measured within admitted scope | VALIDATION | Full-tree N<K/long-unfilled/last-branch gates incomplete; no universal exactness claim |
| C4 | G1 has a complete 256-query host-ready net advantage | unknown | Confirmation collecting; no complete formal gate yet | Six paired processes required; no claim from partial/favorable rows |
| C5 | Cache management may offset the small arithmetic savings | unknown | Static added operations and payloads; net timing pending | Plausible competing explanation, not established CPU/DRAM attribution |

Implementation status: built and qualified for sequential B1 with the immutable
admitted index. Mechanism status: repetition measured and removed; complete net
cost pending. Thesis impact: no novelty or external competitiveness established.
