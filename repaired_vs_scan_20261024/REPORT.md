# Repaired GTS versus strong scan — measured campaign

**The repaired execution path is substantially faster than original A, but does
not beat strong exact scan on any of the 17 quality-valid workloads.** Words
R/S is 11.45–24.51; Tloc R/S is 2.75–4.00. All 17 paired 95% intervals stay
above 1 for R/S and below 1 for R/A. This is evidence for implementation-gap
analysis on that validated subset, not a competitive GPU metric-tree system.

**Material failure:** Tloc target1000 / Q1024 fails the frozen exact-ID contract
for A/R/S by one floating-point boundary hit. Its invalid arms have no promoted
timing or ratio. Native ArborX passes all nine Tloc workloads. The complete
18-workload all-gates acceptance criterion is therefore **not satisfied**; no
full-matrix attribution verdict is claimed. The low-dimensional close rule also
remains undecided: results versus native ArborX are mixed, and one R gate fails.
No radius, test ID, CPU oracle, tolerance or decision rule was changed.

## 1. Provenance, admission and denominator

- Continuation of frozen commit `a9bc1c783746e1dbfe0e618ba83a192514d9d822`,
  under [CONTRACT.md](CONTRACT.md) plus append-only [amendments](AMENDMENTS.md).
  CONTRACT.md remains SHA-256
  `26f23ae2f58de752487f7ed754ba1644cce5b609503c0a083375fc2a84bd8958`.
- Measured on 2026-10-25 UTC, physical GPU **5**, RTX PRO 6000 Blackwell sm_120,
  UUID `GPU-a1e0baba-3982-4538-6540-2b013a1adf49`, driver590.48.01,
  CUDA13.1.115. All arms in all six retained rounds used this same UUID.
  Per-device and task advisory locks held. No GPU settings changed and no foreign
  process was signaled. Admission, checks and before/after snapshots are retained.
- Completed epoch `quality_1792914941223955366`: 360 fresh timed processes,
  1080 retained bundle observations, six matched rounds; 17 valid A/R/S comparisons
  plus ArborX alone on the failed case. Earlier monitor/debug epochs have **zero
  formal timing directories** and remain archived, not spliced into this epoch.
  There was no observed foreign-application contamination in the retained epoch.
  Polling is a sampled monitor, not proof of absence between samples.
- **A is the pinned original `searchIndexRnnUpdate` path, with serial host
  bundling of Q batch-one calls. R is also serial Graph-query bundling. S and
  ArborX use native batched execution.** The native API `qnum` parameter does
  not establish complete-output Q1024 support. These A/R batch results are not
  the historical author-V2 native Q32 ≈237ms denominator; no old speedup was
  multiplied or old comparator timing reused.
- All eight original author source pins match. Original source/evidence is not
  edited; generated scratch copies add counters and the disclosed empty-query
  zero-CTA guard. R combines fixed workspace, stable fused result selection and
  projection, removal of redundant count stages, multi-CTA node traversal and
  Graph replay, without changing A's arithmetic or native ordered outputs.
  Optional high-dimensional leaf early stopping is not used for 2D Tloc.
- Strong S: Q*N flattened CUDA grid, exact rolling-row integer Levenshtein for
  Words and original float32 flat L2 for Tloc; native CUB stable flagged select,
  actual-count complete delivery. No tree, serial device Thrust count or forced
  serial baseline. This is a strong implemented baseline, not proof of the
  fastest possible scan implementation.
- Native X: user-local Kokkos4.7.04 CUDA+SERIAL / BLACKWELL120, ArborX commit
  `3a20eaba22bd8b6c13d6b32064a2086a3ce1c993`. Native double-geometry BVH range
  predicates on the original float32 coordinates, followed by float32 output
  distance projection; no handwritten proxy. Build logs, resources, binary and
  source hashes are in the evidence bundle.

## 2. Host-ready main result

