# Shared-frontier CPU trace: NO_GO

**Decision:** stop this frozen classical query-ball/annulus candidate. None of
12 primary Words/DNA cells reaches the predeclared 10x distance or frontier gate.
This is not a proof that every shared-frontier design is impossible.

| Dataset | Full source rows | Measured initial rows | Batch | Shared/cached-GTS metric calls, across 2 seeds and all radii | Shared/cached-GTS frontier payload including query tree |
|---|---:|---:|---:|---:|---:|
| Words | 611,756 | 65,536 | 256 | 1.67–4.85x | 1.78–7.11x |
| GRCh38-derived DNA108 | 1,000,000 | 65,536 | 256 | 1.54–13.62x | 2.67–14.23x |
| TLoc, pressure only | 10,000,000 | 65,536 | 256 | 340.29–792.31x | 257.42–514.13x |

Ratios are **cost inflation**, not acceleration. Full population sizes are
provenance, not benchmarked sizes. DNA is a real-genome-derived replacement,
not the unavailable original GTS DNA dataset. Quickjoin and spatial controls
are CPU family reimplementations; native GTS GPU, eD-index, Gowanlock GPU and
JZ Morton/plane executables were **not** measured.

## Read and reproduce

- [Full results, diagnosis and limitations](REPORT.md)
- [Frozen contract](CONTRACT.json), [methods and prior art](DESIGN.md)
- [Claim-evidence and negative-result ledger](CLAIM_EVIDENCE.md)
- [Reproduction and private custody](REPRODUCE.md)
- [Machine-readable results](results/SUMMARY.json)
- [MIT license for this new artifact only](LICENSE); no upstream code/data is relicensed.

Data-free replay, standard-library Python only, no downloads or target starts:

~~~sh
python3 check.py --test
~~~

Nine serial CPU processes completed; 90 complete method-output streams matched
all-pair references. That reference shares the metric primitive; the edit kernel
also passed 581 independent dynamic-programming pair checks. No CUDA/GPU process
was started. Every counter row, construction/update observation, process proof,
source freeze, input identity and raw-output hash is retained. Raw payloads and
output streams stay outside Git in independently verified persistent remote and
local archives.

The original runner did not hash actual qid/delete files at launch. Post-run
read-only audit confirmed exact agreement with frozen deterministic selections,
all query self-matches and sealed complete outputs; this does not retrospectively
provide launch-time attestation. Original sources/results were not rewritten.
