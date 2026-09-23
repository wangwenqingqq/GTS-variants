# Claim / experiment ledger

Experiment `gtspp_20260923_workflow_integer_l2_audit`, contract in `CONTRACT.md`.
Keeper: pinned native archive; candidate: none. Predicted mechanism deltas are
proposals in the operator ledgers; there is no optimized-versus-native comparison.
Provenance is the source/binary/raw-file hashes in `EVIDENCE.json`; last live
collection verified on2026-09-23. The source inventory and diagnostic stages are
complete at their stated scope, not a correct/paired/accepted performance campaign.

| ID | Exact claim / scope | State | Evidence and counterevidence | Allowed wording / next gate |
|---|---|---|---|---|
| W1 |69 custom definitions and1,014 call sites inventoried in17 pinned files | measured | catalog assertions, source pins, unchanged-body test;35/55 selected definitions dynamically observed | Source-complete inventory, not exhaustive dynamic branch coverage |
| W2 | Static query transpose/leaf/build/rebuild paths contain inefficient representative memory access | partial |35 selected NCU rows plus exact source mapping; sparse tails/broadcasts are counterexamples to naive ratio interpretation | Candidate geometry established for these shapes; no promised speedup |
| W3 | Direct inserts/deletes and buffer query perform CPU/device round trips | measured | Native NSYS API correlation and copy byte/count rows; migration rows without API correlation stay unattributed | Boundary removal is a separate mechanism from GPU coalescing; full operation A/B needed |
| W4 | Native update replay is not an admitted exact baseline | rejected | All-include1999/2000; rebuild68/69; clean, memcheck and NSYS failures; corrected rebuild NCU confirms68/69 | Two count failures under self-included integer-L2 contract; no root-cause assertion for rebuild |
| W5 | Passing simple update counts establish safe insertion/deletion | rejected | Capacity/bounds/identity risks; buffer-delete no final oracle; memcheck0 cannot prove semantics | Only bounded count checks passed; require complete mixed-operation IDs/distances/live state oracle |
| W6 | CPU arithmetic is the primary measured cost of routing | inconclusive | First route2.1067ms wall,65 routes total2.1620ms; managed memory/wait/cold-start mixed in phase | CPU phase exists; useful arithmetic share is unresolved |
| W7 | New workflow coalescing changes accelerate end-to-end | unknown | No optimized candidate or paired measurement in this audit | No speedup claim; correct keeper, one mechanism, paired/sustained gates needed |

## Retained negative / invalid records

- All-include query: measured count violates frozen self-inclusion. Memory-check
  pass does not rescue it. Reopen after consistent self/ID/distance semantics and
  independent result validation; target was native N2000/r10000.
- Rebuild: measured post66-insert query misses one count at r200. Source risks
  are hypotheses, not localized root cause. Reopen after first divergent boundary
  and full result equality are established. No optimized rebuild promoted.
- First NCU getNewData attempt: absent explicit sudo threshold2 caused no rebuild;
  no selected launch/report. Preserve as rejected **collection**, not evidence
  against a coalescing mechanism or an inconsistent post-rebuild output.
- Buffer-delete branch: input size1 and0 surviving stores cannot establish store
  packing quality. Reopen on nonempty survivor distributions with an oracle.
- Prior kNN Q32 regressions/inconclusive short gates remain in the linked prior
  campaign. Broader workflow auditing does not promote that overlay universally.