Each ms value is the **median of six process medians of three retained complete
bundles**, not per-query time. Every bundle includes input submission, execution,
complete counts/IDs/distances D2H and common CPU ID canonicalization before timer
stop. Oracle checks and file I/O are outside retained timers. Build/setup,
capture/instantiate, first call and three warmups are separately recorded below.

Ratios are the frozen **paired geometric mean** of the six round-level ratios,
with Student-t log-space 95% intervals (df5). They need not equal the quotient of
displayed marginal medians. `CF` = measured correctness failure, **not zero or a
slow sample**; no A/R/S timed processes were admitted for that case. `—` = metric
not applicable. Target labels are calibration targets, not measured hit counts.

| Dataset | Target | Radius | Q | A ms | R ms | S ms | ArborX ms | R/S [95% CI] | R/A [95% CI] |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| words | 10 | 3 | 1 | 45.193 | 3.709 | 0.199 | — | 18.825 [18.088, 19.593] | 0.082 [0.076, 0.089] |
| words | 10 | 3 | 32 | 1032.220 | 93.553 | 8.080 | — | 11.446 [11.190, 11.708] | 0.091 [0.090, 0.091] |
| words | 10 | 3 | 1024 | 33992.010 | 3081.117 | 236.245 | — | 13.527 [12.233, 14.957] | 0.094 [0.086, 0.103] |
| words | 100 | 4 | 1 | 53.989 | 4.589 | 0.200 | — | 23.718 [21.919, 25.664] | 0.087 [0.078, 0.098] |
| words | 100 | 4 | 32 | 1299.069 | 131.007 | 8.515 | — | 15.477 [13.448, 17.812] | 0.101 [0.088, 0.117] |
| words | 100 | 4 | 1024 | 42878.326 | 4095.555 | 253.839 | — | 16.565 [15.945, 17.210] | 0.096 [0.090, 0.103] |
| words | 1000 | 6 | 1 | 57.922 | 9.321 | 0.326 | — | 24.506 [16.738, 35.877] | 0.155 [0.142, 0.168] |
| words | 1000 | 6 | 32 | 1712.135 | 242.255 | 12.407 | — | 18.653 [15.428, 22.553] | 0.145 [0.136, 0.153] |
| words | 1000 | 6 | 1024 | 56995.705 | 7034.618 | 507.632 | — | 13.506 [12.287, 14.847] | 0.125 [0.121, 0.129] |
| tloc | 10 | 0.053697448223800001 | 1 | 3.191 | 0.994 | 0.370 | 0.269 | 3.128 [2.253, 4.345] | 0.366 [0.265, 0.506] |
| tloc | 10 | 0.053697448223800001 | 32 | 114.115 | 31.550 | 10.913 | 1.089 | 3.180 [2.517, 4.017] | 0.304 [0.240, 0.385] |
| tloc | 10 | 0.053697448223800001 | 1024 | 3524.028 | 964.131 | 348.948 | 2.411 | 3.251 [2.346, 4.504] | 0.321 [0.234, 0.440] |
| tloc | 100 | 0.200301930308 | 1 | 3.166 | 1.582 | 0.370 | 0.378 | 3.833 [2.192, 6.700] | 0.451 [0.255, 0.800] |
| tloc | 100 | 0.200301930308 | 32 | 124.632 | 48.517 | 10.935 | 7.008 | 4.005 [2.929, 5.475] | 0.352 [0.256, 0.483] |
| tloc | 100 | 0.200301930308 | 1024 | 3872.538 | 976.891 | 349.853 | 26.209 | 3.019 [2.292, 3.976] | 0.272 [0.208, 0.356] |
| tloc | 1000 | 0.57966452837000004 | 1 | 3.254 | 0.976 | 0.372 | 0.787 | 2.754 [2.257, 3.361] | 0.318 [0.262, 0.385] |
| tloc | 1000 | 0.57966452837000004 | 32 | 139.714 | 35.059 | 11.177 | 46.362 | 3.529 [2.745, 4.538] | 0.286 [0.223, 0.367] |
| tloc | 1000 | 0.57966452837000004 | 1024 | CF | CF | CF | 205.286 | CF | CF |

