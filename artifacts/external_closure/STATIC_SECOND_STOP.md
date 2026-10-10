# Second interruption: preserve48 valid rows, do not infer a complete ranking

2026-10-10; parent checkpoint `b94a5d9`.

The first recovery stopped again. Original4 valid observations plus44 valid
recovery observations give **48/72**, not a complete six-method/two-snapshot
matrix. The next entry, `first_rebuilt_r3_GPU_RANGE_COMPLETE`, exited normally
but failed the isolation guard;23 later entries were not attempted. The first
CPU-environment failure also remains. Including the earlier internal18,
there are68 primary attempts, not68 complete external results.

The flagged GPU-app snapshot reported one PID with `[No data]` at4.284s.
The child process resource observer recorded4.235s; the guard recorded4.498s.
Before/after snapshots were empty. The old guard sampled GPU apps before
reading live descendants and did not log owned PID/starttime identities.
An exiting-owned-descendant race is therefore a plausible explanation, **not
established historical ownership**. Do not relabel or count the invalid sample.
Complete output correctness does not repair failed isolation.

`static_second_stop.py` rebinds the original prefix/qualification, all44 valid
recovery results, source/input/binary/request/order/guard identities and the
invalid observation's complete output separately. It emits no speedup ranking.
The original registration, 45 recovery receipts, outputs and failed record are
immutable; the private bundle hash and sanitized proof are retained in evidence.

## Proposed bounded recovery, not launched

`static_guard.py` is a separate observer identity. It records process starttime
identities before and after each GPU-app snapshot. An exiting PID is accepted
only if positively observed as owned around **that same snapshot**; unknown,
conflicting or reused PIDs still fail. `[No data]` is never a whitelist. Initial
and final idle checks, advisory locks, timeout and full runtime/quality gates
remain. `test_static_guard.py` covers the observer race and foreign/PID-reuse
negative cases without starting a GPU workload. This does not prove that the
old flagged PID belonged to the experiment.

A new explicitly approved recovery must preserve all48 valid samples and both
failed attempts, bind the new guard and unchanged native executors, recheck
imports/inputs/qualification, and register exactly the invalid slot plus23
unattempted entries in original order. Expected cumulative primary attempts
would be92/102. Stop on the next failure; no generic retry/replacement loop.
The analyser must explicitly combine4+44+24, not forge the prior68-row COMPLETE
receipt or silently repurpose the old recovery registration.

The three requested task/lifecycle tables remain pending complete valid72-row
evidence. No external ranking, static-to-dynamic claim or long-run launch is
inferred from the partial matrix. CPU single-thread and inherited96B context
limitations remain unchanged.
