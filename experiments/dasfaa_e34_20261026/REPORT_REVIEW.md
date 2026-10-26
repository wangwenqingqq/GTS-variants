# Curated report and publication review

Reviewed 2026-10-26 UTC. **PASS for the reviewed partial-result publication set; operational HOLD remains unchanged.** This review does not constitute a push, remote verification, a completed E4/E3 evaluation, or authorization to resume GPU work.

## Evidence cross-check

Independently read the retained local raw archive without extracting or publishing it:

- Archive size:238004 bytes; SHA256 `0b46b02587c05a2880bd5bf6dd77abb307cf4da7c98ec1c582ee5830b434ca0d`, matching `RAW_ARCHIVE.json`.
- Exactly eight completed GPU receipts: P memcheck and synccheck at Q1/32/1024, plus S memcheck at Q1/32. All use bounded N2000, one UUID, exit0, and valid receipts.
- Every curated receipt/stdout/stderr hash matches the corresponding raw file. Every raw complete-ID audit equals its curated quality record; output byte sizes match1000 rows or wrapped1024 rows as declared. All eight sanitizer logs contain `ERROR SUMMARY: 0 errors`.
- Every corresponding GPU guard starts within the declared16GiB RSS/48GiB memory-floor/<=900s limits and ends0, with no killed/refused event. Reported peak RSS and minimum MemAvailable match the extrema of these eight guard receipts.
- No formal `time_r` directory is present in that archive. S Q1024 memcheck, all S synccheck, full-scale gates/counts/timings, Word GPU, and E3 GPU are explicitly uncompleted.
- The raw stop record is `contract-output-scope`, not a resource/telemetry/SSH failure. Initial and final input-check JSONs are identical after removing their verification timestamps, including all file, prefix, oracle and isolation records.
- Deep matching-base-row counts are16/63/201/379 at1/3/10/20M. The report retains every requested Q, labels these rows blocked, and preserves larger P/G scales as not run under the N<=10M safety cap.
- Word evidence records three distinct newly generated120000-byte CPU oracles, immutable source/packed-data hashes, zero exact-value overlap at feasible Ns, and infeasible literal611K after holding out1000 of611756 source rows. Guard logs for the three oracle commands end0. No Word GPU claim is made. Thread count is configuration, not an independently sampled runtime thread measurement.

## Claim calibration

`E4_INTERIM.md` does not present sanitizer or process-settling wall time as latency. It claims no full-scale correctness, six-pair number, ratio/CI, fitted slope, crossover, story B, or novelty/priority result. It separates candidate-ID recall from the unresolved native-distance output-delivery requirement. The intentional STOP and the unanswered output/query amendments remain visible.

`E3_PROGRESS.md` retains all nine datasets, k8 plus L2 k10, Q1/Q32/full-query settings, native G arena uncertainty, metric5 angular semantics, and unestablished metric8 P/G support. CPU-only Tanimoto tests are not presented as target-GPU evidence. New Word/JIT code is labeled local/pre-launch, with source/runtime/artifact gates and the operational hold preserved.

## Publication boundary

The reviewed set is the task-local source, curated English documentation, review notes, and `evidence/resume_20261026/*.json` in this experiment directory, together with the already task-owned corrected-source commit. The raw archive remains outside Git; only its manifest/hash is intended for publication. No dataset, binary, checkpoint, credential, device configuration, or raw conversation is in the reviewed pending set.

A content scan found two newly introduced personal-home Python command paths; the primary owner replaced them with portable environment commands before this final pass. The subsequent scan found no home paths, credentials, raw-conversation dump, private host/proxy configuration, or prohibited AI-attribution text in the reviewed publication set. Full Git commit-message/author attribution scanning returned no matches. Existing repository ownership/visibility and branch authorization remain the primary publisher's responsibility; this review does not request history rewriting, anonymization of an existing public repository, unrelated cleanup, or merging main.

## Remaining delivery gates

The primary owner must stage only the named task-owned set, inspect the exact staged diff, run final tests/scans, commit, push the authorized experiment branch, and independently verify the remote commit and downloaded file hashes. A local review or commit is not evidence that uploading succeeded. Keep STOP set and report E4/E3 as partial until the user's pending contract decisions and subsequent independent GPU/evaluation gates are satisfied.
