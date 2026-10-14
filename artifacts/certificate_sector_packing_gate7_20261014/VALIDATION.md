# Validation and closure

Passed before population: 545 native fixture rows (272 inherited + 273 packed),
including finite extremes, signed zero, subnormal, duplicate/self rows, equality,
invalid metadata and nonfinite guards. The addition-order counterexample is
retained. All 32 x first4096 rows match independent ordered NumPy partial/full
arithmetic and frozen original full bits before population.

Population:one training process, one 32M-pair evaluation process; no failed or
retried population. All 960M transformed FP32 coordinate bit patterns are restored
exactly. Full32M packed-source scores match the frozen scores bit-for-bit.
Every P1 partial is finite, nonnegative, <=frozen full, with 0 false rejection.
Original data, reference files, parent files, source and packed hashes are frozen.

Read-only closure:96M saved partial-bound/count checks (P1+historical S1+C1),
source/reference/raw-proof identities, exact integer gates and rational p90.
The public stdlib checker independently reconstructs W and the frozen permutation
and checks all 32 scalar counts, purity, recovery, ownership and no-GPU scope.
No candidate population was rerun during observation. An additional read-only
scalar-input audit checks all 1024 training top128 orders and all 32 evaluation
C1/packed-sector orders and FP64 score hashes from the original inputs; it runs
no pair distances. See evidence/INPUT_SEMANTIC_AUDIT.json.

Operational repairs, not measurement replacements:initial local module staging
lookup; one observer transfer path error; one exclusive-output collision in the
observer. Original failed logs/directories remain private. The repaired observer
used a new output directory; see evidence/OPERATIONAL_NOTES.json. The prior-art
citation locator correction is additive; registered admission text stays intact.

Figures:four inherited-style 3.4-inch diagnostics, vector PDF/SVG and 300DPI PNG,
minimum visible font 7pt, zero-origin bars, no fabricated confidence intervals.
Automated text bounds/style checks, whole-image 300DPI inspection and 600DPI PDF
title/label crops pass; embedded PDF fonts are not Type3.
See evidence/FIGURE_QA.json. No paper page was edited or claimed visually verified.

Release-grade fresh-checkout and remote-upload receipts are recorded at delivery
outside this content-hashed manifest; a source-tree check alone is not a claim
that a committed or remote revision has been verified.
