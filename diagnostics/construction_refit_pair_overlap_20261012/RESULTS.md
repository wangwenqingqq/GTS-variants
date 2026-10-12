# Results

**Both rebuilds repeat every refit pair in construction scoring. The existing nominal values do not satisfy the frozen interval-refit contract, and scoring output is freed before refit.** No speedup was measured or predicted.

## A. Exact identity and task overlap

| Metric | R1 | R2 |
|---|---:|---:|
| Construction scoring tasks | 5,000,000 | 5,000,000 |
| Construction boundary tasks | 111,110 | 111,110 |
| Refit tasks | 5,000,000 | 5,000,000 |
| Construction scoring unique pairs | 4,999,800 | 4,999,800 |
| Refit unique pairs | 4,999,800 | 4,999,800 |
| Exact unique intersection | 4,999,800 | 4,999,800 |
| Intersection / refit unique | 100% | 100% |
| Intersection / scoring unique | 100% | 100% |
| Multiplicity-matched refit tasks | 5,000,000 | 5,000,000 |
| Task-level identity overlap | 100% | 100% |

C and R are equal **multisets**, not merely equal-size lists. For both rebuilds, 4,999,600 unique pairs occur once and 200 unique pairs occur twice. The exact pair-set hashes differ between R1 and R2; equal aggregate counts are not a reused result file.

## B. Numeric admission, not measured value equality

| Class / denominator | R1 | R2 |
|---|---:|---:|
| Identity overlap unique pairs | 4,999,800 | 4,999,800 |
| SAME_NUMERIC source contract | 0 | 0 |
| Optimistic CONVERTIBLE self-zero unique pairs | 11,109 | 11,109 |
| INCOMPATIBLE nonself source-contract pairs | 4,988,691 | 4,988,691 |
| Admission ceiling / refit unique pairs | 0.22218889% | 0.22218889% |
| Optimistic self-zero refit tasks | 11,111 | 11,111 |
| Admission ceiling / refit tasks | 0.22222% | 0.22222% |
| Measured per-pair bit-identical interval outputs | UNKNOWN | UNKNOWN |

Construction uses FP32 subtraction and nominal scalar distance, then encodes the FP64 sorting key; nodeSplit accumulates into FP32. Refit converts inputs to FP64 before subtraction and performs directed-rounding subtraction/multiplication/addition/sqrt to form two endpoints. Neither undoing scale/offset nor a scalar sqrt converts the legacy nominal output into the **same frozen interval endpoints**. The self-pair exception analytically derives `[0,0]`; it is generously included for admission, not an implemented reuse path.

The small percentage is a ceiling on **the currently source-contract-admitted categories plus the trivial-zero exception**, not a mathematical upper bound on all imaginable conversion algorithms, accidental equality, wider conservative bounds or a redesigned build-produced certificate. Per-pair refit intervals were not captured; only node extrema exist. Thus actual nonself value equality remains UNKNOWN, not measured 0%.

## C. Level alignment (identical counts in R1 and R2)

| Scoring level | Refit level | Scoring tasks | Refit tasks | Exact matched tasks | Refit fraction |
|---:|---:|---:|---:|---:|---:|
| 0 | 1 | 1,000,000 | 1,000,000 | 1,000,000 | 100% |
| 1 | 2 | 1,000,000 | 1,000,000 | 1,000,000 | 100% |
| 2 | 3 | 1,000,000 | 1,000,000 | 1,000,000 | 100% |
| 3 | 4 | 1,000,000 | 1,000,000 | 1,000,000 | 100% |
| 4 | 5 | 1,000,000 | 1,000,000 | 1,000,000 | 100% |

Root refit level 0 has zero distance tasks. A same-level-only comparison would incorrectly report zero across levels 1–4. The full matrix is in `summary/LEVEL_MATRIX.csv`: other than the five 1M aligned intersections, scoring L2/refit L5 and scoring L4/refit L3 each share 200 unique pairs; all other cells are zero.

## D. Ownership and stage provenance (each rebuild)

- Scoring–refit matched tasks: SAME_OWNER=0; DIFFERENT_OWNER=5,000,000. All 4,999,800 unique overlap pairs have only DIFFERENT_OWNER matches. The parent scores once, its ten children partition that membership and inherit that pivot; refit deposits extrema into those child owners.
- Boundary tasks: 111,110, unique pairs=111,108. All match refit pairs and all have SAME_OWNER destinations; multiplicity overlap=111,110/5,000,000=2.2222%.
- These boundary identities cover 111,128 refit task instances (2.22256%). This is **not** the number of available boundary producer instances: repeated refit identities account for the difference.
- Scoring identity covers every refit task; boundary is a subset. The combined unique intersection stays 4,999,800, not 5,110,908.

## E. Lifetime and pure capacity lower bounds (each rebuild)

`dis_list` is an N-entry FP64 sort workspace (8,000,000 bytes), reused/overwritten at each scoring level. It cannot hold all 5M historical results. It is freed at the end of indexConstru before numeric refresh starts. Scoring values currently survive to refit: **NO**. Boundary `TN.min_dis` persists: **YES**, but it is an incompatible nominal FP32 scalar.

| Hypothetical payload for 4,999,800 identity-overlap unique pairs | Bytes | Decimal MB |
|---|---:|---:|
| One FP32 nominal distance | 19,999,200 | 19.9992 |
| One FP64 nominal distance | 39,998,400 | 39.9984 |
| Two FP64 interval endpoints | 79,996,800 | 79.9968 |
| Separate two uint32 occurrence ID mapping | 39,998,400 | 39.9984 |
| Separate two uint64 occurrence ID mapping | 79,996,800 | 79.9968 |

These are theoretical payload-only capacity products, **not measured extra VRAM or a complete layout**. No cache, lookup structure, alignment, write traffic, metadata, synchronization or lifetime-management design was built. Identity headroom is not speedup headroom.

## The seven requested answers

1. Construction scores each active parent's captured member OID against its selected pivot OID and separately computes each sorted child boundary pair.
2. Refit visits each final valid nonroot node's membership against its inherited pivot OID.
3. Scoring and refit unique sets and multiplicities overlap 100%.
4. Both actual rebuild captures independently produce that result, under this one frozen shape/trace.
5. Existing nominal arithmetic/output is not the frozen directed-interval contract; actual per-pair equality is unknown.
6. Identity overlap spans every aligned scoring L/refit L+1 level. Boundary contributes no new pair identity, and ownership changes for all scoring–refit matches.
7. Identity headroom alone is large, but the declared combined gate fails numeric admission. **NO_GO_REUSE for existing nominal-output reuse; no automatic entry to a reuse prototype or performance campaign.** A changed arithmetic/certification path remains untested.
