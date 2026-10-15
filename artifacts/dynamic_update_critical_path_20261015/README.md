# Update critical-path attribution — stopped checkpoint

**No native-path bottleneck conclusion or speedup is admitted yet.** R1 was
stopped when source review found that annotation scope moved deletion's
`std::set` destruction ahead of copy submission. Both instrument modes were
affected. Correct search outputs do not validate this changed Host path.

| R1 state | Count |
|---|---:|
| Registered maximum GPU starts | 124 |
| Actual starts | 84 |
| Qualification passed | 29 |
| Primary passed before stop | 54 |
| Interrupted, not accepted | 1 |
| Primary not executed | 29 |
| Timeline not executed | 11 |
| Passed nonselftest outputs rechecked offline | 75 |

The interrupted service produced valid-looking complete output under the
offline checker, but lacks the guard completion receipt. It remains excluded.
The unchanged parent service binaries and copy controls were not affected by
the annotation lifetime change; their partial observations are preserved, not
combined into a completed six-round study. No replacement was auto-started.

## What was fixed, not yet GPU-qualified

1. Close the validation NVTX range explicitly without introducing a new scope
   for the validation set. Its original post-sync destruction is preserved.
2. Require nonnegative finite distance and squared-distance output fields.
3. Bind replacement summary time, bytes, copy calls and synchronization calls
   exactly to its two native records.

CPU validation passes 27 replay cases, 27 corrupt mutation witnesses, 14 corrupt
field/accounting cases, an exact source-body roundtrip and two extracted-body
lifetime tests (TRACE 0/1). A first CPU fixture incorrectly expected two swaps
for IDs `{0,1}`; it was retained and corrected to `{0,2}`. This is not a GPU
correctness, profiler, or native performance result.

## Evidence and resumption

- [Decision and unfinished questions](DECISION.md)
- [Claim boundaries](CLAIM_EVIDENCE.md)
- [Exact execution ledger](evidence/EXECUTION_R1.json)
- [Offline quality](evidence/QUALITY_R1.json)
- [Source and binary identities](evidence/IDENTITY_R1.json)
- [Raw-file inventory](evidence/RAW_MANIFEST_R1.json)
- [CPU checks](evidence/CPU_FIX_VALIDATION.json)
- [Reproduction and custody](REPRODUCE.md)

Recovery proposal: fresh R2 registration, at most 124 starts, including fresh
same-card controls; cumulative R1+R2 maximum 208. Authorization is pending.
No new data, query set, timing denominator, estimator, index or storage
mechanism is proposed. Do not resume the stopped R1 or overwrite its records.
The four requested figures and NSYS attribution remain pending: fabricating
them from unqualified timings would defeat the study.
