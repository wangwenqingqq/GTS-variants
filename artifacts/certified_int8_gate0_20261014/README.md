# Certified INT8 exact search: Gate0 admission stop

**SUBSUMED_PRIOR_ART — stop after Gate A.** The proposed broad certified
precision-routing thesis has a direct prior-art precedent, plus older exact
Euclidean compact-filter/refine foundations. This is a novelty-admission
judgement, **not a measured INT8 failure**. See [the source-specific audit](PRIOR_ART.md).

No INT8 quantizer, residual fixture, 1M-row conversion, 32M-pair replay, GPU,
Tensor Core or profiler was started. Certification rate, fallback fraction,
zero-error quality, latency and end-to-end gain are **UNKNOWN / NOT_RUN**.
The 12 tiny rational witnesses are logical checks, not GIST or FP64-bound evidence.

## Frozen scope, not executed results

GIST1M: **1,000,000 original FP32 row occurrences x 960 dimensions**, same 32
Gate2 range queries, radius bits, cutoff and ordered-FP64 oracle identities.
The plan parent 1f71ad70b5dbf839ff6bf2360b0a1197aecc8006 is an ancestor of the
live delivery base 3b9d570d899e19d83ad991f73a6024563e1db810. All three frozen
parent input files are byte-identical at those commits. No user work was reset
and no data file was read.

| Requested stage / metric | State |
|---|---|
| Workload identity freeze; primary-source admission | Complete; SUBSUMED_PRIOR_ART |
| Symmetric per-vector INT8 quantizer / residual upper bounds | NOT_IMPLEMENTED / NOT_RUN |
| 1M quantization;32M interval classification | NOT_RUN; 0 rows / pairs |
| Certification fraction; fallback / margin diagnostics | UNKNOWN |
| FN / FP / bound violations | UNKNOWN, not zero |
| Actual traffic; latency; E2E gain | NOT_MEASURED |
| GPU / NCU / NSYS / Tensor Core starts | 0 |

## Design arithmetic only

The requested payload model remains intact:960B code+4B scale+4B residual
bound=968B/vector; original3840B vectors remain for exact score fallback.
Persistent payload would be **4.808 GB**, or **1.252083x** FP32-only storage,
not 4x total compression. Inserts maintain an additional 968B/vector; delete
must keep raw and sidecar row ownership aligned. No cheap-update claim is made.

Query source bytes would be 968,000,000+3840*|ambiguous union final hits|.
The mean is unknown because no classification ran. An ambiguous hit is counted
once, and membership acceptance does not replace the exact output score.
Query/control/ID/output/rounding costs are unpriced unknowns, not zero.

The 968MB first-pass floor is at most **4.614451%** below the historical
progressive source model 1,014,828,776B/query, even before fallback. This is
**not an actual-DRAM or E2E upper bound**, and does not silently change the
plan's 1.50GB GO threshold against its 3.84GB full-scan reference. A favorable
weak-reference model would not establish an advantage over the existing keeper.

[Five required decision answers](DECISION.md) · [Claim-evidence ledger](CLAIM_EVIDENCE.md) ·
[Validation](VALIDATION.md) · [Reproduction](REPRODUCE.md) ·
[Unresolved numerical boundaries](NUMERICAL_BOUNDARY.md)

No data plots are fabricated;[figures/README.md](figures/README.md) explains the
unexecuted figure set. Source PDFs/full snapshots, original data, private plan,
credentials and machine configuration are excluded from the publication set.
Keeper and confidential manuscript remain unchanged; GPU Gate1 is not admitted.
