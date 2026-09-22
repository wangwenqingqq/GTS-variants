# Supplementary source admission

Registered on 2026-09-22 before supplementary measurements. The user approved
the two previously identified files from the older GTS dataset collection.
This resolves the source decision recorded as pending in commit `16b731c`.

| Dataset | Relative input | Header | Interpretation | Native metric |
|---|---|---|---|---|
| Protein | `dna_barcode/protein.txt` | `100 52799 6` | 52,799 original sequences, declared length limit 100 | Unit-cost Levenshtein |
| ChEMBL | `chembl/chembl_50k.txt` | `2048 50000 8` | 50,000 fingerprints of 2,048 binary features | Binary Tanimoto |

No substitution with `protein_200k.txt` or ChEMBL-10K is admitted. Both supplied
query-ID files contain 1,000 distinct valid IDs within their corresponding base
cardinalities. Record and verify full base/query hashes during the run.

The supplementary run uses unchanged source and contract from the accepted
seven-dataset comparison: 20,000 sampled references, 512 disjoint queries,
three fixed seeds, full descriptive scans, 10,000-row covariance, 2,048-row
hubness, native query diagnostics, and file-order controls. Strings and binary
fingerprints receive no continuous LID. Source SHA-256:
`8dc24f33852b157eb0d4cf7ccabc72ccfd4ddb31f87fa557725cd3a933612e27`.
Contract SHA-256:
`5fa81ff647cf1b0efa3eb3f7d4cd762f9a1018fc6c7bbec92f5efaf313dcaaec`.

Inputs remain read-only. Use CPU-only execution, low scheduling/I/O priority,
two numerical-library threads, and a new `run04_supplementary` output directory.
No other process or service is modified. The two results can join the combined
report only after source, sample, metric, and raw-to-aggregate validation.

Source admission does not establish an exact upstream UniProt/ChEMBL release,
the fingerprint generator, or molecular identity. Those provenance limits
remain explicit. File order is not a verified time axis.
