# Audit record — stopped checkpoint only

## Read-only source findings and independently verified fixes

1. **Critical-path source deviation:** R1 introduced a validation-set scope.
   Its destruction moved before D2D submission. Both PLAIN/MARKED are affected.
   The controller was interrupted; the full execution record remains stopped.
   Fixed by explicit NVTX close without changing the original set lifetime.
2. **Native field validation gap:** squaring distance alone admitted negative
   distances. Fixed by explicit finite nonnegative distance and squared fields.
3. **Replacement accounting gap:** pair fields were not bound to native
   delete/insert records. Fixed by exact time and copy/byte/sync equality.

The three code repairs were independently re-reviewed read-only and all CPU
regressions re-executed. Validation-set destruction now belongs to Other Host,
outside `DELETE_VALIDATE`, inside `U_DELETE`. This is a source/CPU check, not a
new GPU pass.

## Evidence custody and stop

The R1 source archive predates all starts. Its three changed sources reconstruct
exactly by reversing the published patch; its original scope and contract are
retained. The raw work tree, partial guard and interrupted output remain
external and hash-inventoried. Exact partial-stage file/command/guard/output
census passes: 84 starts, 83 passed, one interrupted, 40 unexecuted. All 75
previously passed nonselftest outputs pass the stronger offline checker.

No completed NSYS capture exists, no source-deviated ACK timing is promoted,
and no figure is fabricated. No foreign process was signaled or GPU setting
changed. Only the new task directory is a publish candidate; older artifacts,
unrelated work and manuscript sources are excluded. A fresh recovery requires
new authorization and registration, not relabeling the R1 records.

## Interrupted telemetry and archive custody

The interrupted guard left its read-only telemetry child writing `gpu.csv`.
The first archive failed because that file changed during tar; this failed
archive is retained and rejected. The monitor was identified by matching owner,
process starttime, exact query command and open descriptor to this task's log.
Only that verified observer was terminated, not a GPU workload or foreign
process. Its log contains post-stop observations and is excluded from every
attribution result. The 83 passed samples and frozen sources were unchanged.
A separately named STABLE archive was created after logging stopped and is
hash-bound in the raw manifest; neither archive is published to Git.
