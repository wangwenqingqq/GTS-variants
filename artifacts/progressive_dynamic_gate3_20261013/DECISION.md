# Decision: UNCLASSIFIED

## Q1: how much static range benefit survives A?

A-local complete range ACK speedup is **2.143573x**, reduction 53.35%. The prior static 2.255428x used a different 32-query pool; A has 128 range requests. A percentage of static gain retained would mix contracts and is not calculated. Service events + release improves 14.41%, below the frozen >=15% requirement.

## Q2: are updates still cheap?

For the 40-event insert and delete totals, D0/D1 medians are 0.556818/0.576951 ms and 0.303727/0.291951 ms. Ratios 1.036157/0.961227 do not trigger >1.5x regression. This is fixed-D, preallocated, bounded evidence, not constant-time asymptotic complexity or unlimited churn qualification.

## Q3: index, rebuild or heavy maintenance?

No D1-specific persistent O(ND) device representation, tree or rebuild. One unchanged raw vector buffer and native kNN norms coexist with borrowed progressive access and an extra 32,031,488 bytes of O(N) reusable query workspace. Both retain a CPU input copy and logical maps. Preallocation/setup and library reservations are not free; see memory accounting.

## Q4: update-heavy exactness and selectivity?

**Unknown: B was not admitted or executed.** A's diagnostic fixed32 pool passes all 128 checkpoint queries; maximum per-query prefix-survivor change is 0.0007 percentage points across initial/20I20D/40I40D/final. This is descriptive small-update evidence, not a B or long-workflow claim. No numerical stability cutoff was invented.

## Q5: gate classification and action?

| Priority/test | Result |
| --- | --- |
| Correctness/ownership/final-state failure | None observed within qualified scope |
| Insert or delete total ACK ratio >1.5 | No |
| Range ratio <=0.60 | Pass: 0.466510814 |
| Service ratio <=0.85 | **Fail: 0.855934141** |
| Paired primary CI upper <0.92 and >=5 wins | Pass: 0.857722127; 6/6 |
| Remaining NO_GO: service >=0.95 or range >0.75 | Neither |
| Uncovered interval | **UNCLASSIFIED, stop** |

Implementation is validated only for the declared bounded trace and fixture scopes. The progressive range mechanism retains a strong local ACK benefit. Full dynamic admission is withheld, and novelty remains ENGINEERING_ONLY. B, stages, mix, kNN, external comparisons, 100k events and large-scale matrices are not automatically pursued.

## Retained negative evidence and reopen condition

Keeper D0 and D1 were remeasured on the same GIST1M/D960 stream. D1 adds query workspace/compaction/control, cuts range ACK time, but unchanged kNN dominates the baseline and the primary ratio misses 0.85. This does not reject all progressive execution; it fails current workflow admission without resolving the declared gray interval. The broader complete-Host-release interpretation is additionally unvalidated, not inferred from this timer.

Do not revive this frozen candidate by resampling, picking another estimator, adjusting stages, changing query mix or modifying kNN. Reopening a paper direction requires a distinct non-incremental mechanism and decisive same-contract external evidence, separately authorized and preregistered; this artifact stays immutable.
