# Word phase pre-launch integrity review

Reviewed 2026-10-26 UTC. **Code-review verdict: CLEAN within the stated scope, with the findings below corrected before Word GPU execution. Operational verdict: HOLD.** The global campaign stop and the unresolved complete-output payload contract remain binding. This review does not authorize removing a stop, starting Word, changing the payload contract, creating a replacement epoch, or promoting timing results.

## Review boundary

Read-only review of `word_campaign.py`, its tests and change note, `make_word_freeze.py`, its creator-to-runner integration test, the supplied contract/amendments, and the installed CuPy compiler/cache source captured by the primary executor. No remote command, NVML query, real signal, GPU kernel, sanitizer, or benchmark was run by this reviewer. The Word source parser/oracle/auditor were implemented earlier by this reviewer; their correctness is not independently established by this orchestration review. Real-source manifests, target binaries, and CPU-oracle run artifacts still require the primary executor's exact-artifact validation.

The primary executor reported a global stop on 2026-10-26 at 02:12:55 UTC, before any formal timing, to resolve whether complete output must include native k-distance values as well as IDs. The current P vector/Word harness copies IDs but not those native distances. Even a clean orchestration review cannot waive that material timing-scope question. No Word GPU launch is approved by this document.

## Reviewed identities

| File | SHA256 |
|---|---|
| word_campaign.py | `be94569a70391eb14d95317dd506d9580be53faab239fd811f9505d6db1a6307` |
| make_word_freeze.py | `48816550b1b88dcf50a4fa819d8d19939325c52e81e300a6c0f012efad092478` |
| test_word_campaign.py | `0f24ee70c7f046b8f91e197667b23195f8a23c7b649e6ed344c3fc7bb423d483` |
| test_word_freeze.py | `c01e795139ffa9fbf738649b2b9a3623dc00f2a489ca6b0903a0175108325f20` |
| campaign.py | `cf35b5bcad2baa65e83a8879e78b5afe7d8a607e013cad598af7f2a250470c68` |
| lock_support.py | `b759aa687e9d8f346333de9ee52e9627bd36bced58659656bfe58236a83769a8` |
| audit.py | `74f3a71b0309b675b1c78e35cdb0c98d5ce0d6cbc17ce23f0756ba2ebe65890c` |
| scan.py | `ad5c7d68f77a6f1898a76f28bbe6da3924451e0f10995327f8e460e4918c0e05` |
| tree_bench.cu | `aeea431516a1677fe307c982773fb0faf2da42b2751d0a28e427a21f3d075b2c` |

The last five identities match the existing vector epoch's reviewed implementation; this Word audit did not edit those frozen files. Later source changes require a new review/freeze, not silent continuation under these hashes.

## Findings and disposition

### INFO — prescribed workload and ordering retained

`NS=(61000,150000,300000,611000)`, `QS=(1,32,1024)`, k8 and stride109 are checked against the immutable Word manifest. Literal 611K remains visible and is never launched when the held-out split leaves only 610756 indexed rows. Exact-value overlaps block loads rather than resampling queries. The plan contains every requested N/Q, bounded P/S memcheck/synccheck at all Qs, separate P work counts, and six alternating PS/SP fresh-process rounds. Skipped and correctness-failed loads remain recorded and are not replaced.

Word requires the vector `COMPLETE.json` to indicate that its plan was processed and rejects failed vector epochs. Initialization and every GPU step use the prior vector GPU UUID through the existing same-device advisory lock and campaign lock; there is no automatic card selection or retry. The Word telemetry state inherits the prior timestamp so the >=30-second cadence does not reset at the phase boundary. All GPU execution delegates to the frozen `campaign.execute`; CPU dependency/oracle steps use the same guard wrapper with at most16 OpenMP threads and no visible GPU. Global campaign and caller-reported SSH stop markers are checked before any phase work.

### WARNING, corrected — case inputs could evade frozen-file coverage

The initial runner verified entries in the phase file map but did not require every case's base/query path to belong to that map. The initial freeze creator also allowed unchecked manifest paths. Current creator path validation rejects absolute/escaping input names and unlisted case inputs. Current runner checks resolved task locality and coverage by both the Word manifest and the phase manifest; command construction checks the bound input paths again. Mock regressions cover escape and partial-coverage attempts. No real Word GPU run used the earlier path-check gap.

### WARNING, corrected — source/binary hashes needed actual build binding

A binary hash beside a source hash alone does not establish which source was compiled. The Word build record now binds all three binaries to their sources, exact compile commands, successful guard logs, and hashes. The runner checks source/output command paths, instrumented-count versus timing flags, CUDA13.1/SM120 metadata, one start/end guard pair with exit0, and absence of killed/refused events. Every compiled P header in the corrected source manifest is included in the phase freeze. These checks validate the supplied build-evidence record; they are not SASS inspection or a substitute for target correctness/sanitizer gates.

