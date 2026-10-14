# Gate6 decision

## Q1: Sector-family oracle headroom

**STRONG_SECTOR_HEADROOM.** O2 total 484,008 / 32M pairs; mean **15,125.25**,
ratio **0.023122761393** to B0. Relative to Gate5's unconstrained O1 mean 2,574.0625,
sector grouping loses oracle information, but substantial headroom remains.
O2 reads every coordinate and selects per pair; its nominal 512B is not execution
cost or a bandwidth efficiency. No GPU or deployable-oracle claim.

## Q2: One query-only probe

S1 total **3,776,388**, mean **118,012.125**, ratio **0.180411312729** to B0.
Additional survivor reduction **81.9589%**; oracle headroom realization **83.8988%**.
It uses unchanged FP32 dataset moments and one stable top16 selection per query.
No per-object summaries, transformation or additional heuristic.

## Q3: Strong source-byte comparison

The conditional coordinate model sums to **28,951,819,264 B / all32 queries**,
mean **904,744,352 B**. Strong baseline sum is **32,474,520,832 B**, mean
**1,014,828,776 B**. Ratio **0.891524140226**, reduction **10.8476%**.
GO requires the exact integer comparison `5 x candidate_total <= 4 x baseline_total`:
mean <= **811,863,020.8 B**, equivalently survivors <= **46853597/520**.
S1 exceeds the GO byte ceiling by **92,881,331.2 B/query**. No rounded threshold
or switch to full scan is used. This model assumes retained selected coordinates;
retention/recomputation/spill and all execution overhead remain unknown.

## Q4: Query robustness

S1/B0 min **0.000001456579**, p10 **0.001632874492**, median **0.043850985462**,
p90 **0.494019725983**, max **1.0**. The exact linear p90 fraction is
`2998332287613/6069256205600`; it passes <=1/2. Queries 625378 and 72436 already
have one B0 survivor and cannot improve. No literal universal/per-query half-count
or cross-dataset claim is made.

## Q5: Separate dispositions

- **Implementation:** correctness-qualified CPU certificate reference only.
- **Diagnostic:** **CONDITIONAL_SECTOR_PROOF**; exactness and robustness pass,
  but the 20% source-byte margin fails.
- **Novelty:** dedicated audit **NOT_TRIGGERED**, verdict unavailable. Broad
  prior overlap was known at pre-experiment triage; no new mechanism is admitted.
- **GPU / NCU:** **NOT_RUN**. Gate7 is outside scope and not registered.
- **Keeper / manuscript:** untouched.

Stop. Keep the characterization and negative admission result. Do not add a
second score, alter 16-sector/32B geometry, reorder data or port to CUDA to rescue
this probe. Reopening requires an explicitly authorized distinct mechanism and
new frozen contract, not a favorable alternative denominator or rounded cutoff.
