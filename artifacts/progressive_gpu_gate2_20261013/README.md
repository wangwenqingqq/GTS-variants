# Progressive stage execution: Gate2

**Decision: GO_PROGRESSIVE_GPU (strong-GO thresholds met).** On the frozen GIST1M/D960/B1 initial snapshot, one `STAGED_COMPACT` implementation cuts complete Host-ready range-query latency by **55.6625%** (2.255428x) relative to the same-campaign strengthened exact-scan keeper. All-kernel DRAM traffic drops by **71.0181%**. This is a static operator feasibility result, not a dynamic-workflow or novelty claim.

| Same campaign | Complete Host ACK, ms/query | All-kernel DRAM, GB/query |
| --- | ---: | ---: |
| B0 READ_ONLY structural control | 2.518568 | Not profiled this campaign |
| B1 strengthened non-padded exact scan | 2.573117 | 3.862199 |
| P1 STAGED_COMPACT | 1.140855 | 1.119337 |

ACK is the median of six fresh-process mean ACKs. Each process has eight warmups and the original32 measured queries. Traffic is the mean of32 all-kernel totals from independent NCU processes:160 baseline and416 candidate kernel launches. NCU duration is not primary latency. Matched-process geometric ratio **0.443278**, 95% bootstrap CI **[0.442961, 0.443627]**, wins **6/6**; both order strata retained.

## Redundancy -> mechanism -> module -> effect -> end-to-end benefit

- **Redundancy:** reading the entire960-coordinate row even after a safe prefix already excludes that occurrence from the inclusive range.
- **Mechanism:** outward-bounded partial sums and ordered-FP64 refinement; fixed checkpoints128/256/512/960, no dimension permutation or approximation.
- **Module:** a16-byte `PrefixState`, four warp-per-row scans, stable installed CUB selection, actual count readbacks and complete Host output.
- **Effect:** CPU checkpoint-rounded coordinate opportunity1.014829GB/query is realized as measured all-kernel DRAM1.119337GB/query, including every selection and materialization kernel.
- **End-to-end operator benefit:** complete exact-output Host ACK2.573117 ->1.140855ms/query in the same campaign. No owner/survivor construction, compaction, count wait or result transfer is moved outside the request.

## Gates reached and strongest caveats

Numerical proof and CPU pre-screen preceded CUDA. Strict modeled logical payload including tuple padding, flags and replay upper bound is1.103315GB/query; this is not measured DRAM. All complete checkpoint IDs, multiplicity/order, final membership and declared fields passed. Synthetic100 iterations/two independent streams plus boundedN4096 target passed memcheck, racecheck and synccheck. Full-N sanitizer and Graph were not performed/claimed.

The32 fixed queries are reused across all processes, not32 independent process replicates. Outputs are highly skewed:30 queries have1 or2 hits, two have1114 and5443 hits. One query's median P1/B1 ratio is about0.971; the mean-traffic strong-GO does not mean every query has traffic<=1.30GB (maximum1.626807GB). This does not establish10k queries,100k events,1B scale, insert/delete cost, CPU-tree/GPU-tree/CAGRA/IVF superiority, or production integration.

Event-enabled diagnostics isolate CUB selection at **4.5655%** of that diagnostic's complete ACK, below the25% persistent-motivation gate. The scan phases remain dominant, including final ordered-hit replay. Host-minus-events is an unattributed residue, not proof of recoverable CPU waiting. NSYS was conditionally skipped because both primary GO latency/CI tests passed; no trace-derived launch-gap claim is made.

Novelty classification stays **ENGINEERING_ONLY**: early abandoning, dimension pruning and stream compaction have established prior art. Do not turn this GPU realization into a new paper mechanism or restart the abandoned incremental baseline. Production dispatch, manuscript and dynamic workflow are untouched.

## Read next

- [Decision and five questions](DECISION.md)
- [Frozen contract](CONTRACT.json), [numerical envelope](NUMERICS.md), [prior art](PRIOR_ART.md)
- [Complete timing](timing/PRIMARY_TIMING.md), [all-kernel DRAM](traffic/DRAM_ACCOUNTING.md)
- [Checkpoint/stage table](stages/STAGE_COUNTS.md), [event breakdown](breakdown/STAGE_BREAKDOWN.md)
- [Sanitizer boundary](correctness/SANITIZER.md), [claim ledger](CLAIM_EVIDENCE.md)
- [Reproduction and privacy boundary](REPRODUCE.md)

Execution:32 successful GPU processes plus one preserved pre-CUDA guard import failure =33/34 authorized top-level starts. No successful sample was rerun/replaced; the optional NSYS start was not consumed. Source, scalar evidence, figures and raw-evidence identities are published; full vectors, complete payloads, profiler binaries, placement and credentials stay private.
