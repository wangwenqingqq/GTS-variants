# Audit boundaries and postmeasurement hardening

The contract, GPU adapter sources, quality gate, input schedules and analyzer
were frozen before the primary campaign. Postprocessing was kept separate.
No GPU process was rerun or replaced for this audit.

A read-only preliminary review found a proof gap, not a wrong-result sample:
the first curator checked commands against guards/receipts but did not derive
them again from each frozen job, and it did not reject off-ledger stage files.
The offline checker was hardened before final curation:

1. Derive every complete command using the unchanged `campaign.command`.
2. Require exact stage-root, guard, output, command/checked/log and report sets;
   reject extra entries, nested unexpected directories and symlinks.
3. Bind all117 commands to the sequential start ledger and raw-file identities.
4. Retain wrong-command-with-consistent-receipts, extra guard/checked/output/
   report/log and symlink negative fixtures in `test_audit.py`.

This changes no query, kernel, binary, measurement, stop condition or statistical
estimator. The former postprocessing source archive is retained privately;
`evidence/INPUT_IDENTITY.json` identifies final executed postprocessors, while
`evidence/STAGE_CENSUS.json` records source-derived command hashes and exact
family counts. The public verifier also checks the raw-manifest file census.
A hash is provenance, not public re-execution of private complete answers.

Per-process operation summaries were additionally exported after measurement
for the plan's update, nested statistics spans, memory, throughput and finite
query-tail inventory. They do not change the frozen primary estimator or create
a posthoc winner threshold. `summarize.py` reconstructs the descriptive table
from these published records. Full raw operations remain in private custody.