Words uses all611,756 objects; Tloc uses all1,000,000 2D points. Calibration16 and
test1024 object IDs are disjoint; Q uses nested test prefixes. Frozen Words
radii3/4/6 produced calibration median hits17/124.5/4521.5; integer ties overshoot
1000 without retuning. Q1024 test medians are21/133.5/6126 (Words) and14/169/1343
(Tloc). Full counts, exact query IDs and manifests remain in the frozen evidence.
The workloads are in-dataset, self-inclusive queries, not held-out vectors.

### Native ArborX comparison and close-rule uncertainty

| Tloc target | Q | R/ArborX [95% CI] | >=5 point rule |
|---:|---:|---|---|
| 10 | 1 | 4.105 [3.384, 4.979] | no |
| 10 | 32 | 31.917 [25.301, 40.264] | yes |
| 10 | 1024 | 476.321 [340.958, 665.425] | yes |
| 100 | 1 | 3.677 [2.160, 6.259] | no |
| 100 | 32 | 6.251 [4.561, 8.568] | yes |
| 100 | 1024 | 40.510 [30.631, 53.575] | yes |
| 1000 | 1 | 1.295 [1.048, 1.600] | no |
| 1000 | 32 | 0.860 [0.665, 1.112] | no |
| 1000 | 1024 | CF | ineligible |

Four of eight valid Tloc cases have R/X>=5, but only three intervals lie wholly
above5; target100/Q32 crosses5. Target100/Q1 also crosses5 from below. At
target1000/Q32, R/X=0.860 with CI crossing1: no established win. Consequently
neither a blanket >=5 slowdown nor a reliable R advantage is justified. X's
Q1024 target1000 latency is valid independently, but cannot form an R/X ratio.

## 3. Correctness, sanitizer and stress gates

- Full data: 17 workloads pass complete exact ID/count and distance-tolerance
  comparison for every applicable arm. Full native ordered A/R binary outputs
  are byte-identical for **all18** workloads (including the shared failure).
  Native X passes all9 Tloc cases. Every retained first/warmup/measured output
  is rechecked outside the retained timer; count/hash alone is not a pass.
- **Failed frozen boundary:** query index585, query ID427451, object ID417457.
  CPU double distance0.5796645534324731 exceeds radius0.5796645283699036 by
  2.5062569575240445e-08. Original float32 A, faithful R and float32 S round this
  distance to the radius and include one extra ID. All other IDs agree. Double
  native ArborX excludes it. Keeping raw A's exact set and strict frozen CPU
  IDs is incompatible here. No common exactness adapter or semantic waiver was
  authorized/applied. Raw outputs and failure receipts are retained by SHA256;
  input coordinates are not published.
- **42 bounded sanitizer runs pass:** memcheck and synccheck for every
  metric/applicable arm, Q32/N2000 real-prefix data with empty, zero-radius and
  all-hit radii. `ERROR SUMMARY: 0 errors` and return0 are retained. These are
  bounded sanitizer gates, **not full-million-object sanitizer runs**.
- R passes64 changing-ID Graph replays per metric on the **full dataset**,
  Q32/target100 (first bundle plus one retained stress bundle).
  Full1024 distinct test IDs additionally pass on all eligible radii. Static
  compiler/resource reports are separate from correctness and host-ready timing;
  no new Nsight/SASS kernel-attribution measurement is claimed.
- Frozen dataset/oracle/calibration hashes and eight source pins are verified
  again after timing. Historical admission/Kokkos failures remain historical,
  not overwritten or represented as the current build state.

## 4. Separately instrumented work (never timed)