### WARNING, corrected — self-consistent JIT history rewind

The original cumulative cache chain could be reset to an older self-consistent state if the newest manifest and added cache files were removed. Successful S steps now include their manifest path/hash/sequence in `STEP_*_DONE.json`. Before every next step and final completion, the current head and every manifest in the full chain must match every completed S checkpoint. The delete-and-rewind regression now fails. New cache keys may appear only during an S process; existing `.cubin/.cu` files cannot change or disappear. Failed-process cache evidence is diagnostic and cannot yield eligible timing. This detects the specified history mutations; it is not a claim of an external tamper-proof filesystem.

### WARNING, corrected — venv invocation and runtime freeze integration

Resolving two venv Python symlinks can yield the same interpreter, so resolved executable identity alone was insufficient. The runner now freezes the exact absolute invocation path separately and checks it against the runtime provenance. Read-only runtime dependency files must form a nonempty absolute-path SHA256/size map and are rechecked at each identity validation. The creator initially omitted that new map; a creator-to-runner integration test exposed the mismatch. Current `make_word_freeze.py` includes `RUNTIME_WORD_FILES.json`, verifies its runtime map, and writes both runtime hashes and the exact Python invocation into the atomic no-overwrite phase manifest. The integration test now passes. The required actual runtime inventory still must be collected and reviewed before a future authorized launch.

### INFO — complete result counts and oracle identities enforced

Q1024 must deliver exactly1024*8 int32 IDs; Q1/Q32 must deliver all1000*8. Full and bounded oracle payload sizes/hashes are checked before a child and again before auditing. The frozen Word auditor checks every candidate against the independent CPU oracle, including range, duplicates, tie-aware distance threshold, and expected output count. Correctness failure remains a recorded gate failure rather than a tuned replacement. These checks do not resolve the separate ID-versus-distance payload hold.

### INFO — installed CuPy cache assumptions verified from primary source

The captured installed runtime is CuPy14.1.0. Its compiler code uses `.cubin` cache names and `_kernel_cache_backend.load/save`; the selected backend is `DiskKernelCacheBackend`. Its constructor reads `CUPY_CACHE_DIR` and `CUPY_CACHE_SAVE_CUDA_SOURCE`, and its disk container contains an ASCII SHA1 prefix followed by the compiled payload. Word sets its three cache environment variables before launching each fresh S Python child and restores the parent environment on both success and failure. The source also confirms that `CUPY_CACHE_IN_MEMORY=0` does not bypass disk persistence in this path.

Reviewed installed-source hashes from the captured logs:

- compiler.py: `d90c0b3adb5eeb360826b1a38499155de187ceef5a7b089c98f6251c36116834`
- _compiler_cache.py: `058394246b4792caeb45c2f5f780f799f3c84be475d70f146ed5e9112d73f301`

The runner correctly labels its SHA256 as the **whole CuPy disk-cache container** hash, not a raw ELF/cubin-only hash, normalized SASS hash, or proof that every cached function executed. No real Word JIT cache artifact was generated or independently inspected by this review.

## Local checks rerun

- `python3 test_word_campaign.py`: **31** mock-only tests passed.
- `python3 test_word_freeze.py`: creator-to-runner verification, runtime/build binding, no-overwrite publication, and task-local case coverage passed.
- `python3 test_bits.py (Python >=3.10)`: **10** CPU/mock-only E3 packed-bit checks passed. The system Python3.9 correctly refuses that auditor because it lacks `int.bit_count`.

The E3 bit scan/oracle/auditor received a supplementary read-only inspection. No numerical code defect was identified in that limited scope. Its empty-union distance0 policy, exact source packing and holdout, full ID+FP64-distance output scope, P/G support, CUDA compilation, sanitizer and timing remain separate E3 freeze/validation requirements. Those CPU tests do not finish E3.

## Final disposition

No result fabrication, query resampling, selective favorable-load removal, evaluator rewriting, or timing promotion was found in this review. The identified trust/provenance gaps were corrected before any Word GPU execution and are retained here rather than erased from history.

**Remain stopped.** The vector plan is not a completed E4 result, Word has no validated GPU measurement, and no crossover, slope or paired CI follows from these tests. Future work requires the user's explicit resolution of the complete-output payload contract and the resulting authorized amendment/revalidation plan, plus normal source/runtime freeze and hardware gates. This review does not authorize retrying a safety-stopped or otherwise failed epoch.
