# Claim-evidence checkpoint

Experiment: `gts_20261010_pivot_reuse_original_knn`. Exact contract and frozen
identities: `CONTRACT.json`, `SOURCE_PINS.json`, `QUERY_SCOPE.json`.

| ID | Claim and scope | State | Evidence | Counterevidence / allowed wording |
|---|---|---|---|---|
| C1 | Original sibling-pivot sharing and encountered-pivot upper-bound use exist | measured (source audit) | BASELINE_AUDIT, eight source pins | G2/G3 are not independent new mechanisms; do not claim their novelty |
| C2 | G1 reduces distance arithmetic 1.068666579% on fixed32 | measured | WORK_COUNTS, final guarded diagnostic receipt hashes | No visits decrease; not whole-program work or a latency bound |
| C3 | G1 preserves admitted fixed32, twelve full256-query processes, seven-K synthetic/last-allocated-leaf results and cache sanitizer gates | measured within admitted scope | VALIDATION, BOUNDARY_RESULT | Full-tree N<K and arbitrary long-unfilled/visit-order trees remain uncertified; no universal exactness claim |
| C4 | G1 has a complete256-query host-ready net advantage | inconclusive | SUMMARY, FORMAL_ROUNDS, four complete gates | Paired1.003294 [0.998207,1.009474],4/6 wins; no additional round or promotion |
| C5 | Cache management may offset the small arithmetic savings | unknown | Source costs and PROFILE_RESULT | Added64 malloc/64 free/32 memset calls on32 queries; no isolated causal overhead/CPU-arithmetic attribution |
| C6 | Thread-level saved arithmetic need not skip the leaf's complete warp loop | inferred | WARP_REUSE_SCREEN and unchanged original leaf mapping | Every leaf has10 objects and at most2 evaluated pivots; at least7 noncached nonself lanes remain. Not a dynamic SASS count |
| C7 | The captured fixed32 GIST1M query pass has high temporal GPU coverage and is leaf dominated | measured | PROFILE_RESULT | GPU coverage96.782%/96.871%, leaf about88.9% of Host range; not SM utilization, not a formal profiler speed ratio |

Implementation status: fixed admitted static B1 checks pass; broader qualification
is partial. Mechanism status: repetition measured and removed, complete net benefit
inconclusive. Keep G0; do not promote G1. Thesis impact: no novelty, external
competitiveness or update benefit established. Reopen only under a preregistered
regime with whole-SIMD elimination or substantially more repetition, full cost,
exact outputs and all required support gates. Last live verification:2026-10-10.