The following are **per complete Q-query bundle**. A and R have identical actual
node/leaf distance calls, DP-update cells/coordinates and candidate leaves.
Only scheduling/result/control work changes. Calls omit the explicitly skipped
L2 self-distance arithmetic. Active payload lanes can include self without an
arithmetic call. DP cells count inner updates, not row initialization.

`eff A/R/S` is active/total launched **payload** threads, in percent. R's denominator
includes inactive-capacity leaf CTAs; this is algorithmic utilization, **not SM
occupancy**. S's tail is also charged. `†` counts diagnostic wrong-output work,
not an eligible exact-query measurement. Full integer counters and statuses are
in WORK_COUNTS.json and RESULTS.json.

| Dataset | Target | Q | Calls A=R | Calls S | DP cells A=R / S (Words) or coordinates (Tloc) | Candidate leaves A=R | eff A / R / S (%) |
|---|---:|---:|---:|---:|---|---:|---|
| words | 10 | 1 | 573,550 | 611,756 | 44,175,000 / 50,477,240 | 78,178 | 1.19634 / 0.841749 / 99.9863 |
| words | 10 | 32 | 12,468,549 | 19,576,192 | 1,148,797,788 / 2,120,044,080 | 1,690,811 | 1.19699 / 0.56922 / 100 |
| words | 10 | 1024 | 418,321,003 | 626,438,144 | 41,304,568,123 / 67,538,547,120 | 56,597,037 | 1.19728 / 0.595568 / 100 |
| words | 100 | 1 | 693,951 | 611,756 | 57,553,256 / 50,477,240 | 95,520 | 1.19537 / 1.02764 / 99.9863 |
| words | 100 | 32 | 15,763,235 | 19,576,192 | 1,522,074,994 / 2,120,044,080 | 2,156,181 | 1.19626 / 0.725445 / 100 |
| words | 100 | 1024 | 533,300,402 | 626,438,144 | 54,337,558,428 / 67,538,547,120 | 72,820,073 | 1.19649 / 0.765776 / 100 |
| words | 1000 | 1 | 721,651 | 611,756 | 59,542,088 / 50,477,240 | 99,798 | 1.19488 / 1.07322 / 99.9863 |
| words | 1000 | 32 | 19,331,209 | 19,576,192 | 1,971,244,303 / 2,120,044,080 | 2,659,010 | 1.19565 / 0.894163 / 100 |
| words | 1000 | 1024 | 653,126,969 | 626,438,144 | 68,441,384,240 / 67,538,547,120 | 89,841,427 | 1.19563 / 0.944097 / 100 |
| tloc | 10 | 1 | 69 | 999,999 | 138 / 1,999,998 | 2 | 1.95312 / 3.51563e-05 / 99.9936 |
| tloc | 10 | 32 | 6,038 | 31,999,968 | 12,076 / 63,999,936 | 354 | 1.95312 / 0.000194458 / 100 |
| tloc | 10 | 1024 | 190,946 | 1,023,998,976 | 381,892 / 2,047,997,952 | 11,196 | 1.95312 / 0.000192192 / 100 |
| tloc | 100 | 1 | 199 | 999,999 | 398 / 1,999,998 | 11 | 1.95312 / 0.00019336 / 99.9936 |
| tloc | 100 | 32 | 25,508 | 31,999,968 | 51,016 / 63,999,936 | 1,940 | 1.95312 / 0.00106567 / 100 |
| tloc | 100 | 1024 | 885,996 | 1,023,998,976 | 1,771,992 / 2,047,997,952 | 69,095 | 1.95312 / 0.0011861 / 100 |
| tloc | 1000 | 1 | 759 | 999,999 | 1,518 / 1,999,998 | 61 | 1.95312 / 0.00107227 / 99.9936 |
| tloc | 1000 | 32 | 110,008 | 31,999,968 | 220,016 / 63,999,936 | 9,146 | 1.95312 / 0.00502405 / 100 |
| tloc† | 1000 | 1024 | 4,359,246 | 1,023,998,976 | 8,718,492 / 2,047,997,952 | 365,488 | 1.95312 / 0.00627402 / 100 |

