# Claim–evidence ledger

| ID | Claim and denominator | State | Evidence | Counterevidence / allowed wording |
|---|---|---|---|---|
| U01 | Source review: serial delete submits one D2D row request per actual swap; insert submits one H2D request per batch. | measured | Parent `service.cu` MODE=2 and hash-bound R1 generated source. | Source structure, not measured physical traffic or dominant cost. |
| U02 | R1 preserves the exact native Host critical path. | rejected | `provenance/R1_SOURCE.diff`, frozen source identity. | Annotation scope shortened validation-set lifetime in both variants; no native ACK claim from R1. |
| U03 | The fixed delete preserves source scope and destruction after sync. | partial | `evidence/CPU_FIX_VALIDATION.json`, `test_protocol.py`. | CPU mock and textual proof only; GPU qualification pending. |
| U04 | Previously passed nonselftest outputs satisfy stronger fields/accounting gates. | measured | `evidence/QUALITY_R1.json`, 75 offline rechecks. | Retrospective output validation does not repair R1 timing provenance. |
| U05 | The interrupted service is a valid completed measurement. | rejected | `evidence/EXECUTION_R1.json`, missing guard receipt. | Output-only checks pass, but isolation/runtime completion is incomplete. |
| U06 | Host/control or synchronization dominates native update ACK. | unknown | No completed admitted native-path study. | Source counts alone cannot distinguish waits, staging, submission and actual device work. |
| U07 | Batch growth reduces native amortized cost by a particular amount. | unvalidated | R1 partial raw files retained, not promoted. | Lifetime-preserving fresh measurements are required. |
| U08 | Update GPU kernel, DRAM/L2 or DMA utilization is quantified. | unknown | Timeline stage not started. | No application kernel in source is not a zero-traffic measurement. |
| U09 | A novel dynamic-search systems mechanism is established. | unknown | This is attribution only; `PRIOR_ART.md`. | No new algorithm, product admission or manuscript claim. |

Provenance: parent commit `d4e196f38aa8242e547e3dea3d9311650bb9ef10`,
2026-10-15, RTX PRO6000 Blackwell Server Edition, CUDA 13.1. Sources, binaries,
guard hashes and raw-file identities are retained separately. Native-path
performance remains unvalidated; exact occurrence/output evidence has narrower
validity. A future fixed run cannot retroactively change these states.
