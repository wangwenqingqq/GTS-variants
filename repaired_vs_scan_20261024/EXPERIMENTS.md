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