Native ArborX getter instrumentation counts **primitive predicate tests**, including
native count/fill repeat traversals, not unique candidate points. Output float32
projection is separate; internal AABB tests are not counted as point distances.
A comparable launched-payload thread denominator is unavailable and left **null**.
Its work counters cannot be relabeled as the metric tree's leaf-CTA count.

| Tloc target | Q | Native primitive tests / candidate primitive leaves | Output projection distance calls | Coordinates evaluated | Effective threads |
|---:|---:|---:|---:|---:|---|
| 10 | 1 | 12 | 1 | 26 | unavailable |
| 10 | 32 | 1,724 | 641 | 4,730 | unavailable |
| 10 | 1024 | 60,624 | 22,805 | 166,858 | unavailable |
| 100 | 1 | 70 | 25 | 190 | unavailable |
| 100 | 32 | 17,194 | 7,903 | 50,194 | unavailable |
| 100 | 1024 | 660,292 | 307,650 | 1,935,884 | unavailable |
| 1000 | 1 | 284 | 121 | 810 | unavailable |
| 1000 | 32 | 119,192 | 58,036 | 354,456 | unavailable |
| 1000 | 1024 | 4,911,368 | 2,398,048 | 14,618,832 | unavailable |

**Mechanism implication (inference, not a new kernel profile):** R preserves A's
metric work but eliminates substantial execution overhead. It also preserves
full-table Words DP and poor leaf-lane packing. Fixed-capacity Graph copying and
grids are costly for sparse Tloc: actual R leaf payload fractions range from
0.0000352% to0.00502% on valid cases, versus A's1.953125%; S is >=99.986% on Words
and >=99.9936% on Tloc. These percentages are not a direct hardware occupancy or
latency decomposition. Source-derived R output capacity is17,777,764bytes/query
(2,222,220 slots plus count), ~18.2GB/Q1024 even for sparse outputs; this is a
capacity calculation, **not measured PCIe traffic**. Native S allocates17*Q*N
bytes plus CUB temporary/input storage, a substantial large-batch memory cost.

## 5. Excluded setup, first call and warmup

Across all timed processes for each arm, entries below are median [min,max] ms.
These aggregate different loads; per-load/per-process values remain in RESULTS.
R setup includes capture; its capture column is a **subset**, not additive.
First-call time excludes its later oracle check; `warmup` is the total wall time
of three full bundles **plus their out-of-timer oracle checks**. No setup value
is added to the warm steady-query ratios. Repeated-query use must amortize this
cost; a one-off built-from-scratch latency is not the reported denominator.

| Arm | Processes | Build | Setup | Graph capture/instantiate | First bundle | Three-warmup wall time |
|---|---:|---|---|---|---|---|
| A | 102 | 46.460 [38.113, 102.834] | 0.000 [0.000, 0.001] | 0.000 [0.000, 0.000] | 141.248 [5.561, 57847.509] | 419.912 [10.441, 173443.382] |
| R | 102 | 48.914 [37.802, 133.532] | 8.470 [7.276, 23.755] | 0.403 [0.327, 1.269] | 57.381 [0.870, 7308.215] | 166.435 [2.265, 22644.980] |
| S | 102 | 0.000 [0.000, 0.000] | 4.624 [3.734, 11.133] | 0.000 [0.000, 0.000] | 15.068 [2.731, 782.907] | 32.722 [0.596, 2522.409] |
| X | 54 | 1.591 [1.459, 2.472] | 0.123 [0.102, 0.230] | 0.000 [0.000, 0.000] | 8.257 [3.815, 248.349] | 7.591 [0.848, 678.470] |

## 6. Frozen decision and boundaries

