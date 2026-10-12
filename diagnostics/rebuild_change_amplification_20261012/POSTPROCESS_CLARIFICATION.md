# Post-processing clarification (no additional GPU replay)

The original contract, observer, snapshots, analysis v1, RESULT v1 and CLOSURE v1
are retained unchanged in private storage. A read-only audit identified three
interpretation/provenance issues after the single successful replay. Analysis v2
is a CPU-only clarification and is not presented as original preregistration.
GO/NO_GO thresholds are unchanged. The primary leaf/node decision is unchanged.

1. **Construction counts:** the captured 5,000,000 tasks count getPivotDisTiled
   pivot scoring only. nodeSplit additionally computes one FP32 min_dis distance
   for every created child: 111,110 tasks. The complete source-derived
   construction distance-task inventory is 5,111,110; this does not include
   hidden sort instructions. Keep the raw `build_distance_tasks` as pivot scoring.
2. **PAR counts:** 2,283,344 is regenerated final-payload scalar cardinality,
   justified by make_plan assignments and pushes. It is not executed scalar-store
   instruction count: initial assignments, overwrites, validation and temporary
   intermediates add work. Pack/refit output cardinalities similarly do not claim
   hardware instruction counts. No sums mix these heterogeneous units.
3. **Causal attribution:** A checks observed touched dependencies in POST and,
   when canonically matched, PRE (including deleted IDs/old pivots). Remaining
   matched changed nodes without direct dependencies are B, with no necessity
   claim. Unmatched nodes with no observed touched dependency are U (unknown),
   because no persistent pre-node alignment exists. C requires canonical
   topology and all numeric state identical. The original two-bucket label
   `B_transitive_observed` is superseded; it cannot prove unavoidable transitive
   work. Ordered child topology also includes the child's pivot occurrence.
4. **Closure:** the original registration bound binary/source/case, but did not
   individually preregister every runner/checker/reference file. Final closure
   rechecks those dependencies against the prior campaign's frozen INPUTS and
   raw-file manifest, then explicitly marks current script bindings as
   post-close verification. No later binding is misrepresented as an original
   preregistration pin. The earlier CLOSURE alone is not complete provenance.

Full saved snapshots are reanalyzed twice on CPU with identical result hashes.
The CPU address/index-churn regression check also passes. No optional GPU repeat,
new workload, sanitizer, external process or mechanism has been added.

Physical positions additionally cover the complete PRE/POST logical live set,
including PRE insertion scratch rows. All pending occurrences already exist in
PRE, so they are moves into base, not newly created occurrences at rebuild.
The base-only ledger retains admissions/tombstone removals and survivor moves;
the all-live ledger adds the ten pending-to-base moves. Across the rebuild itself
there are zero logical creations/deletions. Mutation-window net changes remain
separate. This is a denominator clarification, not an additional replay.

The first CPU post-close verifier stopped on a prior-quality JSON schema error
(`passed` was nested under measured/warmup rather than top-level). Its log is
retained. The reader was repaired to check both phase reports and all six payload
hashes, and to bind the original runtime receipt hash. Only the CPU verifier was
retried; no GPU process or snapshot was changed. This failure is a tooling
closure failure, not a failed keeper replay or favorable-sample replacement.

The first small-archive check also caught a packaging omission: one private,
regenerable Python bytecode cache was listed in FINAL_CLOSURE but excluded by the
archive filter. The original archive/manifest are retained as V1. The corrected
private archive includes that exact bound cache plus ARCHIVE_REPAIR.json, so the
final local verifier checks every closure binding rather than silently skipping
it. No snapshot, result or GPU process was changed.

The published close helper derives CPU-analysis inventory from retained result
directories rather than hardcoding this run's four analyses, so a fresh recovery
cannot falsely claim the intermediate analysis occurred. The archived original
close helper and FINAL_CLOSURE retain their accurate historical four-analysis
record; this portable metadata-only fix changes no gate or saved result.
