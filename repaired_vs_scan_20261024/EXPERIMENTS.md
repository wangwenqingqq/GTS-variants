# Experiment ledger

| Experiment | Hypothesis | Contract | Keeper/candidate | Expected delta | Invariants | Raw evidence | Decision |
|---|---|---|---|---|---|---|---|
| gts_20261024_repaired_host_ready | Combined execution repairs remove the original implementation gap versus exact scan | CONTRACT.md v1 | A / coupled R; S external comparator | Fewer scalar counts/launches; traversal parallelism; same distances | Complete ordered A/R output, CPU oracle | pending | designed |

No new algorithmic novelty is claimed. The cheap kill test is the required
same-contract R/S comparison itself; a new paper thesis remains gated on prior art.

| Claim | Scope | State | Evidence | Allowed wording |
|---|---|---|---|---|
| R is competitive with S | Required 18-workload matrix | unknown | no evidence | Not established |
| R improves A | Same GPU/driver and host-ready output | unknown | no evidence | Not established in this campaign |
| Low-dimensional route should close | Tloc native ArborX | unknown | no evidence | Undecided |

## 2026-10-25 UTC — resource-admission stop

- Implementation state: CPU tools prepared/tested; combined R/native batch S and
  GPU campaign runner not assembled or built in this attempt.
- Mechanism state: unknown; no GPU work or timing observations.
- Thesis impact: undecided, including the low-dimensional close rule.
- Resource evidence: foreign GPU-0 VLLM process observed/confirmed before GPU
  launch; later idle diagnostic retained without restarting the stopped attempt.
- Native ArborX state: native CMake configure failed to locate Kokkos >=4.5;
  no dependency installed and no proxy used.
- Contract: CONTRACT.md plus the pre-GPU batching correction in AMENDMENTS.md.
- CPU evidence: both complete input hashes and all eight author source pins
  match; disjoint calibration/test IDs and frozen radii; full CPU oracle files
  retained outside Git with hashes and all 18 workload output-size summaries.
- Raw paths: task-local private artifacts and matching remote task scratch.
  Curated evidence: evidence/GPU_ADMISSION.json, evidence/CPU_ORACLE.json,
  evidence/ARBORX.json and evidence/VALIDATION.json.
- Decision: incomplete/resource-stopped, not a rejected metric-tree mechanism.
- Reopen condition: a separate complete attempt with explicit restart decision,
  fresh idle/lock admission, composed R, native-batch S, and all declared gates.
  Never splice old/contaminated observations or infer missing ratios/counters.

## 2026-10-25 UTC — composed CUDA and native-library correctness gate

- Re-admitted physical GPU 5 under the existing device lock. No settings changed.
- Composed A/R/native-batch S compile; user-local Kokkos 4.7.04 CUDA/sm_120 and
  native ArborX compile. The old no-Kokkos failure is historical, not current.
- Monitor diagnostic revisions retain trailing NVML observations and identify
  sanitizer target PIDs (including their exited-but-cached NVML records).
  No formal timing samples existed while those monitor issues were corrected.
- The original negative-radius fixture exposes a zero-CTA leaf launch. Its
  generated scratch-only legality guard is disclosed in amendment v1.3.
- All 17 other required workloads pass complete-output checks. On Tloc target
  1000 / Q1024, original A, faithful R, and float32 S each report an extra ID
  relative to the frozen double CPU oracle: query index 585, query ID 427451,
  object ID 417457. CPU distance 0.5796645534324731 exceeds the frozen radius
  0.5796645283699036 by 2.5062569575240445e-08; the original float32 output
  rounds to exactly the radius. Native ArborX passes that full workload.
- This is a measured correctness failure, not a valid latency result or evidence
  that R is slow. Preserving raw A's complete IDs and matching the strict frozen
  CPU set are incompatible on this boundary. A shared exactness adapter requires
  explicit disposition; the frozen radius/query/oracle is not retuned or waived.
- Raw full outputs, failed receipts, exactness diagnosis and passing native
  outputs remain in the task scratch. Formal timing has not begun at this entry.

## 2026-10-25 UTC — final retained six-round campaign

Experiment: `gts_20261024_repaired_host_ready`, epoch
`quality_1792914941223955366`. Contract v1 plus append-only v1.1/v1.2/v1.3;
original CONTRACT/calibration/query/oracle bytes unchanged. Actual GPU5 UUID
`GPU-a1e0baba-3982-4538-6540-2b013a1adf49`, driver590.48.01, CUDA13.1.115,
sm120. Shared host, clocks/settings unchanged. Six paired fresh-process rounds,
three warmups/three retained complete bundles per process, fixed direction-
balanced orders; process median then paired geometric mean/log-t CI. Same
campaign comparator remeasured, no historical timing denominator.

