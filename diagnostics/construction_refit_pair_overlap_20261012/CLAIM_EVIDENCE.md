# Claim–evidence ledger

Experiment: `gtspp_20261012_construction_refit_pair_overlap`. Last verified: 2026-10-12. Provenance: parent d315215; original P2 observer + byte-equal native C0 stage captures; historical GPU1 SM120; this analysis CPU-only. See CONTRACT and input/derived manifests for exact hashes.

| ID | Claim / denominator | State | Evidence / gate | Counterevidence or material limit | Allowed wording |
|---|---|---|---|---|---|
| P1 | C and R share 4,999,800 unique ordered OID pairs / 4,999,800 R unique, R1/R2 | measured | Concrete enumeration, input hashes, immutable base mapping, RESULT summaries | One shape/trace, source-exact reconstruction rather than new pair-trace GPU kernel | Both captured rebuilds show 100% unique scoring–refit pair overlap |
| P2 | sum min multiplicities = 5,000,000 / 5,000,000 refit tasks | measured | Raw task lists, exact multisets, captured metadata count gate | Does not count arithmetic instructions or saved time | Every refit pair-task multiplicity is matched by scoring |
| P3 | All five L→L+1 alignments share 1M tasks | measured | LEVELS and full LEVEL_MATRIX | Same-level comparison would miss inherited pivot relation | Overlap exists at every aligned level |
| P4 | Scoring SAME_OWNER=0; boundary SAME_OWNER=111,110 | measured | Canonical member hashes, selected vs inherited pivot, owner dictionary / task lists | Dictionary indices are not identities; this balanced topology permits same-level owner test | All scoring matches change canonical destination owner |
| P5 | Boundary identities are a subset of scoring; boundary task matching 2.2222% | measured | Boundary stage-specific sorted order; union and multiplicity checks | Non-exclusive stages; identity-present R instances=111,128, not producer task count | Boundary adds no new reusable pair identity |
| N1 | Existing nominal arithmetic differs from directed interval consumer | inferred | Pinned tree.cuh/numeric.cuh and NUMERIC_LIFETIME source audit | CUDA pow/FMA codegen not disassembled; actual per-pair endpoint equality unavailable | Existing nominal outputs are not admitted as the exact refit certificate |
| N2 | Nonself per-pair bit equality | unknown | No per-pair refit outputs; only node extrema | Do not replace missing values with mismatch counts | Actual value equality remains unknown |
| N3 | 11,109 unique self pairs / 4,999,800 =0.22218889% optimistic admission ceiling | theoretical | Measured identity count plus analytical d(x,x)=0 interval | Not a mathematical bound on every conversion mechanism; not implemented reuse | Even granting trivial zero conversions, currently admitted categories fall below the gate |
| L1 | Scoring output survives to refit: NO | inferred | Reused dis_list and cudaFree at indexConstru end, refresh_bounds caller order | Boundary min_dis survives but is not the certificate; no new lifetime trace | Current scoring workspace does not preserve values until numeric refit |
| S1 | FP64 nominal payload=39,998,400 bytes; interval payload=79,996,800 | theoretical | Measured unique count × declared payload width | Excludes mapping/layout/traffic; not actual VRAM overhead | Payload-only capacity lower bounds, not a cache cost |
| D1 | Direct existing nominal→exact interval reuse | rejected | Frozen combined gate, N1/N3/L1 | Does not reject a changed build-produced certificate | NO_GO_REUSE under this existing-output contract |
| D2 | New certificate/fusion novelty, correctness or speedup | unknown | No evidence | No prototype, no prior-art clearance, no timing | No new mechanism or performance claim |

Measured here means CPU-reproduced exact analysis of pinned actual captures, not new GPU execution. Source semantic/lifetime deductions remain inferred; numerical equality and redesigned certificates remain unknown.
