# Append-only experiment and claim ledger

## Premeasurement checkpoint — 2026-10-11

| Hypothesis | Contract | Keeper/candidate | Predicted work delta | Raw evidence | Status |
|---|---|---|---|---|---|
| Joint coordinate gaps contain information absent from max-of-pivot intervals | CONTRACT.json; original GIST tree and 8-query slice | C0 / random-ortho and full-database PCA prefixes | Fewer original 960-D object evaluations, plus query projection and box metadata reads | Frozen input manifest and 128-pair bridge, then full 27-cell matrix | unknown |

Task owned branch: experiments/projection-certificate-20261011, base 1e77f6e.
CPU-only: Xeon Gold 6530, Linux x86_64, NumPy 1.26.4, Python 3.12,
OpenBLAS pthread backend, four low-priority CPU cores for covariance and one for
ordered projection. No GPU lock, CUDA toolkit, clocks/power modification, CUDA
sanitizer, SASS, NSYS/NCU, warmup, paired timing, or sustained latency gates apply.
Elapsed times are resource receipts only, never a speedup denominator. A private
live process preflight was inspected; foreign processes remain untouched.

Budget ambiguity is resolved before measurements: the primary comparator is the
strongest previous pivot cell whose aligned bytes are no more than the same
budget, matching the plan's explicit 16/32/64B examples (REGION4 uses 48B).
An unlimited-budget, strongest-pivot sensitivity is also retained; weaker
GLOBAL-only comparisons cannot support a gain claim.

| Claim | State | Allowed wording before measurement |
|---|---|---|
| Projection-plus-box novelty | rejected | Established baseline, not a new paper contribution |
| Projection correctness | unvalidated | Stored-matrix contraction and floating-point bridge remain to be checked |
| Information improvement | unknown | No evidence yet |
| GPU speedup or CPU/GPU I/O reduction | unknown | Not measured in this offline experiment |

## Measured and independently checked — 2026-10-11

Stage A passed before Stage B. All 128 pairs, both families and k=1/2/4/8
were checked; 45,518 unique rows / 728,288 projected coordinates were recomputed
with an independent ordered implementation. Every object in selected regions
is covered, with no false prune, no bound above truth and nested prefix bounds.
A supplementary 260-row Python-scalar cross-runtime fixture is bitwise equal.

The full 27-cell / 216-per-query matrix checks 7,104,000 candidate bounds and
retains zero correctness failures. PCA-8 gaps at L3/L4/L5 are
4.891304% / 6.927600% / 16.857069%; random adds zero pruning. Stage C condition is
false, so it is not run. Final decision: LINEAR_PROJECTION_CERTIFICATE_KILLED.
Implementation status: correct offline CPU prototype. Mechanism status: rejected
for the frozen small-box families/slice. Thesis impact: no PCA-plus-box novelty
or GPU promotion. Leaf improvement over the strongest <=64B pivot (+3.330208 pp)
is real but insufficient; see DECISION.md for reopen conditions.

| Claim | State | Evidence | Allowed wording |
|---|---|---|---|
| Stored-matrix contraction and arithmetic safety | theoretical + measured | SAFETY.md, BASIS.json, STAGE_A.json, CERTIFICATE_VALIDATION.json | Exact-safe on the declared FP32-domain/RN-FP64 contract |
| PCA information improvement | measured | per_level_summary.csv, per_query_summary.csv | Limited ancestor improvement; leaf gap 16.857069% on eight frozen queries |
| Within-budget pivot advantage | measured | pivot_comparison.csv | PCA loses at L3/L4 and improves at leaf at 32/64B; REGION comparator is query-oracle |
| GPU I/O or latency reduction | unknown | no evidence | No claim |
| Partition is the root cause universally | unknown | no identifying experiment | These two summaries fail here; co-design is a next-step recommendation only |

Four bounded CPU worker runs were retained, not averaged or selected for timing.
Run1 is the initial version; run2 makes CPU binding inherited/portable and forbids
Python -O; run3 reads actual CPU/BLAS/thread metadata; run4 adds a direct-CLI
short-header input gate. Basis coefficients, projected-array SHA, interval bytes,
scalar fixture and all count/comparison CSVs are identical across all four.
Source snapshots and original receipts remain in private raw storage; their hashes
are retained in RAW_MANIFEST.json. The final published source corresponds to
run4. No adverse correctness result was discarded or relabeled.

Four vector figures were rendered as whole pages and 600-DPI crops; a legend
intersection was fixed. Font embedding, final-size labels, signed-axis gain and
separate denominators were inspected. Publication verification remains a distinct
final gate; this entry does not itself claim uploading.