- **Implementation:** combined fixed/fused/dead-count/grid/Graph R and native
  batch S built. Native Kokkos4.7.04/ArborX CUDA BVH built user-local. All63
  full-output arm/cases accounted; 60pass, 3shared strict-ID failures in one
  required workload. All18 native A/R outputs byte-identical. 42 bounded
  memcheck/synccheck runs and changing-ID Graph stress pass. 63 separate count
  runs retained, with wrong-output diagnostic counts labeled. Source/resource
  and binary hashes retained; no new profiler/SASS result is claimed.
- **Measured effect:** R/S>1 and R/A<1 for all17 valid workloads, including
  entire paired pointwise95% intervals. Words R/S11.45–24.51, A/R6.47–12.21;
  valid Tloc R/S2.75–4.00, A/R2.22–3.67. A/R means serial original Update bundles,
  not historical native author-V2 batches. Native X has mixed R/X outcomes.
- **Work delta:** A/R metric calls/cells/coordinates/candidate leaves identical.
  R changes execution overhead, not pruning or full-table DP. Full-capacity
  Graph output/grid is an added sparse-query cost. Work counters support this
  mechanism but do not constitute a measured per-kernel time decomposition.
- **Quality exception:** target1000 Tloc/Q1024, extra ID417457 at query585 due
  float32 rounding onto radius. Independent CPU double is outside by2.506e-08.
  Failed A/R/S not timed; X passes/timed alone. No adapter/waiver/radius tuning.
- **Admission:** completed same-GPU epoch, 360timed processes/1080samples. All
  earlier diagnostic epochs have zero formal time directories and are retained.
  Final epoch had no observed foreign compute applications. Telemetry is sampled;
  no settings changed, no foreign signals, no cross-epoch/sample replacement.
- **Mechanism status:** execution repairs effective against the pinned serial A;
  competitive scan parity rejected on the valid subset. No universal metric-tree
  impossibility conclusion follows from this implementation or correctness gap.
- **Thesis impact:** no system-paper candidate evidence; subset favors an
  attribution/analysis direction. Frozen rule forbids full-matrix classification
  with the required quality gate incomplete. Low-dimensional route undecided
  (mixed >=5x results and one invalid R). A new novelty thesis is not established.
- **Reopen:** explicit disposition of exact-ID boundary, any common adapter as
  a new amendment, and a new complete oracle-valid paired campaign; or a
  genuinely new mechanism that changes the strong-baseline gap. Do not revive
  this R as scan-competitive by citing kernel-only gains, multiplying old gains,
  weakening S batching or changing the frozen test distribution.

### Claim-evidence map (supersedes the earlier unknown state, retains history)

| ID | Exact claim / scope | State | Gates and evidence | Counterevidence / allowed wording |
|---|---|---|---|---|
| C1 | R competitive with S across required18cases | rejected for this implementation on17valid cases; full quality incomplete | REPORT main table; RESULTS, raw_samples, TIMING_COMPLETE | All17 R/S CIs>1; no system-candidate evidence. Do not generalize to all trees. |
| C2 | R improves A for17quality-valid serial Update workloads | measured | Same GPU/driver/timing, full output+sanitizers; all17 R/A CIs<1 | Not historical native V2 batching; not a full18case claim. |
| C3 | Tloc route should close at R/X>=5 across tested matrix | inconclusive | Native X built and passes9cases;8valid R/X pairs | Four point estimates>=5, three CIs wholly>=5, others below/mixed; one R CF. Undecided. |
| C4 | R preserves A metric work and native full output | measured | Separate counts equal on18cases;18 native output byte equalities | One shared output set is wrong vsCPU; preservation alone is not correctness. |
| C5 | Full18workload exact-ID gate passes | rejected | FULL_QUALITY, EXACTNESS_FAILURE, FULL_OUTPUT_CPU_AUDIT | A/R/S each one extra ID on one Tloc case; no boundary adapter authorized. |
| C6 | Defensible new algorithmic/system novelty | unknown | No novelty evidence from this attribution campaign | Existing engineering combinations are not novelty; no paper thesis promoted. |

Durable raw references: `evidence/measured_20261025/PROCESS_EVIDENCE.json.gz`,
`RAW_MANIFEST.json`, `SANITIZERS.json`, `WORK_COUNTS.json`, `BUILD_PROVENANCE.json`,
`BUILD_LOGS.json.gz`, `RETAINED_ATTEMPTS.json`, `FROZEN_INPUTS_END.json`.
Large data/oracles/native outputs remain outside Git with hashes. Report and
RESULTS contain every required workload, including the failed one. The final
source revision is the enclosing task branch commit; no original source/old
receipt, frozen contract or paper prose was changed.
