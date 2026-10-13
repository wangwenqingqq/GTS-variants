# Validation scope

## Executed

- Frozen parent `ef9df8e`, precise B0 count, N/D, all 32 query IDs, cutoff and input/reference hashes. Human-approved WEAK_HEADROOM and uncovered-p90 stop rules; exact rather than rounded thresholds.
- Initial primary-source novelty triage admitted the CPU diagnostic only. Dedicated routing audit followed C1 GO and rejected GPU/novelty admission.
- Target g++ 13.3.0 native build with the declared strict FP64 flags; qualified binary reused unchanged in C1. No installation or CUDA initialization.
- Native independent fixtures: 272 rows per invocation, including stable top-k, original-order bit sums, finite extremes, signed zero, subnormal, equality, duplicates, nonfinite and index guards.
- A and B each qualify all 32 x first 4096 pairs before their full population. O1 uses independent NumPy stable sorting; C1 independently accumulates selected terms.
- Exactly one 32M-pair Gate5A population and one 32M-pair Gate5B population. B0 per-query counts match the old exact parent; all 32M O1 full-score bits match frozen files. All B0/O1/C1 partials are safe with zero false rejection. Zero O1 numerical-boundary pairs.
- Input, code and frozen-reference identities checked before/after each population. Only new task-owned scratch written; no foreign process signalled or GPU setting changed.
- Read-only saved-array observer verifies hashes and all **96M partial bounds** across the three methods on the **same 32M distinct pairs**, without candidate replay. Public scalar checker independently recomputes gates, aggregates, ratios, overlap and metadata ownership.
- Exactly the three requested auxiliaries: selected-set overlap, contribution concentration and margin distributions. Contribution statistics explicitly exclude 33 zero-full-score pairs; no artificial ratio is substituted.
- Three SVG/300-DPI PNG figures rendered at compact final size, with no invented CI, explicit nominal-byte scope, zero-origin bars, log-labeled ratios and redundant grayscale encodings. Native geometry and visual checks are recorded.
- A fresh whitelist copy on the intended CPU passes the independent stdlib scalar checker and all native fixtures; its native binary matches the qualified population binary byte-for-byte. `evidence/CLEAN_COPY_VALIDATION.json` records those checks. The separate checker also audits 96M saved partials; `evidence/INDEPENDENT_RAW_AUDIT.json` records the read-only audit. Saved-array reanalysis matches all 43 regenerated public files byte-for-byte.
- Publication-set and independent read-only release audits are separate from experiment qualification. No local report by itself confirms GitHub upload.

## Not executed / not established

- CUDA implementation, GPU sanitizer/stress, NCU/NSYS, physical DRAM/sectors, latency, sustained or end-to-end timing: **NOT_RUN**.
- Complete range-result pipeline, kNN, insert/delete workflow, larger query pools, other datasets, ordering/budget sweeps or additional probes: **NOT_RUN**.
- Same-contract external query-adaptive comparison or distinct publishable routing mechanism: **not established**. Numeric GO is not research admission.
- A universal physical-byte optimization abstraction, per-query strict gains, arbitrary-query guarantees or an exhaustive absence-of-prior-art result: **not claimed**.
- Raw original/query vectors, 768MB of saved partials and source PDFs are not in Git. Public scalar checks cannot reproduce the full raw audit without identified inputs.
- Manuscript edits, synchronization, compilation, submission or keeper replacement: **not performed**.

Operational receipt times (A 127.036277 s; B 22.381513 s) include unequal build/qualification/preprocessing/hash/export work and **must not be compared as search latency**. Independent raw arrays and negative admission evidence remain intact.