| Frozen rule | Result | Decision / reopen condition |
|---|---|---|
| R/S<=1 across matrix and >=2x win somewhere, with gates | All17 valid R/S>1; one case CF | **No system-paper candidate evidence for this R.** Reopen only with a genuinely improved, oracle-valid implementation and fresh complete campaign; not multiplied old speedups. |
| R slower than S but substantially faster than A | Holds on17 valid cases: Words A/R6.47–12.21x, Tloc2.22–3.67x | **Subset evidence favors attribution/analysis.** Frozen protocol forbids a full-matrix classification while the required exactness gate fails. No new algorithmic novelty is established. |
| Tloc R/native ArborX>=5 on same contract | Mixed: four/eight valid points qualify, three CIs wholly>=5; one CF | **Undecided**, not blanket route closure. No proxy or extrapolation to invalid/other loads. |

This is an executed, evidence-complete accounting of the requested matrix,
**not a declaration that every acceptance criterion passed**. The unresolved
exact-ID failure blocks full-matrix acceptance; it is not resource unavailability
or evidence that metric trees are impossible. An authorized common boundary
adapter would be a separate amendment and implementation, followed by a fresh
complete paired campaign, not radius tuning or replacing one failed sample.

Other limits: no optional Deep1M run; original/native repaired Q1024 batching
not established (serial bundles are disclosed); shared host, unlocked clocks,
sampled foreign-process monitoring and six pairs yield broad low-dimensional
intervals. CIs are pointwise, not simultaneous familywise intervals. No per-fix
factorial attribution, all-data sanitizer, controlled-frequency campaign or
new kernel-time breakdown was performed. This report supports neither a
universal best-scan claim nor a universal low-/high-dimensional tree conclusion.

## 7. Durable evidence and reproduction

- [Machine-readable18 cases, all process medians/ratios/order splits](RESULTS.json)
- [Raw1080 retained samples](evidence/measured_20261025/raw_samples.csv)
- [Compressed normalized process evidence](evidence/measured_20261025/PROCESS_EVIDENCE.json.gz):
  530 receipts, logs and admission/live/after snapshots (full/gates/count/stress/timing).
- [Full quality](evidence/measured_20261025/FULL_QUALITY.json),
  [exact failure](evidence/measured_20261025/EXACTNESS_FAILURE.json),
  [sanitizers](evidence/measured_20261025/SANITIZERS.json),
  [work counters](evidence/measured_20261025/WORK_COUNTS.json).
- [Binary/source/build provenance](evidence/measured_20261025/BUILD_PROVENANCE.json),
  [successful and failed build logs](evidence/measured_20261025/BUILD_LOGS.json.gz),
  [end-of-campaign frozen hashes](evidence/measured_20261025/FROZEN_INPUTS_END.json),
  [retained earlier attempts](evidence/measured_20261025/RETAINED_ATTEMPTS.json).
- [Raw-file hash/size manifest](evidence/measured_20261025/RAW_MANIFEST.json).
  Large full output/oracle/data files remain outside Git in retained task scratch;
  paths are relative to that scratch, contents identified by SHA256. Commands
  are normalized to `${TASK_SCRATCH}`; raw receipts retain their original hashes.
  Input datasets, raw coordinates and device connection configuration are not published.
  CSV line endings and resource-report whitespace are normalized only;
  PUBLICATION_NORMALIZATION.json records original/published hashes (values unchanged).
- [Implementation card](DESIGN.md), [append-only experiment/claim ledger](EXPERIMENTS.md),
  [reproduction commands](README.md). `python3 verify_evidence.py` independently
  recomputes every displayed estimator from raw CSV and checks quality/schedule,
  receipt/GPU identity, sanitizer outcomes and frozen hashes without a GPU.

Branch: `experiments/repaired-gts-vs-scan-20261024` in
[wangwenqingqq/GTS-variants](https://github.com/wangwenqingqq/GTS-variants).
No main merge, original-source edit or paper rewrite is part of this experiment.
