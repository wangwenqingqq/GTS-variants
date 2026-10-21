# Reproduction and custody

## Evidence-only check

From this directory run `python3 check.py --test`. It verifies the exact publish
manifest, five frozen execution sources, input pins, nine process proofs, raw
seal/member hash bindings, 90 counter rows, 15 build rows and exact integer 10x
decisions. Three isolated-copy tamper checks must fail. It never launches C++,
reads a dataset, calls CUDA or requests a GPU. This is not a fresh metric
experiment or independently recomputed full-result oracle.

## Fresh CPU replay: separate from shipped evidence

Use Linux, Python 3.12, g++ supporting C++17 and unsigned 128-bit integers, at
least 5 GiB free disk, and source files identified in `evidence/INPUTS.json`.
Existing Words/TLoc are not redistributed: obtain their original GTS-format
inputs and require exact full-file hashes, not just row counts. DNA comes from
the public UCSC GRCh38 chr1 URL in the contract; verify its compressed SHA-256
against `evidence/DNA_PROVENANCE.json` and provider md5sum.txt first. Do not
replace missing inputs with synthetic data and retain the same label.

~~~sh
# All output directories must be new and outside this repository.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
python3 prepare.py --words "$WORDS" --tloc "$TLOC" --chr1 "$CHR1_GZ" --out "$INPUTS"
# Compare INPUTS.json source/trace/selection identities to evidence/INPUTS.json.
# A different identity is a different experiment.
nice -n 10 python3 run.py --inputs "$INPUTS" --out "$RUN"
python3 audit_run.py --run "$RUN" --inputs "$INPUTS" --out "$AUDIT_NEW_JSON"
python3 analyze.py --run "$RUN" --inputs "$INPUTS" --out "$SUMMARY_NEW_JSON"
~~~

One arithmetic thread, serial targets, 1800 seconds total worker time per dataset,
1.5 GB raw-run budget, first failure stop, no automatic retries. The frozen
runner is preserved verbatim; stronger post-run audit is mandatory, not an
optional route around input/campaign checks. New compilers may produce different
binary/timing identities. Never substitute a new run into the shipped evidence.
No GPU execution is authorized by this recipe.

## Accounting

Query/DB order, metric, output membership, self matches and duplicate-content IDs
are fixed. DNA/Words use unit Levenshtein; TLoc parses FP32 coordinates and uses
ordered FP64 squared-L2 membership. Every query-plan, partition, bound and
verification metric call is counted; persistent DB construction is separate.
All tree/partition methods use BFS. Frontier payload includes both vector
capacities and the candidate's resident query-tree ownership. Logical query-node
mass prevents a packed group from masquerading as eliminated work. These counts
are not GPU time, DRAM traffic, allocator RSS or service ACKs.

## Preservation and hash chain

`SOURCE_FREEZE_R1.json` and `SOURCE_FREEZE.json` preserve the pre-population
revision chain. `PREPOP_REVISION.json` records the only revision: complete the
already declared mutation/release/rebuild timing. No candidate code or threshold
changed after population counters were observed.

`evidence/RUN_SEAL.json` pins all 187 run files before post-run review.
`evidence/RAW_MEMBERS.json` pins the 232-member private archive including sampled
inputs, actual query/deletion files, source snapshots, full output streams,
compiler binary and original launch/exit logs. Archive SHA-256:
`ce9253ab6c9aab2daed935fb8f7068438005b7d840936f2a09e34e2f18f46458`
(4,867,063 bytes). Every member was independently streamed, hashed and extracted
locally, matching the persistent remote archive. Full source populations and
chromosome download remain persistent outside Git; URLs, derivation, full hashes
and sampling seeds enable reconstruction. Physical paths/raw payloads are not
published.

A redundant slow DNA downloader was superseded only after a verified fallback
transfer; its partial file and exact cancellation receipt remain private. This
was data acquisition, not a failed/replaced metric sample. An archive-transfer
quoting error left two empty postprocessing reports, retained privately before
successful transfer; no CPU target was restarted or evidence sample replaced.

The original runner checks trace/selection hashes, but not qid/delete at launch.
Post-run audit checks complete registered argv, source/binary identities,
deterministic current qid/delete bytes, full outputs and every query's zero-score
self-hit. It cannot prove those small files never changed during execution;
no launch-time attestation is claimed. No source/output repair or experimental
rerun was used to resolve this limitation.
