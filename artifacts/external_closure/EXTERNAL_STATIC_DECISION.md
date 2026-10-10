# External static closure: evidence and next decision

The72-row matrix is complete. **P is slower than both strong GPU scan controls
under this frozen static contract**, while beating the qualified native
single-thread CPU portfolios. This is not an inconclusive GPU tie and is not
rescued by the existing internal R/P speedup.

## Same-contract evidence

Experiment: `GTSPP_20261010_EXTERNAL_STATIC_HOST_READY`; FP32 GIST
N1,000,000/D960/B1/K8, radius bits0x3f34a3d8, two snapshots. Each method/snapshot
has six fresh processes, eight warmups and32 measured calls per supported task.
The hardware is the admitted isolated RTX PRO6000 Blackwell single GPU on a
shared host; CPU libraries use one native thread and fixed NUMA placement.
Hardware/software, all72 rows, process CPU/RSS, phase distributions, inputs,
complete-output and guard identities are in
[evidence](evidence/EXTERNAL_STATIC_COMPLETE.json). Full outputs remain in the
private hash-bound raw archives, not just public result hashes.

| Claim ID | Evidence state | Exact scope and denominator | Result and allowed wording |
|---|---|---|---|
| EXT-KNN | measured |32-query Host-ready pass on prebuilt indexes; paired P/GPU Flat time | P takes1.584999x initial and1.586267x rebuilt; the scan is faster in all6 pairs/snapshot. |
| EXT-RANGE | measured | Complete range output under the same pass boundary; paired P/GPU scan time | P takes6.333017x initial and5.498743x rebuilt; the scan is faster in all6 pairs/snapshot. |
| EXT-CPU | measured | Same per-task boundary; single-thread KD/Ball/CPU Flat inclusive adapter | P wins every CPU comparison under the frozen gate; this is not whole-machine CPU throughput. |
| EXT-LIFECYCLE | measured | Preparation + build +32 kNN +32 range + native/index release | Against CPU Flat, CPU/P is9.542851x initial and9.431373x rebuilt. Single-task GPU methods are excluded from this ratio. |
| EXT-DYNAMIC | unknown | Same logical insert/delete/query service with paid maintenance and matched terminal state | No new external mixed-service evidence; static losses do not themselves establish dynamic loss or gain. |
| EXT-GPU-TREE | unvalidated | Target Host-ready timing identity | No timing row. Range-only target correctness is separate; kNN minimal repair fails native queue memcheck. |
| EXT-UNIVERSAL | rejected | Static superiority over all strong GPU controls | Contradicted at this shape/query scope. Do not claim all-GPU-tree superiority or pure coalescing gain. |
| EXT-NOVELTY | unknown | Non-incremental mechanism beyond prior work | A completed matrix is not novelty evidence; no new novelty claim is promoted. |

The task tables retain the primary **comparator/P** estimator. Reciprocal P/scan
values above are algebraic restatements, not a different selected statistic.
For kNN the comparator/P95% intervals are[0.629782,0.632010] and
[0.629987,0.630852]; for range they are[0.156274,0.159296] and
[0.180227,0.183367]. Both order strata are below1 in all four comparisons.
Bootstrap20000, seed2026101002, the six pairs and all raw observations are fixed.

## Retained adverse evidence and boundaries

- Keeper/control: native GPU Flat kNN and complete GPU range; candidate:
  unchanged PAR_STRONG/FULL/TILED P. No mechanism was changed in this recovery.
- Rejected claim: P has a static Host-ready advantage over these strong scans
  on the measured N1M/D960 observed-query workload. Added costs are visible in
  preparation/build/query/release tables; this campaign does not isolate which
  kernel or memory-organization mechanism causes the remaining gap.
- The two external failures remain distinct: pre-build CPU environment failure,
  and correct-output but isolation-invalid GPU range. The latter's historical
  process ownership remains unknown. Neither is retroactively admitted.
- Counts:4+44+24 valid,74 actual external attempts,92 including18 internal;
  old GPU qualifier count32 unchanged. Separate tree diagnostics remain6/8.
- The initial scan-range row and all other original observations remain in the
  estimates despite two interruptions and changed ownership observation.
  Batch registration times and both order strata are reported; no favorable
  subgroup replaces the original six-round estimator.
- Lifecycle excludes warmup/context, process setup, serialization and destruction
  of retained client outputs. It is not full-program wall time. The inherited
  96B context-symbol issue remains; no universal leak-clean claim.
- CPU tree inputs are converted to their native FP64 representation; conversion
  cost is recorded. CPU Flat range is explicitly inclusive-adapted. No lowered
  quality or approximate external result is used to repair P's ranking.

## Decision and reopen condition

Implementation status: this bounded recovery and external static reporting are
complete. Mechanism status: existing internal improvements remain measured at
their prior scopes; the external static advantage claim is rejected here.
Thesis impact: general superiority over strong GPU controls is not supported.

The supplied plan calls for **one same-semantics short mixed maintenance/build
check before considering10K**, because both static tasks lose to strong scans.
First bind query/insert vectors and delete occurrence IDs, preserve duplicates,
qualify the external update/output implementation, charge mapping/copies and
actual maintenance, and freeze the terminal-state policy. Do not force a scan
to rebuild an unnecessary tree or filter only a fixed top-K after deletion.
No new native process is launched by this decision note.

Reopen an external benefit claim only with a separately registered, correct,
same-contract mixed-service comparison showing an attributable advantage;
neither another favorable static query subset nor multiplying internal ratios
is a reopen condition. Any subsequent sustained10K comparison remains conditional
and separately registered. Internal P/T sustained stability, if selected, must
be labeled internal. A scope-specific static loss is not proof that every
possible dynamic workload or tree organization loses.

[Remaining gates](NEXT_GATES.md) preserve the GPU-Tree Host-ready admission,
logical-trace, resource-growth and long-timeout requirements. No manuscript was
published or rewritten by this delivery.
